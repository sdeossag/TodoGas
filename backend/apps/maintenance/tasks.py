import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name='maintenance.generate_preventive_work_orders')
def generate_preventive_work_orders():
    from .engine import run_daily_generation
    summary = run_daily_generation()
    logger.info("[task] Generación diaria completada: %s", summary)
    return summary


@shared_task(name='maintenance.send_meter_alert')
def send_meter_alert(task_id):
    """
    Una lectura cruzo el umbral de una tarea "cuando" y se abrio la tarea
    pendiente: correo a los administradores con el equipo, la lectura y la
    condicion (decision del 2026-09-24).
    """
    from django.conf import settings
    from django.core.mail import EmailMessage
    from django.template.loader import render_to_string

    from apps.users.models import User

    from .models import Task

    tarea = Task.objects.select_related(
        "asset__hospital", "asset__node", "plan_task__meter_unit", "trigger_reading__meter__unit",
    ).filter(pk=task_id).first()
    if tarea is None or tarea.trigger_reading is None:
        return {"status": "skipped", "reason": "sin lectura"}
    para = sorted(
        User.objects.filter(role=User.Role.ADMIN, is_active=True)
        .exclude(email="").values_list("email", flat=True)
    )
    if not para:
        return {"status": "skipped", "reason": "sin administradores con correo"}
    pt = tarea.plan_task
    lectura = tarea.trigger_reading
    msg = EmailMessage(
        subject=f"Lectura fuera de umbral: {tarea.asset.name} | {tarea.asset.hospital.name}",
        body=render_to_string("maintenance/email_meter_alert.html", {
            "tarea": tarea,
            "lectura": lectura,
            "unidad": lectura.meter.unit,
            "condicion": f"{pt.get_meter_comparator_display().lower()} {pt.meter_threshold.normalize():f}",
            "valor": f"{lectura.value.normalize():f}",
            "frontend_url": settings.FRONTEND_URL,
        }),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=para,
    )
    msg.content_subtype = "html"
    msg.send()
    logger.info("[task] Aviso de umbral de %s a %s", tarea.asset.code, para)
    return {"status": "sent", "to": para}
