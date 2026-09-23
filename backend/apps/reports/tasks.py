import hashlib
import logging

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone

from apps.maintenance.models import task_type_label
from apps.work_orders.models import WorkOrder

from .failures import record_report_failure
from .generator import field_facts, generate_service_report_pdf
from .models import GeneratedReport, ReportSendLog
from .utils import get_logo_base64

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_work_order_pdf(self, work_order_id):
    try:
        work_order = WorkOrder.objects.select_related(
            "hospital", "assigned_to"
        ).get(id=work_order_id)

        _pdf_bytes, file_url, _report_hash = generate_service_report_pdf(work_order)

        send_report_email.delay(work_order_id)

        return {"status": "ok", "file_url": file_url}
    except Exception as exc:
        # En desarrollo las tareas corren en modo eager con EAGER_PROPAGATES a
        # False: sin este log el fallo no aparece en ningun sitio y la OT queda
        # completada pero sin PDF, con la pestaña Reportes girando en vacio.
        logger.exception(
            "No se pudo generar el PDF de la OT %s: %s", work_order_id, exc
        )

        # En modo eager (desarrollo, CELERY_TASK_ALWAYS_EAGER) self.retry() NO
        # reintenta: levanta Retry, y apply() la traga porque EAGER_PROPAGATES
        # esta en False. `retries` nunca crecia, asi que la rama de abajo no se
        # alcanzaba jamas y el fallo no quedaba registrado en ningun sitio: la
        # OT se cerraba sin acta y sin rastro. Por eso la condicion no es "ya
        # agote los reintentos" sino "no va a haber otro intento".
        will_retry = (
            not self.request.is_eager
            and self.request.retries < self.max_retries
        )
        if not will_retry:
            # El log del servidor deja de ser el unico sitio donde consta:
            # queda en la traza de auditoria, que si tiene interfaz, y el
            # detalle de la OT lo expone como report_status='failed' para
            # avisar y ofrecer el reintento manual.
            record_report_failure(work_order_id, exc)
            return {"status": "failed", "error": str(exc)}

        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@shared_task(bind=True, max_retries=3)
def send_report_email(self, work_order_id):
    report = None
    recipient_email = ""
    try:
        work_order = WorkOrder.objects.select_related(
            "hospital", "assigned_to"
        ).get(id=work_order_id)
        hospital = work_order.hospital

        report = GeneratedReport.objects.filter(
            work_order=work_order
        ).latest("generated_at")

        if not hospital.contact_email:
            return {"status": "skipped", "reason": "no email"}

        recipient_email = hospital.contact_email

        activos = _assets_label(work_order)
        subject = f"Reporte de servicio - {work_order.wo_code} | {activos or work_order.title}"
        body = render_to_string(
            "reports/email_report.html",
            {
                "work_order": work_order,
                "assets_label": activos,
                "hospital": hospital,
                "report": report,
                "frontend_url": settings.FRONTEND_URL,
                # Lo mismo que dice el acta: cuando y quien, segun el campo.
                **field_facts(work_order),
            },
        )

        msg = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )
        msg.content_subtype = "html"
        msg.send()

        ReportSendLog.objects.create(
            report=report,
            recipient_email=recipient_email,
            recipient_name=hospital.contact_name or "",
            was_successful=True,
        )
        return {"status": "sent", "to": recipient_email}

    except Exception as exc:
        if report is not None and recipient_email:
            ReportSendLog.objects.create(
                report=report,
                recipient_email=recipient_email,
                was_successful=False,
                error_message=str(exc),
            )
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@shared_task(bind=True, max_retries=3)
def generate_consolidated_report(
    self, hospital_id, date_from, date_to, task_type=None, requested_by_id=None
):
    from weasyprint import HTML

    from apps.assets.models import Hospital
    from apps.users.models import User

    try:
        hospital = Hospital.objects.get(id=hospital_id) if hospital_id else None
    except Hospital.DoesNotExist:
        hospital = None

    requested_by = None
    if requested_by_id:
        try:
            requested_by = User.objects.get(id=requested_by_id)
        except User.DoesNotExist:
            pass

    qs = WorkOrder.objects.select_related(
        "hospital", "assigned_to"
    ).prefetch_related("tasks__asset").filter(
        scheduled_date__gte=date_from,
        scheduled_date__lte=date_to,
    )
    if hospital:
        qs = qs.filter(hospital=hospital)
    if task_type:
        qs = qs.filter(task_type=task_type)

    total_ots = qs.count()
    completed_count = qs.filter(status=WorkOrder.Status.COMPLETED).count()
    pct_completed = round(completed_count / total_ots * 100, 1) if total_ots else 0.0
    # Activos distintos atendidos: pasan por las tareas, una OT puede llevar
    # varios.
    from apps.maintenance.models import Task
    assets_count = (
        Task.objects.filter(work_order__in=qs).values("asset").distinct().count()
    )

    from django.db.models import Count as DjCount
    status_summary = [
        {"status": item["status"], "count": item["cnt"]}
        for item in qs.values("status").annotate(cnt=DjCount("id"))
    ]

    generated_at = timezone.now()
    context = {
        "hospital": hospital,
        "date_from": date_from,
        "date_to": date_to,
        "task_type": task_type_label(task_type) if task_type else None,
        "work_orders": list(qs.order_by("scheduled_date")),
        "summary": {
            "total_ots": total_ots,
            "pct_completed": pct_completed,
            "assets_count": assets_count,
        },
        "status_summary": status_summary,
        "generated_at": generated_at.strftime("%Y-%m-%d %H:%M"),
        "logo_base64": get_logo_base64("on_light"),
    }

    html_str = render_to_string("reports/consolidated_report.html", context)
    pdf_bytes = HTML(string=html_str, base_url=settings.BACKEND_URL).write_pdf()

    hospital_code = hospital.code if hospital else "all"
    filename = f"reports/consolidated/{hospital_code}_{date_from}_{date_to}.pdf"
    s3_key = default_storage.save(filename, ContentFile(pdf_bytes))

    file_hash = hashlib.sha256(pdf_bytes).hexdigest()
    report = GeneratedReport.objects.create(
        report_type=GeneratedReport.ReportType.CUSTOM,
        title=f"Consolidado {date_from} – {date_to}",
        file_url=s3_key,
        file_hash=file_hash,
        generated_by=requested_by,
        generated_at=generated_at,
    )

    try:
        download_url = default_storage.url(s3_key)
    except Exception:
        download_url = s3_key

    return {"status": "done", "report_id": str(report.id), "download_url": download_url}


def _assets_label(work_order):
    """"Alarma 3 gases" o "Alarma 3 gases y 2 activos mas" para el asunto y el correo."""
    tareas = list(work_order.tasks.exclude(status="CANCELLED").select_related("asset"))
    if not tareas:
        return ""
    primero = tareas[0].asset.name
    resto = len({t.asset_id for t in tareas}) - 1
    if resto <= 0:
        return primero
    return f"{primero} y {resto} activo{'s' if resto > 1 else ''} más"


def _destinatarios_de_hallazgos(work_order, graves):
    """
    El contacto del hospital y las biomedicas cuyo alcance incluye alguno de
    los equipos con hallazgo grave (una limitada a Urgencias no recibe lo de
    Cirugia).
    """
    from apps.assets.models import Asset
    from apps.users import scope
    from apps.users.models import User

    correos = {work_order.hospital.contact_email} if work_order.hospital.contact_email else set()
    activos = Asset.objects.filter(pk__in={f.asset_id for f in graves})
    for u in User.objects.filter(role=User.Role.CLI, is_active=True, hospital=work_order.hospital):
        if u.email and scope.assets(activos, u).exists():
            correos.add(u.email)
    return sorted(correos)


@shared_task(bind=True, max_retries=3)
def send_serious_findings_email(self, work_order_id):
    """
    Aviso al hospital al aprobar una OT con hallazgos criticos o que dejan un
    equipo fuera de servicio (decision del 2026-09-23). El detalle va en el
    acta y en el portal; el correo es para que no espere a leerla.
    """
    try:
        work_order = WorkOrder.objects.select_related("hospital").get(id=work_order_id)
        graves = [f for f in work_order.findings.select_related("asset__node") if f.is_serious]
        if not graves:
            return {"status": "skipped", "reason": "sin hallazgos graves"}
        para = _destinatarios_de_hallazgos(work_order, graves)
        if not para:
            return {"status": "skipped", "reason": "no email"}
        cuantos = len(graves)
        msg = EmailMessage(
            subject=(
                f"{'Hallazgo importante' if cuantos == 1 else f'{cuantos} hallazgos importantes'}"
                f" - {work_order.wo_code} | {work_order.hospital.name}"
            ),
            body=render_to_string("reports/email_findings.html", {
                "work_order": work_order,
                "findings": graves,
                "hospital": work_order.hospital,
                "frontend_url": settings.FRONTEND_URL,
                "logo_base64": get_logo_base64("on_dark"),
            }),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=para,
        )
        msg.content_subtype = "html"
        msg.send()
        return {"status": "sent", "to": para}
    except Exception as exc:
        logger.exception("No se pudo avisar los hallazgos de la OT %s: %s", work_order_id, exc)
        if self.request.is_eager or self.request.retries >= self.max_retries:
            return {"status": "failed", "error": str(exc)}
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
