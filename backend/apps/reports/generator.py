import hashlib

from django.conf import settings
from django.db.models import Count, Q
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.template.defaultfilters import date as formato_fecha
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


def _valor(fr, corto=False, vacio="—"):
    """Lo que el acta imprime de una respuesta. Una foto guarda foto:<id> o
    sin-conexion:<uuid>: la imagen va en las fotos del activo. En una tabla de
    tomas la celda es angosta: basta con "Foto"."""
    if fr is None or not fr.value:
        return vacio
    if fr.field.field_type == "PHOTO":
        return "Foto" if corto else "Foto adjunta (ver fotos del activo)"
    if fr.field.field_type == "BOOLEAN":
        # El campo guarda 'true'/'false'/'na': el acta no imprime eso.
        return {"true": "Sí", "false": "No", "na": "N/A"}.get(fr.value, fr.value)
    if fr.field.field_type == "GPS" and fr.geo_address:
        # Como el *LOCALIZACION de Fracttal: la direccion, y las coordenadas.
        return fr.geo_address if corto else f"{fr.geo_address} ({fr.value})"
    return fr.value


_ORDEN_ETAPA = {"BEFORE": 0, "AFTER": 1}


def _por_etapa(fotos):
    """Antes, luego Despues y al final las sin etiqueta; dentro de cada grupo, por hora."""
    return sorted(fotos, key=lambda p: (_ORDEN_ETAPA.get(p.stage, 2), p.taken_at))


def _grupos_de_fotos(fotos, limite):
    """
    Las primeras `limite` fotos en grupos con subtitulo Antes / Despues. Las sin
    etiqueta van al final sin subtitulo; si ninguna tiene etiqueta, un solo
    grupo sin subtitulo (el acta de siempre).
    """
    grupos = []
    for p in _por_etapa(fotos)[:limite]:
        titulo = p.get_stage_display() if p.stage else ""
        if not grupos or grupos[-1]["label"] != titulo:
            grupos.append({"label": titulo, "photos": []})
        grupos[-1]["photos"].append(p)
    return grupos


def _mapa(fr, opciones):
    """El mapa pequeno de un campo GPS para el acta, si esta encendido."""
    if fr.field.field_type != "GPS" or not (opciones or {}).get("checklist_mapa", True):
        return ""
    from apps.assets.geo import parse_latlng, static_map_data_uri

    punto = parse_latlng(fr.value)
    return static_map_data_uri(*punto) if punto else ""


def _ubicacion_del_activo(tarea, secciones, resolvedores, mapas, opciones):
    """
    La sububicacion del equipo con su direccion y, si el interruptor de mapa
    esta encendido y el tecnico no tomo GPS, un mapa pequeno con su punto.

    Es dato del arbol, no de campo: no entra en el hash de integridad (el acta
    la imprime con lo que diga el arbol al generarse, y las ya generadas no
    cambian).
    """
    from apps.assets.ubicacion import ResolvedorUbicaciones

    activo = tarea.asset
    if not activo.node_id:
        return None
    if activo.hospital_id not in resolvedores:
        resolvedores[activo.hospital_id] = ResolvedorUbicaciones(activo.hospital)
    sub = resolvedores[activo.hospital_id].resolver(activo.node_id)
    if sub is None:
        return None
    sub = dict(sub, map="")
    con_gps_del_tecnico = any(f["map"] for sec in secciones for f in sec["rows"] if "map" in f)
    if (
        sub["latitude"] is not None
        and not con_gps_del_tecnico
        and (opciones or {}).get("checklist_mapa", True)
        and (opciones or {}).get("activo_ubicacion", True)
    ):
        from apps.assets.geo import static_map_data_uri

        punto = (sub["latitude"], sub["longitude"])
        if punto not in mapas:
            mapas[punto] = static_map_data_uri(*punto)
        sub["map"] = mapas[punto]
    return sub


def _sections(respuesta, opciones=None):
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
                {"label": fr.field.label, "value": _valor(fr, vacio="Sin respuesta"), "notes": _texto(fr.notes), "map": _mapa(fr, opciones)}
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
                _texto(indice[(f.id, n)].notes) for f in campos
                if (f.id, n) in indice and _texto(indice[(f.id, n)].notes)
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


def _con_correccion(work_order, calculado):
    """
    La fecha de intervencion corregida en revision (WorkOrder.intervention_*)
    manda sobre la calculada, sin marca en el acta. Lo calculado no se toca.
    """
    inicio = work_order.intervention_start_override
    fin = work_order.intervention_end_override
    if inicio is None or fin is None:
        return calculado
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
        "field_work": _con_correccion(work_order, _trabajo_en_campo(
            respuestas,
            list(Photo.objects.filter(work_order=work_order, hidden=False)),
            list(Signature.objects.filter(work_order=work_order)),
        )),
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


def _texto(valor):
    """El valor como texto limpio: None, vacio o solo espacios no cuentan como dato."""
    if valor is None:
        return ""
    return str(valor).strip()


def _fecha(valor, formato="d/m/Y"):
    if hasattr(valor, "hour"):
        valor = timezone.localtime(valor)
    return formato_fecha(valor, formato)


def _rango(inicio, fin):
    """'26/10/2026 10:00 – 11:30', o con las dos fechas si cruza la medianoche."""
    if _fecha(inicio) == _fecha(fin):
        return f"{_fecha(inicio, 'd/m/Y H:i')} – {_fecha(fin, 'H:i')}"
    return f"{_fecha(inicio, 'd/m/Y H:i')} – {_fecha(fin, 'd/m/Y H:i')}"


def _dato(etiqueta, valor, extra="", mapa=""):
    """Un dato del acta, o None si no hay valor: lo vacio no se imprime."""
    valor = _texto(valor)
    return {"label": etiqueta, "value": valor, "extra": _texto(extra), "map": mapa} if valor else None


def _de_a_dos(datos):
    """Los datos que si existen, en filas de dos celdas (la segunda puede quedar sola)."""
    datos = [d for d in datos if d]
    return [datos[i:i + 2] for i in range(0, len(datos), 2)]


def _ficha_activo(tarea, respuesta, sub, op):
    """
    El cuadro de un activo: su ubicacion y su ficha tecnica juntas, al inicio
    de su bloque. Un activo que es una ubicacion entera (Asset.represents_node)
    se lee como "Ubicacion intervenida", sin codigo interno ni tipo.

    Es presentacion: no entra en el hash de integridad.
    """
    a = tarea.asset
    es_ubicacion = a.is_location
    ruta = _texto(a.node.path) if a.node_id else ""

    ubicacion = None
    direccion, mapa = _texto((sub or {}).get("address")), (sub or {}).get("map", "")
    # Una ubicacion cuyo nombre ya es toda su ruta (y sin direccion ni mapa) no
    # repite lo que dice el titulo del bloque.
    if op["activo_ubicacion"] and ruta and not (es_ubicacion and ruta == _texto(a.name) and not (direccion or mapa)):
        ubicacion = _dato("Ubicación", ruta, extra=direccion, mapa=mapa)

    equipo = [] if es_ubicacion else [
        _dato("Código", a.code),
        _dato("Tipo de equipo", a.asset_type) if op["activo_tipo"] else None,
        _dato("Fabricante", a.manufacturer) if op["activo_fabricante"] else None,
        _dato("Modelo", a.model) if op["activo_modelo"] else None,
        _dato("Número de serie", a.serial_number) if op["activo_serie"] else None,
        # La ubicacion del equipo sale solo si dice algo que la ruta no dice.
        _dato("Dónde está el equipo", a.equipment_location)
        if op["activo_ubicacion_equipo"] and _texto(a.equipment_location) != ruta else None,
    ]
    plan = tarea.plan_task.plan.name if tarea.plan_task_id else ""
    lista = (
        tarea.checklist_version.template.name
        if op["activo_checklist"] and respuesta is not None and tarea.checklist_version_id else ""
    )
    trabajo = [
        _dato("Tarea realizada", tarea.title),
        _dato("Protocolo", plan if _texto(plan) != _texto(tarea.title) else ""),
        _dato("Lista de revisión", lista),
    ]
    return {"location": ubicacion, "rows": _de_a_dos(equipo + trabajo)}


def _revision(respuesta):
    """Cuando y quien respondio el checklist, segun sus respuestas (no started_at, que es la creacion)."""
    if respuesta is None:
        return None
    trabajo = _trabajo_en_campo([respuesta], [], [])
    if trabajo is None:
        return None
    por = _nombre(respuesta.completed_by) if respuesta.completed_by_id else ""
    return {"when": _rango(trabajo["start"], trabajo["end"]), "by": por}


def _datos_de_la_visita(work_order, bloques, ejecutores, trabajo, op):
    """Los datos de la visita en filas de dos celdas; lo apagado o vacio no ocupa lugar."""
    todas_ubicaciones = bool(bloques) and all(b["asset"].is_location for b in bloques)
    return _de_a_dos([
        _dato("Hospital", work_order.hospital.name),
        _dato("Ubicación de la visita", work_order.location.path)
        if op["visita_ubicacion"] and work_order.location_id else None,
        _dato("Ubicaciones intervenidas" if todas_ubicaciones else "Activos intervenidos", len(bloques))
        if op["visita_activos"] and bloques else None,
        # Quien hizo el trabajo y cuando, segun lo registrado en campo; no el
        # asignado ni la hora de aprobar.
        _dato("Trabajo realizado por", ", ".join(ejecutores)) if op["visita_ejecutor"] else None,
        _dato("Fecha programada", _fecha(work_order.scheduled_date))
        if op["visita_fecha_programada"] and work_order.scheduled_date else None,
        _dato("Fecha y hora del trabajo", _rango(trabajo["start"], trabajo["end"]))
        if op["visita_trabajo_en_campo"] and trabajo else None,
        _dato("Tiempo de trabajo", trabajo["duration"]) if op["visita_duracion"] and trabajo else None,
    ])


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

    photos_qs = Photo.objects.filter(work_order=work_order, hidden=False).order_by("taken_at")
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
    resolvedores, mapas = {}, {}
    secciones_por_tarea = {t.id: _sections(respuestas.get(t.id), opciones) for t in tareas}
    bloques = []
    for t in tareas:
        sublocation = _ubicacion_del_activo(t, secciones_por_tarea[t.id], resolvedores, mapas, opciones)
        bloques.append({
            "task": t,
            "asset": t.asset,
            "checklist_response": respuestas.get(t.id),
            "sections": secciones_por_tarea[t.id],
            "sublocation": sublocation,
            "card": _ficha_activo(t, respuestas.get(t.id), sublocation, opciones),
            "title": _texto(t.asset.name) or _texto(t.asset.code),
            "review": _revision(respuestas.get(t.id)),
            "photos": fotos_por_tarea.get(t.id, []),
            "photo_groups": _grupos_de_fotos(fotos_por_tarea.get(t.id, []), 6),
            "field_work": _trabajo_en_campo(
                [respuestas[t.id]] if t.id in respuestas else [], [], []
            ),
        })

    signatures = list(signatures_qs)
    for s in signatures:
        s.file_url = _resolve_url(s.file_url)

    # Hash del contenido probatorio: checklist, fotos, firmas, tecnico y
    # observaciones. Es el que se imprime en el PDF y contra el que verifica
    # /api/work-orders/{id}/integrity/.
    report_hash = compute_wo_content_hash(work_order)
    generated_at = timezone.now()

    trabajo = _con_correccion(
        work_order, _trabajo_en_campo(list(respuestas.values()), photos, signatures)
    )
    ejecutores = _ejecutores(work_order, list(respuestas.values()))

    context = {
        "work_order": work_order,
        "technician": technician,
        "field_work": trabajo,
        "executors": ejecutores,
        "visit_rows": _datos_de_la_visita(work_order, bloques, ejecutores, trabajo, opciones),
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
            work_order.findings.select_related("asset").annotate(n_fotos=Count("photos", filter=Q(photos__hidden=False)))
            .order_by("asset__code", "reported_at")
        ),
        "visit_photos": fotos_visita,
        "visit_photo_groups": _grupos_de_fotos(fotos_visita, 10),
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
