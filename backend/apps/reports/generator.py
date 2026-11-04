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


def _unidad(field, unidades):
    """
    El simbolo de la unidad de un resultado numerico ("A", "PSI", "h"): la del
    medidor al que esta atado un campo de lectura, o la que traiga el campo
    numerico. `unidades` es un cache {id: MeterUnit} que se llena una vez.
    """
    if field.field_type not in ("NUMBER", "METER"):
        return ""
    opciones = field.options_json if isinstance(field.options_json, dict) else {}
    if opciones.get("meter_unit"):
        if unidades is not None and not unidades:
            from apps.assets.models import MeterUnit

            unidades.update({str(u.pk): u for u in MeterUnit.objects.all()})
        u = (unidades or {}).get(str(opciones["meter_unit"]))
        if u is not None:
            return _texto(u.symbol or u.name)
    unidad = opciones.get("unit")
    return _texto(unidad) if isinstance(unidad, str) else ""


def _valor(fr, corto=False, vacio="—", unidades=None):
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
    unidad = _unidad(fr.field, unidades)
    if unidad:
        return f"{fr.value} {unidad}"
    return fr.value


_VERDADERO = ("true", "1", "yes", "si", "sí")
_FALSO = ("false", "0", "no")
# Valor guardado de Aprobo/Alerta/Fallo (FieldType.PASS_ALERT_FAIL, que otro
# modulo define): se compara por la cadena para no depender de que exista.
_APROBO_ALERTA_FALLO = (("APROBO", "Aprobó"), ("ALERTA", "Alerta"), ("FALLO", "Falló"))


def _casillas(fr):
    """
    Las casillas de una respuesta de opciones: [(rotulo, marcada)], como el
    "Aprobó / Alerta / Falló" del acta de Fracttal. None si la respuesta no es
    de ese tipo o no es una de las opciones (el N/A sale como texto).
    """
    if fr is None or not fr.value:
        return None
    tipo = fr.field.field_type
    valor = str(fr.value).strip()
    if tipo == "BOOLEAN":
        if valor.lower() in _VERDADERO:
            return [("Sí", True), ("No", False)]
        if valor.lower() in _FALSO:
            return [("Sí", False), ("No", True)]
    elif tipo == "PASS_ALERT_FAIL":
        if valor.upper() in {c for c, _ in _APROBO_ALERTA_FALLO}:
            return [(rotulo, valor.upper() == codigo) for codigo, rotulo in _APROBO_ALERTA_FALLO]
    return None


def _texto_de_casillas(fr, valor):
    """El texto de una respuesta de opciones fuera de las casillas: N/A y valores raros."""
    if fr is not None and fr.field.field_type == "PASS_ALERT_FAIL":
        return "N/A" if str(fr.value).strip().upper() in ("NA", "N/A") else valor
    return valor


def _localizacion(fr):
    """
    Lo que el acta imprime de una respuesta GPS, como la fila *LOCALIZACION de
    Fracttal: direccion, coordenadas (una por linea) y fecha y hora en que el
    tecnico tomo el punto. None si el campo no es GPS o no tiene respuesta.
    """
    if fr is None or fr.field.field_type != "GPS" or not _texto(fr.value):
        return None
    partes = [p.strip() for p in str(fr.value).split(",")]
    return {
        "address": _texto(fr.geo_address),
        "coords": partes if len(partes) == 2 else [_texto(fr.value)],
        "when": _fecha(fr.answered_at, "d/m/Y H:i:s") if fr.answered_at else "",
    }


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
    unidades = {}  # cache de unidades de medidor, una consulta por acta

    secciones = []
    for grupo, respuestas in por_grupo.items():
        if grupo not in repetibles:
            secciones.append({"name": grupo, "repeated": False, "rows": [
                {
                    "label": fr.field.label,
                    "value": _texto_de_casillas(fr, _valor(fr, vacio="Sin respuesta", unidades=unidades)),
                    "boxes": _casillas(fr),
                    "notes": _texto(fr.notes),
                    "map": _mapa(fr, opciones),
                    "gps": _localizacion(fr),
                }
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
            celdas = [
                {
                    "text": _texto_de_casillas(
                        indice.get((f.id, n)), _valor(indice.get((f.id, n)), corto=True, unidades=unidades)
                    ),
                    "boxes": _casillas(indice.get((f.id, n))),
                }
                for f in campos
            ]
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


def _sin_localizaciones(secciones):
    """
    Separa las respuestas GPS del resto: van en la primera fila de SUBTAREAS
    (LOCALIZACION), no en el grupo donde estaban. Devuelve (secciones sin ellas,
    localizaciones); un grupo que solo tenia GPS desaparece.
    """
    localizaciones, resto = [], []
    for sec in secciones:
        if sec["repeated"]:
            resto.append(sec)
            continue
        filas = []
        for f in sec["rows"]:
            (localizaciones if f.get("gps") else filas).append(f)
        if filas:
            resto.append(dict(sec, rows=filas))
    return resto, localizaciones


def _tablas_de_subtareas(localizaciones, secciones):
    """
    Las tablas de SUBTAREAS: una de 3 columnas (grupo, que se reviso,
    resultado) que abre con las LOCALIZACION y sigue con los grupos normales
    en su orden; un grupo repetible corta la tabla y sale como la suya (una fila
    por toma). Cada elemento es {"repeated": bool, ...}.
    """
    tablas, filas = [], []

    def cerrar():
        if filas:
            tablas.append({"repeated": False, "rows": list(filas)})
            filas.clear()

    for loc in localizaciones:
        filas.append(dict(loc, group=""))
    for sec in secciones:
        if sec["repeated"]:
            cerrar()
            tablas.append(sec)
        else:
            filas.extend(dict(f, group=sec["name"]) for f in sec["rows"])
    cerrar()
    return tablas


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
    # La firma de validacion es de la aprobacion (dias despues, a veces): no es
    # hora de trabajo en campo.
    horas += [
        s.signed_at for s in signatures
        if s.signed_at and s.signature_type != Signature.SignatureType.VALIDATION
    ]
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
    El recuadro ACTIVOS de un activo, como el de Fracttal: una descripcion
    corrida (nombre, marca, modelo, serie y codigo), el "Ubicado en" con la ruta
    del arbol y debajo sus datos en dos columnas. Un activo que es una
    ubicacion entera (Asset.represents_node) se lee como ubicacion, sin codigo
    interno ni datos de equipo.

    Solo salen los datos que existen en el modelo y tienen valor. Es
    presentacion: no entra en el hash de integridad.
    """
    a = tarea.asset
    es_ubicacion = a.is_location
    ruta = _texto(a.node.path) if a.node_id else ""

    ubicacion = None
    direccion, mapa = _texto((sub or {}).get("address")), (sub or {}).get("map", "")
    # Una ubicacion cuyo nombre ya es toda su ruta (y sin direccion ni mapa) no
    # repite lo que dice la descripcion.
    if op["activo_ubicacion"] and ruta and not (es_ubicacion and ruta == _texto(a.name) and not (direccion or mapa)):
        ubicacion = _dato("Ubicado en", ruta, extra=direccion, mapa=mapa)

    partes = [_texto(a.name) or _texto(a.code)]
    if not es_ubicacion:
        if op["activo_fabricante"] and _texto(a.manufacturer):
            partes.append(f"marca {_texto(a.manufacturer)}")
        if op["activo_modelo"] and _texto(a.model):
            partes.append(f"modelo {_texto(a.model)}")
        if op["activo_serie"] and _texto(a.serial_number):
            partes.append(f"serie {_texto(a.serial_number)}")
        if _texto(a.code) and _texto(a.name):
            partes.append(f"cód. {_texto(a.code)}")
    descripcion = _dato(
        "Ubicación intervenida" if es_ubicacion else "Descripción", " ".join(p for p in partes if p)
    )

    clasificaciones = [
        _dato("Clasificación 1", a.classification_1),
        _dato("Clasificación 2", a.classification_2),
    ] if op["activo_clasificaciones"] and not es_ubicacion else []
    equipo = [] if es_ubicacion else [
        _dato("Tipo de equipo", a.asset_type) if op["activo_tipo"] else None,
        _dato("Prioridad", a.get_priority_display()) if op["activo_prioridad"] else None,
        _dato("Código de barras", a.barcode) if op["activo_codigo_barras"] else None,
        # La ubicacion del equipo sale solo si dice algo que la ruta no dice.
        _dato("Dónde está el equipo", a.equipment_location)
        if op["activo_ubicacion_equipo"] and _texto(a.equipment_location) != ruta else None,
    ]
    return {
        "full": [d for d in (descripcion, ubicacion) if d],
        "rows": _de_a_dos(clasificaciones + equipo),
    }


def _unidad_de_frecuencia(valor, unidad):
    nombres = {"DAYS": ("día", "días"), "WEEKS": ("semana", "semanas"),
               "MONTHS": ("mes", "meses"), "YEARS": ("año", "años")}
    singular, plural = nombres.get(unidad, (unidad.lower(), unidad.lower()))
    return singular if valor == 1 else plural


def _numero(valor):
    """Un Decimal sin ceros de mas: 500.000 -> '500'."""
    return format(valor.normalize(), "f") if valor is not None else ""


def _activador(plan_task):
    """
    El activador de la tarea del protocolo, como el "Fecha Cada 6 Meses" de
    Fracttal: por fecha ("Cada 6 meses"), por evento o por medidor. Vacio si la
    tarea no viene de un protocolo.
    """
    if plan_task is None:
        return ""
    T = type(plan_task).Trigger
    if plan_task.trigger == T.DATE and plan_task.frequency_value:
        n = plan_task.frequency_value
        return f"Cada {n} {_unidad_de_frecuencia(n, plan_task.frequency_unit)}"
    if plan_task.trigger == T.EVENT:
        return "Por evento"
    unidad = plan_task.meter_unit
    nombre = _texto(unidad.symbol or unidad.name) if unidad else ""
    if plan_task.trigger == T.EVERY and plan_task.meter_interval:
        return f"Cada {_numero(plan_task.meter_interval)} {nombre}".strip()
    if plan_task.trigger == T.WHEN and plan_task.meter_threshold is not None:
        comparador = type(plan_task).Comparator(plan_task.meter_comparator).label.lower()
        return f"Cuando {_texto(unidad.name) if unidad else 'la lectura'} sea {comparador} {_numero(plan_task.meter_threshold)}"
    return ""


def _ficha_tarea(tarea, respuesta, tiempos, work_order, op):
    """
    El recuadro TAREAS PLANIFICADAS de una tarea: su descripcion, fechas y
    horas reales del trabajo (las de _trabajo_en_campo, no las de la OT), tipo,
    activador del protocolo, duraciones y paro. Es presentacion: no entra en el
    hash de integridad.
    """
    plan = tarea.plan_task.plan.name if tarea.plan_task_id else ""
    detalle = _texto(tarea.description)
    descripcion = _dato(
        "Descripción", _texto(tarea.title) + (f" — {detalle}" if detalle and detalle != _texto(tarea.title) else "")
    )
    lista = (
        tarea.checklist_version.template.name
        if op["activo_checklist"] and respuesta is not None and tarea.checklist_version_id else ""
    )
    programada = tarea.scheduled_date or work_order.scheduled_date
    return {
        "full": [d for d in (descripcion,) if d],
        "rows": _de_a_dos([
            _dato("Protocolo", plan if _texto(plan) != _texto(tarea.title) else ""),
            _dato("Lista de revisión", lista),
            _dato("Fecha programada", _fecha(programada)) if op["visita_fecha_programada"] and programada else None,
            _dato("Fecha y hora de inicio", _fecha(tiempos["start"], "d/m/Y H:i"))
            if op["visita_trabajo_en_campo"] and tiempos else None,
            _dato("Tipo de tarea", tarea.get_task_type_display()) if op["tarea_tipo"] else None,
            _dato("Fecha y hora de finalización", _fecha(tiempos["end"], "d/m/Y H:i"))
            if op["visita_trabajo_en_campo"] and tiempos else None,
            _dato("Prioridad", tarea.get_priority_display()) if op["tarea_tipo"] else None,
            _dato("Duración estimada", _duration_label(tarea.estimated_duration))
            if op["tarea_duracion_estimada"] else None,
            _dato("Activador", _activador(tarea.plan_task)) if op["tarea_activador"] else None,
            _dato("Tiempo de ejecución", tiempos["duration"]) if op["visita_duracion"] and tiempos else None,
            _dato("Tiempo real de paro del activo", _duration_label(work_order.downtime))
            if op["tarea_paro"] else None,
        ]),
    }


def _revision(respuesta):
    """Cuando y quien respondio el checklist, segun sus respuestas (no started_at, que es la creacion)."""
    if respuesta is None:
        return None
    trabajo = _trabajo_en_campo([respuesta], [], [])
    if trabajo is None:
        return None
    por = _nombre(respuesta.completed_by) if respuesta.completed_by_id else ""
    return {"when": _rango(trabajo["start"], trabajo["end"]), "by": por}


def _datos_de_la_visita(work_order, bloques, ejecutores, op):
    """
    El primer recuadro del acta, como el de Fracttal: quien genero la orden,
    el responsable (quien hizo el trabajo, segun lo registrado en campo, no el
    asignado ni quien aprobo), duracion estimada y notas. Lo apagado o vacio
    no ocupa lugar. Las fechas y horas del trabajo van en cada tarea.
    """
    todas_ubicaciones = bool(bloques) and all(b["asset"].is_location for b in bloques)
    creador = _nombre(work_order.created_by) if work_order.created_by_id else ""
    return _de_a_dos([
        _dato("Generó", creador) if op["visita_genero"] else None,
        _dato("Responsable", ", ".join(ejecutores)) if op["visita_ejecutor"] else None,
        _dato("Hospital", work_order.hospital.name),
        _dato("Ubicación de la visita", work_order.location.path)
        if op["visita_ubicacion"] and work_order.location_id else None,
        _dato("Duración estimada", _duration_label(work_order.estimated_duration))
        if op["visita_duracion_estimada"] else None,
        _dato("Ubicaciones intervenidas" if todas_ubicaciones else "Activos intervenidos", len(bloques))
        if op["visita_activos"] and bloques else None,
        _dato("Descripción del trabajo", work_order.description) if op["visita_descripcion"] else None,
        _dato("Notas", work_order.notes) if op["visita_notas"] else None,
    ])


def _render(work_order, opciones, empresa=None):
    """
    El acta en PDF con los interruptores `opciones` (apps.reports.options).
    `empresa` trae la razon social y el NIT del encabezado (ReportSettings);
    sin ellos el encabezado no los muestra.
    Devuelve (pdf_bytes, report_hash, generated_at); no guarda nada.
    """
    from weasyprint import HTML

    empresa = empresa or {}

    technician = work_order.assigned_to

    # Un bloque por tarea: el activo, su checklist y sus fotos. Las tareas
    # canceladas no se hicieron y no van en el acta.
    tareas = list(
        work_order.tasks.exclude(status="CANCELLED")
        .select_related("asset__hospital", "asset__node", "plan_task__plan", "plan_task__meter_unit",
            "checklist_version__template")
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
    signatures = list(signatures_qs)
    for s in signatures:
        s.file_url = _resolve_url(s.file_url)

    # Hash del contenido probatorio: checklist, fotos, firmas, tecnico y
    # observaciones. Es el que se imprime en el PDF y contra el que verifica
    # /api/work-orders/{id}/integrity/. Lo que el acta agrega para parecerse
    # al de Fracttal (encabezado, activador, localizacion...) es presentacion
    # y no entra.
    report_hash = compute_wo_content_hash(work_order)
    generated_at = timezone.now()

    trabajo = _con_correccion(
        work_order, _trabajo_en_campo(list(respuestas.values()), photos, signatures)
    )
    ejecutores = _ejecutores(work_order, list(respuestas.values()))

    resolvedores, mapas = {}, {}
    secciones_por_tarea = {t.id: _sections(respuestas.get(t.id), opciones) for t in tareas}
    bloques = []
    for t in tareas:
        sublocation = _ubicacion_del_activo(t, secciones_por_tarea[t.id], resolvedores, mapas, opciones)
        secciones, localizaciones = _sin_localizaciones(secciones_por_tarea[t.id])
        propio = _trabajo_en_campo([respuestas[t.id]] if t.id in respuestas else [], [], [])
        # Fecha y hora de la tarea: las de su checklist; sin ellas, las del
        # trabajo de la orden. La correccion de revision manda sobre ambas.
        tiempos = _con_correccion(work_order, propio or trabajo)
        bloques.append({
            "task": t,
            "asset": t.asset,
            "checklist_response": respuestas.get(t.id),
            "sections": secciones,
            "tables": _tablas_de_subtareas(localizaciones, secciones),
            "locations": localizaciones,
            "sublocation": sublocation,
            "card": _ficha_activo(t, respuestas.get(t.id), sublocation, opciones),
            "task_card": _ficha_tarea(t, respuestas.get(t.id), tiempos, work_order, opciones),
            "title": _texto(t.asset.name) or _texto(t.asset.code),
            "review": _revision(respuestas.get(t.id)),
            "photos": fotos_por_tarea.get(t.id, []),
            "photo_groups": _grupos_de_fotos(fotos_por_tarea.get(t.id, []), 6),
            "field_work": propio,
        })

    context = {
        "work_order": work_order,
        "technician": technician,
        "field_work": trabajo,
        "executors": ejecutores,
        "visit_rows": _datos_de_la_visita(work_order, bloques, ejecutores, opciones),
        "company": {
            "name": _texto(empresa.get("company_name")),
            "tax_id": _texto(empresa.get("company_tax_id")),
        },
        # La fecha de la orden (como en Fracttal): la programada o, sin ella, la
        # del inicio real del trabajo.
        "order_date": work_order.scheduled_date or (trabajo or {}).get("start"),
        "rating": work_order.rating if opciones["encabezado_calificacion"] else None,
        "validation": _validacion(work_order),
        "technician_signature": next(
            (s for s in signatures if s.signature_type == Signature.SignatureType.TECHNICIAN), None
        ),
        "validation_signature": next(
            (s for s in signatures if s.signature_type == Signature.SignatureType.VALIDATION), None
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
        "logo_base64": get_logo_base64("on_light"),
        "op": opciones,
        "n": numeracion(opciones),
    }

    html_str = render_to_string("reports/service_report.html", context)
    pdf_bytes = HTML(string=html_str, base_url=settings.BACKEND_URL).write_pdf()
    return pdf_bytes, report_hash, generated_at


def _empresa_vigente():
    ajustes = ReportSettings.current()
    return {"company_name": ajustes.company_name, "company_tax_id": ajustes.company_tax_id}


def preview_service_report_pdf(work_order, opciones, empresa=None):
    """El acta como quedaria con estas opciones, sin guardarla ni registrarla."""
    return _render(work_order, efectivas(opciones), empresa)[0]


def generate_service_report_pdf(work_order):
    """
    Genera el PDF del acta de servicio para una OT con la configuracion
    vigente y lo sube al storage. Devuelve (pdf_bytes, s3_key, report_hash).
    """
    opciones = efectivas(ReportSettings.current().options)
    pdf_bytes, report_hash, generated_at = _render(work_order, opciones, _empresa_vigente())

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
