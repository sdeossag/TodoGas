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
from apps.work_orders.integrity import (
    INTEGRITY_ALGORITHM_VERSION,
    compute_wo_content_hash,
)

from .models import GeneratedReport


def _duration_label(value):
    """'1 h 25 min' en vez del timedelta crudo ('1:25:03.851900')."""
    if not value:
        return ""
    minutos = int(value.total_seconds() // 60)
    horas, minutos = divmod(minutos, 60)
    if horas:
        return f"{horas} h {minutos} min" if minutos else f"{horas} h"
    return f"{minutos} min" if minutos else "menos de 1 min"


def _resolve_url(file_key):
    """Devuelve la URL publica o pre-firmada de una clave de storage."""
    if not file_key:
        return ""
    if file_key.startswith("http"):
        return file_key
    return default_storage.url(file_key)


def _valor(fr, corto=False):
    """Lo que el acta imprime de una respuesta. Una foto guarda foto:<id> o
    sin-conexion:<uuid>: la imagen va en las fotos del activo. En una tabla de
    tomas la celda es angosta: basta con "Foto"."""
    if fr is None or not fr.value:
        return "—"
    if fr.field.field_type == "PHOTO":
        return "Foto" if corto else "Foto adjunta (ver fotos del activo)"
    if fr.field.field_type == "BOOLEAN":
        # El campo guarda 'true'/'false': el acta no imprime eso.
        return {"true": "Sí", "false": "No"}.get(fr.value, fr.value)
    return fr.value


def _sections(respuesta):
    """
    El checklist de una tarea, por grupos, en el orden de sus respuestas.

    Un grupo normal lista campo, respuesta y observaciones. Uno repetible sale
    como tabla, una fila por toma y una columna por pregunta: 20 tomas de 9
    preguntas caben en una pagina, no en 20 como en el acta de Fracttal.
    """
    if respuesta is None:
        return []
    repetibles = respuesta.version.repeatable_groups
    por_grupo = {}
    for fr in respuesta.field_responses.all():
        por_grupo.setdefault(fr.field.group, []).append(fr)

    secciones = []
    for grupo, respuestas in por_grupo.items():
        if grupo not in repetibles:
            secciones.append({"name": grupo, "repeated": False, "rows": [
                {"label": fr.field.label, "value": _valor(fr), "notes": fr.notes}
                for fr in respuestas
            ]})
            continue
        campos = sorted(
            (f for f in respuesta.version.fields.all() if f.group == grupo),
            key=lambda f: f.sort_order,
        )
        indice = {(fr.field_id, fr.repetition): fr for fr in respuestas}
        filas = []
        for n in range(1, respuesta.count_for(grupo) + 1):
            celdas = [_valor(indice.get((f.id, n)), corto=True) for f in campos]
            notas = "; ".join(
                indice[(f.id, n)].notes for f in campos
                if (f.id, n) in indice and indice[(f.id, n)].notes
            )
            filas.append({"n": n, "cells": celdas, "notes": notas})
        secciones.append({
            "name": grupo,
            "repeated": True,
            "columns": [f.label for f in campos],
            "rows": filas,
            "with_notes": any(f["notes"] for f in filas),
        })
    return secciones


def generate_service_report_pdf(work_order):
    """
    Genera el PDF del acta de servicio para una OT y lo sube al storage.
    Devuelve (pdf_bytes, s3_key, report_hash).
    """
    from weasyprint import HTML

    technician = work_order.assigned_to

    # Un bloque por tarea: el activo, su checklist y sus fotos. Las tareas
    # canceladas no se hicieron y no van en el acta.
    tareas = list(
        work_order.tasks.exclude(status="CANCELLED")
        .select_related("asset__hospital", "asset__node", "plan_task__plan", "checklist_version__template")
        .order_by("sort_order", "created_at")
    )
    respuestas = {
        r.task_id: r
        for r in ChecklistResponse.objects.filter(task__in=tareas).prefetch_related(
            "field_responses__field", "version__fields"
        ).select_related("version")
    }

    photos_qs = Photo.objects.filter(work_order=work_order).order_by("taken_at")
    signatures_qs = Signature.objects.filter(work_order=work_order)
    stock_movements = StockMovement.objects.filter(
        work_order=work_order
    ).select_related("item")

    # Resolver URLs de imagenes para el PDF
    photos = list(photos_qs)
    for p in photos:
        p.file_url = _resolve_url(p.file_url)
    fotos_por_tarea = {}
    fotos_visita = []
    for p in photos:
        if p.task_id:
            fotos_por_tarea.setdefault(p.task_id, []).append(p)
        else:
            fotos_visita.append(p)
    bloques = [
        {
            "task": t,
            "asset": t.asset,
            "checklist_response": respuestas.get(t.id),
            "sections": _sections(respuestas.get(t.id)),
            "photos": fotos_por_tarea.get(t.id, []),
        }
        for t in tareas
    ]

    signatures = list(signatures_qs)
    for s in signatures:
        s.file_url = _resolve_url(s.file_url)

    # Hash del contenido probatorio: checklist, fotos, firmas, tecnico y
    # observaciones. Es el que se imprime en el PDF y contra el que verifica
    # /api/work-orders/{id}/integrity/.
    report_hash = compute_wo_content_hash(work_order)
    generated_at = timezone.now()

    context = {
        "work_order": work_order,
        "technician": technician,
        "actual_duration": _duration_label(work_order.actual_duration),
        "blocks": bloques,
        "visit_photos": fotos_visita,
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
        title=f"Acta de Servicio {work_order.wo_code}",
        file_url=s3_key,
        file_hash=pdf_hash,
        content_hash=report_hash,
        integrity_version=INTEGRITY_ALGORITHM_VERSION,
        generated_by=None,
        generated_at=generated_at,
    )

    return pdf_bytes, s3_key, report_hash
