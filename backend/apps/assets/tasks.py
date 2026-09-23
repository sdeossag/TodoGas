import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


@shared_task(name="assets.send_contract_expiry_notices")
def send_contract_expiry_notices():
    """
    Correo diario a los administradores con los contratos y garantias que
    cruzaron un umbral (60 dias, 30 dias, vencido) desde el ultimo aviso.
    Uno solo, agrupado; si no hay nada, no sale (decision del 2026-09-23).
    """
    from apps.users.models import User

    from .contracts import avisos_pendientes, hoy
    from .models import Contract

    dia = hoy()
    pendientes = avisos_pendientes(dia)
    if not pendientes:
        return {"status": "skipped", "reason": "nada por avisar"}
    para = sorted(
        User.objects.filter(role=User.Role.ADMIN, is_active=True)
        .exclude(email="").values_list("email", flat=True)
    )
    if not para:
        return {"status": "skipped", "reason": "sin administradores con correo"}

    def filas(aviso):
        return [
            {"contract": c, "days_left": (c.end_date - dia).days}
            for c, a in sorted(pendientes, key=lambda p: p[0].end_date) if a == aviso
        ]

    grupos = [
        ("Vencieron", filas(Contract.Notice.EXPIRED)),
        ("Vencen en los próximos 30 días", filas(Contract.Notice.DAYS_30)),
        ("Vencen en los próximos 60 días", filas(Contract.Notice.DAYS_60)),
    ]
    cuantos = len(pendientes)
    msg = EmailMessage(
        subject=(
            "Un contrato o garantía por vencer" if cuantos == 1
            else f"{cuantos} contratos y garantías por vencer"
        ),
        body=render_to_string("assets/email_contracts.html", {
            "grupos": [(titulo, f) for titulo, f in grupos if f],
            "frontend_url": settings.FRONTEND_URL,
        }),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=para,
    )
    msg.content_subtype = "html"
    msg.send()
    # Solo despues de enviar: si el correo falla, mañana se intenta de nuevo.
    for c, aviso in pendientes:
        c.last_notice = aviso
        c.save(update_fields=["last_notice"])
    logger.info("[task] Aviso de vencimientos: %s documentos a %s", cuantos, para)
    return {"status": "sent", "to": para, "count": cuantos}
