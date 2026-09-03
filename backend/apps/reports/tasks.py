import hashlib
import logging

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone

from apps.work_orders.models import WorkOrder

from .generator import generate_service_report_pdf
from .models import GeneratedReport, ReportSendLog
from .utils import get_logo_base64

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_work_order_pdf(self, work_order_id):
    try:
        work_order = WorkOrder.objects.select_related(
            "asset__hospital", "assigned_to"
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

        if self.request.retries >= self.max_retries:
            # Ultimo intento: el log del servidor deja de ser el unico sitio
            # donde consta. Queda en la traza de auditoria, que si tiene
            # interfaz, y el detalle de la OT lo expone como
            # report_status='missing' para poder reintentar a mano.
            _registrar_fallo_de_acta(work_order_id, exc)
            return {"status": "failed", "error": str(exc)}

        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


def _registrar_fallo_de_acta(work_order_id, exc):
    """Anota en auditoria que una OT cerrada se quedo sin acta."""
    from apps.audit.models import AuditLog

    try:
        AuditLog.objects.create(
            user=None,
            action=AuditLog.Action.CREATE,
            entity_type="GeneratedReport",
            entity_id=work_order_id,
            changes={
                "resultado": "fallo",
                "detalle": "No se pudo generar el acta tras agotar los reintentos.",
                "error": str(exc)[:500],
            },
        )
    except Exception:
        # Si ni la auditoria se puede escribir, el log de arriba es lo que hay.
        logger.exception(
            "Tampoco se pudo registrar en auditoria el fallo del acta de la OT %s",
            work_order_id,
        )


@shared_task(bind=True, max_retries=3)
def send_report_email(self, work_order_id):
    report = None
    recipient_email = ""
    try:
        work_order = WorkOrder.objects.select_related(
            "asset__hospital", "assigned_to"
        ).get(id=work_order_id)
        hospital = work_order.asset.hospital

        report = GeneratedReport.objects.filter(
            work_order=work_order
        ).latest("generated_at")

        if not hospital.contact_email:
            return {"status": "skipped", "reason": "no email"}

        recipient_email = hospital.contact_email

        subject = (
            f"Reporte de servicio - {work_order.wo_code}"
            f" | {work_order.asset.name}"
        )
        body = render_to_string(
            "reports/email_report.html",
            {
                "work_order": work_order,
                "hospital": hospital,
                "report": report,
                "frontend_url": settings.FRONTEND_URL,
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
        "asset__hospital", "assigned_to"
    ).filter(
        scheduled_date__gte=date_from,
        scheduled_date__lte=date_to,
    )
    if hospital:
        qs = qs.filter(asset__hospital=hospital)
    if task_type:
        qs = qs.filter(task_type=task_type)

    total_ots = qs.count()
    completed_count = qs.filter(status=WorkOrder.Status.COMPLETED).count()
    pct_completed = round(completed_count / total_ots * 100, 1) if total_ots else 0.0
    assets_count = qs.values("asset").distinct().count()

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
        "task_type": task_type,
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
