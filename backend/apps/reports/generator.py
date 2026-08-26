import hashlib

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.template.loader import render_to_string
from django.utils import timezone

from apps.checklists.models import ChecklistResponse
from apps.evidence.models import Photo, Signature
from apps.inventory.models import StockMovement
from apps.reports.utils import get_logo_base64

from .models import GeneratedReport


def _resolve_url(file_key):
    """Devuelve la URL publica o pre-firmada de una clave de storage."""
    if not file_key:
        return ""
    if file_key.startswith("http"):
        return file_key
    return default_storage.url(file_key)


def generate_service_report_pdf(work_order):
    """
    Genera el PDF del acta de servicio para una OT y lo sube al storage.
    Devuelve (pdf_bytes, s3_key, report_hash).
    """
    from weasyprint import HTML

    asset = work_order.asset
    technician = work_order.assigned_to

    try:
        checklist_response = ChecklistResponse.objects.prefetch_related(
            "field_responses__field"
        ).get(work_order=work_order)
    except ChecklistResponse.DoesNotExist:
        checklist_response = None

    photos_qs = Photo.objects.filter(work_order=work_order).order_by("taken_at")
    signatures_qs = Signature.objects.filter(work_order=work_order)
    stock_movements = StockMovement.objects.filter(
        work_order=work_order
    ).select_related("item")

    # Resolver URLs de imagenes para el PDF
    photos = list(photos_qs)
    for p in photos:
        p.file_url = _resolve_url(p.file_url)

    signatures = list(signatures_qs)
    for s in signatures:
        s.file_url = _resolve_url(s.file_url)

    contenido = f"{work_order.id}{work_order.wo_number}{work_order.completed_at}"
    report_hash = hashlib.sha256(contenido.encode()).hexdigest()
    generated_at = timezone.now()

    context = {
        "work_order": work_order,
        "asset": asset,
        "technician": technician,
        "checklist_response": checklist_response,
        "photos": photos,
        "signatures": signatures,
        "stock_movements": stock_movements,
        "report_hash": report_hash,
        "generated_at": generated_at,
        "logo_base64": get_logo_base64("on_dark"),
    }

    html_str = render_to_string("reports/service_report.html", context)
    pdf_bytes = HTML(string=html_str, base_url=settings.BACKEND_URL).write_pdf()

    filename = f"reports/{work_order.id}/OT-{work_order.wo_number}.pdf"
    s3_key = default_storage.save(filename, ContentFile(pdf_bytes))

    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()

    GeneratedReport.objects.create(
        work_order=work_order,
        report_type=GeneratedReport.ReportType.WORK_ORDER,
        title=f"Acta de Servicio OT-{work_order.wo_number}",
        file_url=s3_key,
        file_hash=pdf_hash,
        generated_by=None,
        generated_at=generated_at,
    )

    return pdf_bytes, s3_key, report_hash
