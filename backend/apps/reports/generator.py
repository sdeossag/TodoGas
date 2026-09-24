import hashlib

from django.conf import settings
from django.db.models import Count
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

from .models import GeneratedReport, ReportSettings
from .options import efectivas, numeracion


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
        # El campo guarda 'true'/'false'/'na': el acta no imprime eso.
        return {"true": "Sí", "false": "No", "na": "N/A"}.get(fr.value, fr.value)
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


def _nombre(user):
    return f"{user.first_name} {user.last_name}".strip() or user.email


def _trabajo_en_campo(respuestas, photos, signatures):
    """
    Cuando se hizo el trabajo, segun lo que el tecnico registro en campo:
    de la primera a la ultima respuesta, foto, cierre de checklist o firma.
    Todas llevan la hora del telefono, tambien lo hecho sin red.

    No se usan started_at/completed_at de la OT: el primero es cuando se marco
    "en proceso" y el segundo cuando el supervisor aprobo, a veces dias
    despues. Imprimirlos como hora del trabajo es lo que hacia falsas las
    actas de Fracttal.
    """
    horas = [fr.answered_at for r in respuestas for fr in r.field_responses.all()]
    horas += [r.completed_at for r in respuestas if r.completed_at]
    horas += [p.taken_at for p in photos if p.taken_at]
    horas += [s.signed_at for s in signatures if s.signed_at]
    if not horas:
        return None
    inicio, fin = min(horas), max(horas)
    return {"start": inicio, "end": fin, "duration": _duration_label(fin - inicio)}


def _ejecutores(work_order, respuestas):
    """
    Quien hizo el trabajo: quienes cerraron los checklists. El asignado puede
    haber cambiado despues (una reasignacion en revision), y en el acta de
    Fracttal eso dejaba de responsable a alguien que no fue.
    """
    vistos = {}
    for r in respuestas:
        if r.completed_by_id and r.completed_by_id not in vistos:
            vistos[r.completed_by_id] = _nombre(r.completed_by)
    if vistos:
        return list(vistos.values())
    return [_nombre(work_order.assigned_to)] if work_order.assigned_to else []


def field_facts(work_order):
    """Periodo de trabajo en campo y ejecutores, para el correo del acta."""
    respuestas = list(
        ChecklistResponse.objects.filter(task__work_order=work_order)
        .exclude(task__status="CANCELLED")
        .select_related("completed_by")
        .prefetch_related("field_responses")
    )
    return {
        "field_work": _trabajo_en_campo(
            respuestas,
            list(Photo.objects.filter(work_order=work_order)),
            list(Signature.objects.filter(work_order=work_order)),
        ),
        "executors": _ejecutores(work_order, respuestas),
    }


def _validacion(work_order):
    """Quien aprobo la OT (la paso a completada) y cuando: el "Validado por"."""
    from apps.work_orders.models import WorkOrder

    h = (
        work_order.status_history.filter(to_status=WorkOrder.Status.COMPLETED)
        .select_related("changed_by")
        .order_by("-changed_at")
        .first()
    )
    if h is None or h.changed_by is None:
        return None
    return {
        "name": _nombre(h.changed_by),
        "role": h.changed_by.get_role_display(),
        "at": h.changed_at,
    }


def _render(work_order, opciones):
    """
    El acta en PDF con los interruptores `opciones` (apps.reports.options).
    Devuelve (pdf_bytes, report_hash, generated_at); no guarda nada.
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
        ).select_related("version", "completed_by")
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
            "field_work": _trabajo_en_campo(
                [respuestas[t.id]] if t.id in respuestas else [], [], []
            ),
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
        "field_work": _trabajo_en_campo(list(respuestas.values()), photos, signatures),
        "executors": _ejecutores(work_order, list(respuestas.values())),
        "validation": _validacion(work_order),
        "technician_signature": next(
            (s for s in signatures if s.signature_type == Signature.SignatureType.TECHNICIAN), None
        ),
        "client_signature": next(
            (s for s in signatures if s.signature_type == Signature.SignatureType.CLIENT), None
        ),
        "blocks": bloques,
        # Lo capturado en campo: la decision posterior del planificador no
        # cambia el acta (va en el portal y en la bandeja).
        "findings": list(
            work_order.findings.select_related("asset").annotate(n_fotos=Count("photos"))
            .order_by("asset__code", "reported_at")
        ),
        "visit_photos": fotos_visita,
        "photos": photos,
        "signatures": signatures,
        "stock_movements": stock_movements,
        "report_hash": report_hash,
        "generated_at": generated_at,
        "logo_base64": get_logo_base64("on_dark"),
        "op": opciones,
        "n": numeracion(opciones),
    }

    html_str = render_to_string("reports/service_report.html", context)
    pdf_bytes = HTML(string=html_str, base_url=settings.BACKEND_URL).write_pdf()
    return pdf_bytes, report_hash, generated_at


def preview_service_report_pdf(work_order, opciones):
    """El acta como quedaria con estas opciones, sin guardarla ni registrarla."""
    return _render(work_order, efectivas(opciones))[0]


def generate_service_report_pdf(work_order):
    """
    Genera el PDF del acta de servicio para una OT con la configuracion
    vigente y lo sube al storage. Devuelve (pdf_bytes, s3_key, report_hash).
    """
    opciones = efectivas(ReportSettings.current().options)
    pdf_bytes, report_hash, generated_at = _render(work_order, opciones)

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
        options_used=opciones,
        generated_by=None,
        generated_at=generated_at,
    )

    return pdf_bytes, s3_key, report_hash
