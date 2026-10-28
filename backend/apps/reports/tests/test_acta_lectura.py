"""
Revision del 2026-10-23: el acta se lee sin ser tecnico. Un cuadro por activo
con su ubicacion y su ficha juntas, etiquetas en lenguaje comun, sin quien
corrigio, sin hora en "Emitido", sin estado y sin datos vacios.
"""

import re
from datetime import timedelta

import pytest
from django.utils import timezone
from model_bakery import baker

from apps.assets.activo_ubicacion import activo_de_ubicacion
from apps.assets.models import Asset, AssetNode, Hospital
from apps.checklists.models import (
    ChecklistField,
    ChecklistFieldResponse,
    ChecklistResponse,
    ChecklistTemplate,
    ChecklistTemplateVersion,
)
from apps.maintenance import services
from apps.maintenance.models import Task
from apps.maintenance.testing import make_plan
from apps.reports.models import ReportSettings
from apps.reports.options import efectivas, numeracion
from apps.reports.tests.test_acta_configurable import acta_html, admin  # noqa: F401
from apps.users.models import User
from apps.work_orders.models import WorkOrder

pytestmark = pytest.mark.django_db


def _ot(admin, activo, plan_name="MANT. ALARMA", respuesta="118 V"):  # noqa: F811
    t = baker.make(ChecklistTemplate, name="Alarma")
    v = baker.make(ChecklistTemplateVersion, template=t, version_number=3, is_current=True)
    campo = baker.make(ChecklistField, version=v, label="Voltaje", field_type="TEXT",
                       group="", is_required=True, sort_order=0)
    plan = make_plan(plan_name, assets=[activo], checklist_template=t,
                     next_due_date=timezone.localdate())
    tarea = Task.objects.get(plan_task__plan=plan, status=Task.Status.PENDING)
    orden, _ = services.create_work_order_for_tasks([tarea], admin, assigned_to=admin)
    r = orden.tasks.get().checklist_response
    ChecklistFieldResponse.objects.create(
        response=r, field=campo, value=respuesta,
        answered_at=timezone.now() - timedelta(minutes=40),
    )
    ChecklistResponse.objects.filter(pk=r.pk).update(completed_at=timezone.now(), completed_by=admin)
    WorkOrder.objects.filter(pk=orden.pk).update(
        status=WorkOrder.Status.COMPLETED, completed_at=timezone.now(),
    )
    orden.refresh_from_db()
    return orden, r, campo


@pytest.fixture
def equipo(admin):  # noqa: F811
    h = baker.make(Hospital, name="Clinica Demo Norte", is_active=True)
    bloque = AssetNode.objects.create(hospital=h, name="Bloque A", address="Calle 10 #20-30")
    piso = AssetNode.objects.create(hospital=h, parent=bloque, name="Piso 1")
    a = baker.make(Asset, hospital=h, node=piso, status=Asset.Status.ACTIVE, code="ALR-1",
                   name="Alarma de gases", asset_type="Alarma", manufacturer="AMICO",
                   model="X-100", serial_number="SN-998", equipment_location="Sala de maquinas")
    return _ot(admin, a)


@pytest.fixture
def ubicacion(admin):  # noqa: F811
    h = baker.make(Hospital, name="Clinica Demo Sur", is_active=True)
    piso = AssetNode.objects.create(hospital=h, name="Piso 3")
    return _ot(admin, activo_de_ubicacion(piso))


def _texto(html):
    """El texto visible: sin etiquetas, sin estilos, espacios normalizados."""
    html = re.sub(r"<style.*?</style>|<!--.*?-->", " ", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def _cuadro_del_activo(html):
    """El HTML del primer cuadro (table.ficha) del primer bloque de activo."""
    inicio = html.index("2.1 ")
    ficha = html.index('class="ficha"', inicio)
    return html[ficha:html.index("</table>", ficha)]


# -- Encabezado ---------------------------------------------------------------

def test_emitido_lleva_solo_la_fecha(equipo):
    html, _ = acta_html(equipo[0])
    assert re.search(r"Emitido: \d{2}/\d{2}/\d{4}\s*<", html)
    assert not re.search(r"Emitido: \d{2}/\d{2}/\d{4} \d{2}:\d{2}", html)


def test_el_acta_no_dice_el_estado_de_la_orden(equipo):
    ot = equipo[0]
    html, _ = acta_html(ot)
    assert "Estado" not in _texto(html)
    assert ot.get_status_display() not in _texto(html)


# -- Correcciones en revision -------------------------------------------------

def test_el_acta_no_dice_quien_corrigio_ni_el_valor_anterior(equipo):
    ot, r, campo = equipo
    sup = baker.make(User, role=User.Role.SUP, is_active=True,
                     first_name="Sandra", last_name="Corrige")
    ChecklistFieldResponse.objects.filter(response=r, field=campo).update(
        value="120 V", corrected_by=sup, corrected_at=timezone.now(),
    )
    texto = _texto(acta_html(ot)[0])
    assert "120 V" in texto
    assert "Corregid" not in texto and "Sandra" not in texto and "Corrige" not in texto
    assert "118 V" not in texto


# -- Un cuadro por activo -----------------------------------------------------

def test_el_activo_trae_su_ubicacion_y_su_ficha_juntas(equipo):
    html, _ = acta_html(equipo[0])
    cuadro = _texto(_cuadro_del_activo(html))
    for dato in ("Bloque A/Piso 1", "Calle 10 #20-30", "ALR-1", "Alarma", "AMICO", "X-100",
                 "SN-998", "Sala de maquinas", "Lista de revisión"):
        assert dato in cuadro, dato
    for etiqueta in ("Ubicación", "Código", "Tipo de equipo", "Fabricante", "Modelo",
                     "Número de serie", "Tarea realizada"):
        assert etiqueta in cuadro, etiqueta


def test_la_ficha_no_se_repite_ni_hay_tabla_resumen(equipo):
    html, _ = acta_html(equipo[0])
    texto = _texto(html)
    assert texto.count("SN-998") == 1
    assert texto.count("AMICO") == 1
    assert texto.count("ALR-1") == 1
    assert "Incompleto" not in texto and "Completo" not in texto
    assert re.findall(r"<h2>(\d+(?:\.\d+)?)\.? ", html)[:3] == ["1", "2.1", "3"]


def test_el_checklist_se_lee_sin_version_ni_jerga(equipo):
    texto = _texto(acta_html(equipo[0])[0])
    assert "Qué se revisó" in texto and "Resultado" in texto
    assert "Checklist" not in texto and " v3" not in texto


def test_interruptores_de_la_ficha_siguen_funcionando(equipo):
    ReportSettings.objects.create(options={
        "activo_fabricante": False, "activo_modelo": False, "activo_serie": False,
        "activo_tipo": False, "activo_ubicacion_equipo": False, "activo_checklist": False,
    })
    html, _ = acta_html(equipo[0])
    for dato in ("AMICO", "X-100", "SN-998", "Sala de maquinas", "Lista de revisión"):
        assert dato not in html, dato
    assert "ALR-1" in html


def test_la_ubicacion_del_cuadro_no_se_puede_apagar(equipo):
    ReportSettings.objects.create(options={"activo_ubicacion": False})
    html, _ = acta_html(equipo[0])
    assert "Bloque A/Piso 1" in _texto(_cuadro_del_activo(html))


# -- Ubicacion como ubicacion -------------------------------------------------

def test_un_activo_que_es_ubicacion_se_lee_como_ubicacion(ubicacion):
    html, _ = acta_html(ubicacion[0])
    texto = _texto(html)
    assert "Ubicación intervenida: Piso 3" in texto
    assert "UBI-" not in html
    assert "Tipo de equipo" not in texto and "Fabricante" not in texto
    assert "Código" not in texto
    assert "Ubicaciones intervenidas" in texto and "Activos intervenidos" not in texto
    assert "Dónde está el equipo" not in texto


# -- Nada vacio ---------------------------------------------------------------

@pytest.mark.parametrize("fixture", ["equipo", "ubicacion"])
def test_ningun_campo_vacio_sale_como_none_o_nulo(request, fixture):
    ot = request.getfixturevalue(fixture)[0]
    texto = _texto(acta_html(ot)[0])
    for malo in ("None", "nulo", "null", "NaN", "undefined"):
        assert malo not in texto, malo


def test_un_dato_sin_valor_no_deja_ni_etiqueta(equipo):
    ot = equipo[0]
    Asset.objects.filter(pk=ot.tasks.get().asset_id).update(
        manufacturer="", model="  ", serial_number="",
    )
    WorkOrder.objects.filter(pk=ot.pk).update(description="", notes="")
    html, _ = acta_html(ot)
    texto = _texto(html)
    for etiqueta in ("Fabricante", "Modelo", "Número de serie", "Descripción del trabajo"):
        assert etiqueta not in texto, etiqueta
    assert "Notas" not in texto


def test_sin_ejecutor_la_fila_no_dice_no_registrado(admin):  # noqa: F811
    h = baker.make(Hospital, is_active=True)
    a = baker.make(Asset, hospital=h, status=Asset.Status.ACTIVE, code="A-2")
    ot, *_ = _ot(admin, a)
    WorkOrder.objects.filter(pk=ot.pk).update(assigned_to=None)
    ChecklistResponse.objects.update(completed_by=None)
    ot.refresh_from_db()
    texto = _texto(acta_html(ot)[0])
    assert "No registrado" not in texto
    assert "Trabajo realizado por" not in texto


# -- Fechas y horas operativas ------------------------------------------------

FECHAS = {
    "visita_fecha_programada": "Fecha programada",
    "visita_trabajo_en_campo": "Fecha y hora del trabajo",
    "visita_duracion": "Tiempo de trabajo",
    "checklist_respondido": "Revisión hecha el",
    "visita_ejecutor": "Trabajo realizado por",
}


def test_las_fechas_operativas_aparecen_por_defecto(equipo):
    texto = _texto(acta_html(equipo[0])[0])
    for etiqueta in FECHAS.values():
        assert etiqueta in texto, etiqueta


@pytest.mark.parametrize("clave", sorted(FECHAS))
def test_cada_interruptor_apaga_solo_lo_suyo(equipo, clave):
    ReportSettings.objects.create(options={clave: False})
    texto = _texto(acta_html(equipo[0])[0])
    assert FECHAS[clave] not in texto
    for otra, etiqueta in FECHAS.items():
        if otra != clave:
            assert etiqueta in texto, etiqueta


def test_sin_fechas_la_tabla_de_la_visita_no_deja_huecos(equipo):
    ReportSettings.objects.create(options={
        "visita_fecha_programada": False, "visita_trabajo_en_campo": False,
        "visita_duracion": False, "visita_ejecutor": False,
        "visita_activos": False,
    })
    html, _ = acta_html(equipo[0])
    visita = html[html.index("1. Datos de la visita"):html.index("2.1 ")]
    celdas = re.findall(r"<td[^>]*>(.*?)</td>", visita, flags=re.S)
    assert celdas and all(_texto(c).strip() for c in celdas)
    assert "Clinica Demo Norte" in visita
    assert "Fecha programada" not in visita


def test_la_numeracion_sigue_sin_huecos_con_secciones_apagadas(equipo):
    ReportSettings.objects.create(options={"hallazgos": False, "fotos_visita": False})
    html, _ = acta_html(equipo[0])
    numeros = re.findall(r"<h2>(\d+)(?:\.\d+)?\.? ", html)
    assert numeros == ["1", "2", "3", "4"], numeros  # visita, activo, materiales, firmas
    assert numeracion(efectivas({"hallazgos": False, "fotos_visita": False})) == {
        "visita": 1, "activos": 2, "materiales": 3, "firmas": 4,
    }


def test_una_ubicacion_con_direccion_conserva_su_fila_de_ubicacion(admin):  # noqa: F811
    h = baker.make(Hospital, is_active=True)
    bloque = AssetNode.objects.create(hospital=h, name="Bloque B", address="Carrera 5 #6-7")
    piso = AssetNode.objects.create(hospital=h, parent=bloque, name="Piso 2")
    ot, *_ = _ot(admin, activo_de_ubicacion(piso))
    cuadro = _texto(_cuadro_del_activo(acta_html(ot)[0]))
    assert "Bloque B/Piso 2" in cuadro and "Carrera 5 #6-7" in cuadro
    assert "UBI-" not in cuadro
