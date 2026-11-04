"""
Acta de servicio con el estilo del acta de Fracttal que usa el cliente:
encabezado blanco con razon social y NIT, recuadros con ETIQUETA: valor,
ACTIVOS, TAREAS PLANIFICADAS, tabla de SUBTAREAS con LOCALIZACION, adjuntos de
la tarea y tres firmas al final. Todos los datos son ficticios.
"""

import base64
import os
import re
import struct
import sys
import types
import zlib
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone
from model_bakery import baker

from apps.assets.models import Asset, AssetNode, Hospital, MeterUnit
from apps.checklists.models import (
    ChecklistField,
    ChecklistFieldResponse,
    ChecklistResponse,
    ChecklistTemplate,
    ChecklistTemplateVersion,
)
from apps.evidence.models import Photo, Signature
from apps.inventory.models import InventoryItem, StockMovement
from apps.maintenance import services
from apps.maintenance.models import PlanTask, Task
from apps.maintenance.testing import make_plan
from apps.reports.generator import _activador, _casillas, _valor
from apps.reports.models import ReportSettings
from apps.reports.options import CATALOGO, CLAVES, efectivas
from apps.reports.tests.test_acta_configurable import acta_html, admin, cliente  # noqa: F401
from apps.reports.tests.test_acta_lectura import _texto
from apps.users.models import User
from apps.work_orders.integrity import compute_wo_content_hash
from apps.work_orders.models import Finding, WorkOrder

pytestmark = pytest.mark.django_db

URL = "/api/report-settings/"
EMPRESA = {"company_name": "Gases Demo S.A.", "company_tax_id": "NIT 900.000.000-0"}


def _png():
    """Un PNG de 320x200 con degradado, para fotos y firmas de prueba."""
    ancho, alto = 320, 200
    filas = b"".join(
        b"\x00" + b"".join(bytes((40 + x * 200 // ancho, 90 + y * 120 // alto, 150)) for x in range(ancho))
        for y in range(alto)
    )

    def trozo(tipo, datos):
        c = struct.pack(">I", len(datos)) + tipo + datos
        return c + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF)

    return (
        b"\x89PNG\r\n\x1a\n"
        + trozo(b"IHDR", struct.pack(">IIBBBBB", ancho, alto, 8, 2, 0, 0, 0))
        + trozo(b"IDAT", zlib.compress(filas))
        + trozo(b"IEND", b"")
    )


PNG_URI = "data:image/png;base64," + base64.b64encode(_png()).decode()


def _campo(version, label, tipo, grupo="", orden=0, opciones=None):
    return baker.make(ChecklistField, version=version, label=label, field_type=tipo, group=grupo,
                      is_required=False, sort_order=orden, options_json=opciones if opciones is not None else [])


@pytest.fixture
def rico(admin):  # noqa: F811
    """
    Una OT completada con todo lo que el acta de Fracttal muestra: activo con
    ficha, protocolo semestral, GPS, medidas con unidad, Aprobo/Alerta/Fallo
    (por la cadena del tipo), Si/No, un bloque repetible, fotos y firmas.
    """
    amperios, _ = MeterUnit.objects.get_or_create(name="AMPERIOS", symbol="A")
    t = baker.make(ChecklistTemplate, name="Planta de aire")
    v = baker.make(ChecklistTemplateVersion, template=t, version_number=1, is_current=True,
                   repeatable_groups=["MOTOR"])
    campos = {
        "gps": _campo(v, "LOCALIZACION", "GPS", "", 0),
        "tipo": _campo(v, "Indique el tipo de compresor", "TEXT", "COMPRESOR", 1),
        "filtro": _campo(v, "Revision de filtro de admision", "PASS_ALERT_FAIL", "CABEZOTE 1", 2),
        "alerta": _campo(v, "Revision de correas", "PASS_ALERT_FAIL", "CABEZOTE 2", 3),
        "sinaplicar": _campo(v, "Revision de purga", "PASS_ALERT_FAIL", "CABEZOTE 2", 4),
        "fuga": _campo(v, "Hay fuga", "BOOLEAN", "COMPRESOR", 5),
        "presion": _campo(v, "Presion de trabajo", "NUMBER", "COMPRESOR", 6, {"unit": "PSI"}),
        "corriente": _campo(v, "Consumo de corriente linea 1", "METER", "MOTOR", 7, {"meter_unit": str(amperios.id)}),
        "estado": _campo(v, "Estado del motor", "PASS_ALERT_FAIL", "MOTOR", 8),
    }
    hospital = baker.make(Hospital, name="Hospital Demo Norte", is_active=True)
    bloque = AssetNode.objects.create(hospital=hospital, name="Hospital Demo", address="Calle 1 #2-3, Ciudad Demo")
    cuarto = AssetNode.objects.create(hospital=hospital, parent=bloque, name="Cuarto de aire medicinal")
    activo = baker.make(
        Asset, hospital=hospital, node=cuarto, status=Asset.Status.ACTIVE, code="GEN-1125",
        name="Generador de aire medicinal", manufacturer="EQUIPOS DEMO", model="DX-300",
        serial_number="SN-0001", asset_type="Planta", classification_1="HOSPITAL",
        classification_2="CONTRATO PREVENTIVO", barcode="1125", priority=Asset.Priority.HIGH,
        equipment_location="",
    )
    plan = make_plan("MANT. PLANTA DE AIRE", assets=[activo], checklist_template=t,
                     next_due_date=timezone.localdate())
    PlanTask.objects.filter(plan=plan).update(
        block_counts={"MOTOR": 2}, estimated_duration=timedelta(hours=2, minutes=10),
    )
    tarea = Task.objects.get(plan_task__plan=plan, status=Task.Status.PENDING)
    Task.objects.filter(pk=tarea.pk).update(
        title="MANTENIMIENTO DE PLANTA GENERADORA DE AIRE MEDICINAL",
        estimated_duration=timedelta(hours=2, minutes=10),
    )
    tarea.refresh_from_db()
    creador = baker.make(User, role=User.Role.ADMIN, is_active=True, first_name="Carla", last_name="Creadora")
    tec = baker.make(User, role=User.Role.TEC, is_active=True, first_name="Tomas", last_name="Tecnico")
    orden, _ = services.create_work_order_for_tasks([tarea], creador, assigned_to=tec)
    r = orden.tasks.get().checklist_response
    ahora = timezone.now()

    def responder(campo, valor, repeticion=0, **extra):
        ChecklistFieldResponse.objects.create(
            response=r, field=campo, value=valor, repetition=repeticion,
            answered_at=ahora - timedelta(minutes=50), **extra,
        )

    responder(campos["gps"], "6.1671938,-75.5802634", geo_address="Dg. 31 #36 A 80, Ciudad Demo")
    responder(campos["tipo"], "Piston")
    responder(campos["filtro"], "APROBO")
    responder(campos["alerta"], "ALERTA", notes="Correa con desgaste")
    responder(campos["sinaplicar"], "NA")
    responder(campos["fuga"], "false")
    responder(campos["presion"], "95")
    for n, (valor, estado) in enumerate((("32.5", "APROBO"), ("31.5", "FALLO")), start=1):
        responder(campos["corriente"], valor, n)
        responder(campos["estado"], estado, n)
    ChecklistResponse.objects.filter(pk=r.pk).update(completed_at=ahora - timedelta(minutes=10), completed_by=tec)

    Photo.objects.create(work_order=orden, task=orden.tasks.get(), file_url="a.png", taken_at=ahora - timedelta(minutes=45),
                         file_hash="a" * 64, uploaded_by=tec, caption="Filtros instalados", stage="AFTER")
    Photo.objects.create(work_order=orden, task=orden.tasks.get(), file_url="b.png", taken_at=ahora - timedelta(minutes=48),
                         file_hash="b" * 64, uploaded_by=tec, caption="Filtros viejos", stage="BEFORE")
    for tipo, nombre, rol in (("TECHNICIAN", "Tomas Tecnico", "Técnico"), ("CLIENT", "Clara Cliente", "Mantenimiento")):
        Signature.objects.create(work_order=orden, signature_type=tipo, file_url="s.png", signer_name=nombre,
                                 signer_role=rol, file_hash="c" * 64, signed_at=ahora - timedelta(minutes=5))
    Finding.objects.create(work_order=orden, asset=activo, description="Fuga leve en la union", severity="MEDIUM",
                           reported_by=tec, resolved_on_site=True, resolution_notes="Se ajusto la union")
    filtro = InventoryItem.objects.create(name="Filtro de admision", code="FIL-1", unit_of_measure="und")
    StockMovement.objects.create(item=filtro, movement_type="OUT", quantity=Decimal("2"), work_order=orden,
                                 performed_by=tec)
    WorkOrder.objects.filter(pk=orden.pk).update(
        status=WorkOrder.Status.COMPLETED, completed_at=ahora, rating=5, downtime=timedelta(hours=2),
        notes="Cambio de filtros de admision", estimated_duration=timedelta(hours=2, minutes=10),
    )
    # Nombres fijos: baker inventa nombres de ~150 letras al azar que ensucian el acta de muestra.
    User.objects.filter(pk=admin.pk).update(first_name="Ana", last_name="Aprobadora")
    orden.status_history.create(from_status="IN_REVIEW", to_status="COMPLETED", changed_by=admin)
    orden.refresh_from_db()
    return orden


def _html(ot):
    return acta_html(ot)[0]


def _config(options=None, **campos):
    """Cambia la configuracion vigente (la unica fila), tambien despues de generar un acta."""
    ajustes = ReportSettings.current()
    ajustes.options = options or {}
    for campo, valor in campos.items():
        setattr(ajustes, campo, valor)
    ajustes.save()


# ── Encabezado ────────────────────────────────────────────────────────────────

def test_encabezado_con_razon_social_nit_y_calificacion(rico):
    _config(**EMPRESA)
    texto = _texto(_html(rico))
    assert "Gases Demo S.A." in texto and "NIT 900.000.000-0" in texto
    assert "Orden de trabajo" in texto
    assert f"N°: {rico.wo_code}" in texto
    assert "Calificación: 5" in texto
    assert re.search(r'Fecha: <span class="rojo">\d{2}/\d{2}/\d{4}</span>', _html(rico))


def test_encabezado_sin_razon_social_no_deja_huecos_ni_codigo_fijo(rico):
    html = _html(rico)
    assert "Gases Demo" not in html
    assert 'class="empresa"' not in html
    assert "Orden de trabajo" in _texto(html)
    # Nada de razon social ni NIT en el codigo del acta.
    assert ReportSettings.current().company_name == ""
    assert ReportSettings.current().company_tax_id == ""


def test_encabezado_solo_con_nit_o_solo_con_razon_social(rico):
    _config(company_name="Gases Demo S.A.")
    html = _html(rico)
    assert "Gases Demo S.A." in html and "NIT" not in _texto(html)


def test_sin_calificacion_no_sale_la_linea(rico):
    WorkOrder.objects.filter(pk=rico.pk).update(rating=None)
    rico.refresh_from_db()
    assert "Calificación" not in _texto(_html(rico))


def test_la_calificacion_tiene_su_interruptor(rico):
    _config(options={"encabezado_calificacion": False})
    assert "Calificación" not in _texto(_html(rico))


# ── Primer recuadro ───────────────────────────────────────────────────────────

def test_primer_recuadro_trae_genero_responsable_duracion_y_notas(rico):
    texto = _texto(_html(rico))
    for dato in ("Generó: Carla Creadora", "Responsable: Tomas Tecnico",
                 "Duración estimada: 2 h 10 min", "Notas: Cambio de filtros de admision",
                 "Hospital: Hospital Demo Norte"):
        assert dato in texto, dato


@pytest.mark.parametrize("clave, rotulo", [
    ("visita_genero", "Generó"),
    ("visita_ejecutor", "Responsable"),
    ("visita_notas", "Notas:"),
])
def test_cada_dato_del_primer_recuadro_se_apaga(rico, clave, rotulo):
    _config(options={clave: False})
    assert rotulo not in _texto(_html(rico))


# ── Activos ───────────────────────────────────────────────────────────────────

def test_el_activo_se_describe_como_en_fracttal(rico):
    texto = _texto(_html(rico))
    assert "Descripción: Generador de aire medicinal marca EQUIPOS DEMO modelo DX-300 serie SN-0001 cód. GEN-1125" in texto
    assert "Ubicado en: Hospital Demo/Cuarto de aire medicinal" in texto
    assert "Ciudad Demo" in texto
    for dato in ("Clasificación 1: HOSPITAL", "Clasificación 2: CONTRATO PREVENTIVO",
                 "Tipo de equipo: Planta", "Prioridad: Alta", "Código de barras: 1125"):
        assert dato in texto, dato


@pytest.mark.parametrize("clave, dato", [
    ("activo_clasificaciones", "CONTRATO PREVENTIVO"),
    ("activo_codigo_barras", "Código de barras"),
    ("activo_tipo", "Tipo de equipo"),
    ("activo_fabricante", "EQUIPOS DEMO"),
    ("activo_modelo", "DX-300"),
    ("activo_serie", "SN-0001"),
])
def test_los_datos_del_activo_se_apagan(rico, clave, dato):
    _config(options={clave: False})
    assert dato not in _texto(_html(rico))


def test_la_prioridad_del_activo_se_apaga(rico):
    _config(options={"activo_prioridad": False})
    assert "Prioridad: Alta" not in _texto(_html(rico))


def test_no_se_inventan_campos_que_el_activo_no_tiene(rico):
    Asset.objects.filter(pk=rico.tasks.get().asset_id).update(barcode="", classification_1="", classification_2="")
    texto = _texto(_html(rico))
    for etiqueta in ("Código de barras", "Clasificación 1", "Clasificación 2", "Centro de costo"):
        assert etiqueta not in texto, etiqueta


# ── Tareas planificadas ───────────────────────────────────────────────────────

def test_la_tarea_trae_activador_fechas_reales_tipo_y_paro(rico):
    texto = _texto(_html(rico))
    assert "MANTENIMIENTO DE PLANTA GENERADORA DE AIRE MEDICINAL" in texto
    for dato in ("Activador: Cada 6 meses", "Tipo de tarea: Preventivo", "Duración estimada: 2 h 10 min",
                 "Tiempo real de paro del activo: 2 h", "Fecha y hora de inicio:", "Fecha y hora de finalización:",
                 "Tiempo de ejecución: 40 min", "Fecha programada:"):
        assert dato in texto, dato
    inicio = timezone.localtime(timezone.now() - timedelta(minutes=50)).strftime("%H:%M")
    assert inicio in texto


@pytest.mark.parametrize("clave, rotulo", [
    ("tarea_activador", "Activador"),
    ("tarea_tipo", "Tipo de tarea"),
    ("tarea_paro", "Tiempo real de paro"),
    ("visita_trabajo_en_campo", "Fecha y hora de inicio"),
    ("visita_duracion", "Tiempo de ejecución"),
    ("visita_fecha_programada", "Fecha programada"),
])
def test_cada_dato_de_la_tarea_se_apaga(rico, clave, rotulo):
    _config(options={clave: False})
    assert rotulo not in _texto(_html(rico))


def test_sin_paro_ni_protocolo_la_tarea_no_los_inventa(rico):
    WorkOrder.objects.filter(pk=rico.pk).update(downtime=None)
    Task.objects.filter(work_order=rico).update(plan_task=None)
    rico.refresh_from_db()
    texto = _texto(_html(rico))
    assert "Tiempo real de paro" not in texto and "Activador" not in texto


def test_el_activador_segun_el_tipo_de_disparador():
    pt = PlanTask(trigger=PlanTask.Trigger.DATE, frequency_value=1, frequency_unit="MONTHS")
    assert _activador(pt) == "Cada 1 mes"
    assert _activador(PlanTask(trigger=PlanTask.Trigger.DATE, frequency_value=2, frequency_unit="YEARS")) == "Cada 2 años"
    assert _activador(PlanTask(trigger=PlanTask.Trigger.EVENT)) == "Por evento"
    horas = MeterUnit(symbol="h", name="HORAS")
    cada = PlanTask(trigger=PlanTask.Trigger.EVERY, meter_unit=horas, meter_interval=Decimal("500.000"))
    assert _activador(cada) == "Cada 500 h"
    cuando = PlanTask(trigger=PlanTask.Trigger.WHEN, meter_unit=horas, meter_comparator="GTE",
                      meter_threshold=Decimal("1000.000"))
    assert _activador(cuando) == "Cuando HORAS sea mayor o igual a 1000"
    assert _activador(None) == ""


# ── Subtareas ─────────────────────────────────────────────────────────────────

def test_la_primera_fila_de_subtareas_es_la_localizacion(rico):
    html = _html(rico)
    subtareas = html[html.index(">Subtareas<"):]
    assert subtareas.index("LOCALIZACION") < subtareas.index("Piston")
    for dato in ("Dg. 31 #36 A 80, Ciudad Demo", "6.1671938", "-75.5802634"):
        assert dato in subtareas
    assert re.search(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}", subtareas)


def test_las_subtareas_son_una_tabla_de_tres_columnas_con_grupo(rico):
    html = _html(rico)
    assert "<th>Componente</th><th>Qué se revisó</th><th>Resultado</th>" in html
    fila = re.search(r'<td class="grupo">COMPRESOR</td>\s*<td>Indique el tipo de compresor</td>\s*<td>\s*Piston', html)
    assert fila


def test_aprobo_alerta_fallo_se_dibuja_en_casillas_segun_el_valor(rico):
    html = _html(rico)
    assert re.search(r'<span class="cb on primera"></span>Aprobó<span class="cb"></span>Alerta<span class="cb"></span>Falló', html)
    assert re.search(r'<span class="cb primera"></span>Aprobó<span class="cb on"></span>Alerta<span class="cb"></span>Falló', html)
    # N/A sale como texto, no como casillas.
    fila = re.search(r"Revision de purga</td>\s*<td>\s*(.*?)\s*</td>", html, flags=re.S)
    assert fila.group(1) == "N/A"


def test_si_no_se_dibuja_con_casillas(rico):
    html = _html(rico)
    assert re.search(r'Hay fuga</td>\s*<td>\s*<span class="cb primera"></span>Sí<span class="cb on"></span>No', html)


def test_los_resultados_numericos_llevan_su_unidad(rico):
    texto = _texto(_html(rico))
    assert "95 PSI" in texto
    assert "32.5 A" in texto and "31.5 A" in texto, "en el bloque repetible tambien"


def test_el_bloque_repetible_sigue_siendo_tabla_con_su_nombre(rico):
    html = _html(rico)
    assert "MOTOR &times; 2" in html
    assert "<th>Consumo de corriente linea 1</th>" in html
    assert "<th>Estado del motor</th>" in html


def test_las_observaciones_van_con_el_resultado_y_se_apagan(rico):
    assert "Observaciones: Correa con desgaste" in _texto(_html(rico))
    _config(options={"checklist_observaciones": False})
    assert "Correa con desgaste" not in _html(rico)


def test_el_mapa_pequeno_va_en_la_fila_de_localizacion_si_esta_encendido(rico):
    with patch("apps.assets.geo.static_map_data_uri", return_value="data:image/png;base64,AAA") as mapa:
        html = _html(rico)
    assert 'src="data:image/png;base64,AAA"' in html
    assert mapa.call_args.args[:2] == (pytest.approx(6.1671938), pytest.approx(-75.5802634))
    _config(options={"checklist_mapa": False})
    with patch("apps.assets.geo.static_map_data_uri", return_value="data:image/png;base64,AAA"):
        assert "base64,AAA" not in _html(rico)


def test_casillas_por_cadena_aunque_el_tipo_no_exista_en_el_modelo():
    def fr(tipo, valor):
        return SimpleNamespace(field=SimpleNamespace(field_type=tipo), value=valor)

    assert _casillas(fr("PASS_ALERT_FAIL", "FALLO")) == [("Aprobó", False), ("Alerta", False), ("Falló", True)]
    assert _casillas(fr("PASS_ALERT_FAIL", "NA")) is None
    assert _casillas(fr("BOOLEAN", "true")) == [("Sí", True), ("No", False)]
    assert _casillas(fr("BOOLEAN", "na")) is None
    assert _casillas(fr("TEXT", "true")) is None
    assert _casillas(None) is None


def test_valor_numerico_con_y_sin_unidad():
    campo = SimpleNamespace(field_type="NUMBER", options_json={"unit": "PSI"})
    assert _valor(SimpleNamespace(field=campo, value="95")) == "95 PSI"
    sin = SimpleNamespace(field_type="NUMBER", options_json=[])
    assert _valor(SimpleNamespace(field=sin, value="95")) == "95"


# ── Adjuntos ──────────────────────────────────────────────────────────────────

def test_las_fotos_son_adjuntos_de_la_tarea_con_etapa_y_fecha(rico):
    html = _html(rico)
    assert "Adjuntos de la tarea" in html
    assert "<th>Descripción</th><th>Imagen</th>" in html
    assert html.index("Filtros viejos") < html.index("Filtros instalados"), "Antes va primero"
    assert re.search(r'class="etapa"><td colspan="2">Antes</td>', html)
    assert re.search(r"Filtros viejos</div>\s*<div class=\"peq\">\d{2}/\d{2}/\d{4} \d{2}:\d{2}</div>", html)


def test_sin_interruptor_no_hay_adjuntos(rico):
    _config(options={"fotos_activo": False})
    assert "Adjuntos de la tarea" not in _html(rico)


# ── Hallazgos y materiales ────────────────────────────────────────────────────

def test_hallazgos_y_materiales_siguen_con_tabla_con_bordes(rico):
    html = _html(rico)
    assert html.count('<table class="tabla"') == 2, "hallazgos y materiales, con bordes"
    texto = _texto(html)
    assert "Hallazgos encontrados y reportados" in texto and "Materiales utilizados" in texto
    assert "Fuga leve en la union" in texto and "Resuelto en sitio" in texto
    assert "Filtro de admision" in texto
    _config(options={"hallazgos": False, "materiales": False})
    texto = _texto(_html(rico))
    assert "Hallazgos encontrados" not in texto and "Materiales utilizados" not in texto


# ── Firmas, pie y aviso legal ─────────────────────────────────────────────────

def test_las_firmas_van_en_el_orden_de_fracttal(rico):
    html = _html(rico)
    rotulos = re.findall(r'<td class="rotulo">(.*?)</td>', html)
    assert rotulos == ["Aceptado por", "Validado por", "Realizado por"]
    firmas = html[html.index('class="firmas"'):]
    assert firmas.index("Clara Cliente") < firmas.index("Tomas Tecnico"), "cliente a la izquierda, tecnico a la derecha"


def test_la_fecha_del_encabezado_es_la_de_la_orden_no_la_de_emision(rico):
    WorkOrder.objects.filter(pk=rico.pk).update(scheduled_date="2026-03-05")
    rico.refresh_from_db()
    assert 'Fecha: <span class="rojo">05/03/2026</span>' in _html(rico)


def test_validado_por_no_imprime_texto_crudo(rico):
    """Solo sello o imagen, nombre, cargo y fecha: nada de cadenas largas sin espacios."""
    html = _html(rico)
    celda = html[html.index('class="firmas"'):html.index('class="rotulo"')]
    assert not re.search(r"[A-Za-z0-9+/=]{40,}", _texto(celda))
    assert "Ana Aprobadora" in celda and "Aprobado en TodoGas CMMS" in celda


def test_validado_por_es_automatico_con_nombre_cargo_y_fecha(rico):
    html = _html(rico)
    firmas = html[html.index('class="firmas"'):]
    assert "Aprobado en TodoGas CMMS" in firmas, "sin firma dibujada: solo el sello de aprobacion"
    assert "<strong>" + _nombre_admin(rico) in firmas
    assert "Administrador" in firmas


def _nombre_admin(ot):
    h = ot.status_history.filter(to_status="COMPLETED").latest("changed_at")
    u = h.changed_by
    return f"{u.first_name} {u.last_name}".strip() or u.email


def test_las_firmas_apagadas_no_dejan_columnas(rico):
    _config(options={"firma_validado": False})
    rotulos = re.findall(r'<td class="rotulo">(.*?)</td>', _html(rico))
    assert rotulos == ["Aceptado por", "Realizado por"]
    _config({"firma_validado": False, "firma_aceptado": False, "firma_realizado": False})
    assert 'class="firmas"' not in _html(rico)


def test_el_pie_y_el_aviso_legal_siguen(rico):
    html, reporte = acta_html(rico)
    assert 'content: "Realizado con TodoGas CMMS' in html
    assert 'counter(page) " de " counter(pages)' in html
    assert f'Código de verificación: {reporte.content_hash[:16]}' in html
    assert "Ley 527 de 1999" in html and "Decreto 2364 de 2012" in html
    assert f'Hash de integridad: <span class="hash">{reporte.content_hash}</span>' in html


# ── El hash no cambia con la presentacion ─────────────────────────────────────

def test_el_hash_no_depende_de_la_razon_social_ni_del_estilo(rico):
    antes = compute_wo_content_hash(rico)
    _config(**EMPRESA)
    _, reporte = acta_html(rico)
    assert reporte.content_hash == antes == compute_wo_content_hash(rico)


# ── Interruptores ─────────────────────────────────────────────────────────────

def test_los_interruptores_nuevos_estan_encendidos_por_defecto():
    nuevos = {"encabezado_calificacion", "visita_genero", "visita_duracion_estimada", "activo_clasificaciones",
              "activo_prioridad", "activo_codigo_barras", "tarea_tipo", "tarea_activador",
              "tarea_duracion_estimada", "tarea_paro"}
    assert nuevos <= CLAVES
    assert all(efectivas()[k] for k in nuevos)
    assert {c for c, _, _ in CATALOGO} >= nuevos


def test_todo_apagado_sigue_generando_el_acta_con_lo_obligatorio(rico):
    _config(options={c: False for c, _, _ in CATALOGO})
    texto = _texto(_html(rico))
    assert "Hospital Demo Norte" in texto
    assert "Ubicado en" in texto
    assert "Piston" in texto and "Ley 527" in texto


# ── API: razon social y NIT en Formato del acta ───────────────────────────────

def test_la_api_guarda_y_devuelve_razon_social_y_nit(admin):  # noqa: F811
    c = cliente(admin)
    assert c.get(URL).data["company_name"] == ""
    r = c.patch(URL, EMPRESA, format="json")
    assert r.status_code == 200, r.data
    assert r.data["company_name"] == "Gases Demo S.A." and r.data["company_tax_id"] == "NIT 900.000.000-0"
    # Cambiar solo los interruptores no los borra.
    r = c.patch(URL, {"options": {"materiales": False}}, format="json")
    assert r.data["company_name"] == "Gases Demo S.A."
    # Se pueden vaciar.
    r = c.patch(URL, {"company_name": "  ", "company_tax_id": ""}, format="json")
    assert r.data["company_name"] == "" and r.data["company_tax_id"] == ""


def test_la_api_valida_la_razon_social(admin):  # noqa: F811
    c = cliente(admin)
    assert c.patch(URL, {"company_name": "x" * 201}, format="json").status_code == 400
    assert c.patch(URL, {"company_tax_id": 123}, format="json").status_code == 400
    assert c.patch(URL, {}, format="json").status_code == 400


def test_la_vista_previa_usa_la_razon_social_enviada(rico, admin):  # noqa: F811
    visto = {}
    falso = types.ModuleType("weasyprint")

    def HTML(string, base_url=None):
        visto["html"] = string
        return MagicMock(write_pdf=lambda: b"%PDF-previa")

    falso.HTML = HTML
    with patch.dict(sys.modules, {"weasyprint": falso}):
        r = cliente(admin).post(URL + "preview/", {"options": {}, **EMPRESA}, format="json")
    assert r.status_code == 200
    assert "Gases Demo S.A." in visto["html"]
    assert ReportSettings.current().company_name == "", "la vista previa no guarda"


# ── PDF real ──────────────────────────────────────────────────────────────────

def test_el_pdf_real_se_genera_y_se_puede_guardar_de_muestra(rico, admin):  # noqa: F811
    """
    Con WeasyPrint de verdad. Si ACTA_MUESTRA_DIR esta puesta, deja ahi el PDF
    para revisarlo a ojo (se convierte a PNG con PyMuPDF).
    """
    from apps.reports.generator import preview_service_report_pdf

    with patch("apps.reports.generator._resolve_url", return_value=PNG_URI):
        pdf = preview_service_report_pdf(rico, {}, EMPRESA)
    assert pdf.startswith(b"%PDF") and len(pdf) > 5000
    destino = os.environ.get("ACTA_MUESTRA_DIR")
    if destino:
        with open(os.path.join(destino, "nueva.pdf"), "wb") as f:
            f.write(pdf)
