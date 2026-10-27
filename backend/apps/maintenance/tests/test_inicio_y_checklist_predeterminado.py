"""
Revision del 2026-10-23: fecha de inicio al asignar un protocolo y checklist
predeterminado por activo.

"El contrato lo firmaron hoy y hay que ir manana; ya estan atrasados": al
asignar se puede elegir la fecha de la primera ocurrencia. Y "que pueda
predeterminar que siempre tenga la misma checklist; si la quiero cambiar, la
cambio": el activo guarda una plantilla que completa las tareas de protocolo sin
checklist propio.
"""

import uuid
from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient

from apps.assets.models import Asset, AssetNode, Hospital
from apps.checklists.models import ChecklistTemplate, ChecklistTemplateVersion
from apps.maintenance import services
from apps.maintenance.models import MaintenancePlan, PlanTask, Task
from apps.users.models import User
from apps.work_orders.models import WorkOrder

pytestmark = pytest.mark.django_db


def _user(role):
    return User.objects.create_user(
        email=f"{uuid.uuid4()}@t.co", password="x", first_name="A", last_name="B", role=role,
    )


def _plantilla(nombre, publicada=True, activa=True):
    t = ChecklistTemplate.objects.create(name=nombre, is_active=activa)
    v = None
    if publicada:
        v = ChecklistTemplateVersion.objects.create(template=t, version_number=1, is_current=True)
    return t, v


@pytest.fixture
def d():
    admin = _user(User.Role.ADMIN)
    h = Hospital.objects.create(name="Clinica Norte", code=uuid.uuid4().hex[:8])
    nodo = AssetNode.objects.create(hospital=h, name="Piso 3")
    a1 = Asset.objects.create(hospital=h, node=nodo, name="Alarma 1", code=uuid.uuid4().hex[:8])
    a2 = Asset.objects.create(hospital=h, node=nodo, name="Alarma 2", code=uuid.uuid4().hex[:8])
    plan = MaintenancePlan.objects.create(name=f"ENTREGA {uuid.uuid4().hex[:4]}")
    pt = PlanTask.objects.create(plan=plan, name="Entrega", frequency_value=6, frequency_unit="MONTHS")
    c = APIClient()
    c.force_authenticate(user=admin)
    return {"admin": admin, "h": h, "nodo": nodo, "a1": a1, "a2": a2, "plan": plan, "pt": pt, "c": c}


def _abierta(plan, asset):
    return Task.objects.get(plan_task__plan=plan, asset=asset, status__in=Task.OPEN_STATUSES)


def _post_assets(d, *activos, **extra):
    return d["c"].post(
        f"/api/maintenance/plans/{d['plan'].id}/assign-assets/",
        {"asset_ids": [str(a.id) for a in activos], **extra}, format="json",
    )


# ── Fecha de inicio ───────────────────────────────────────────────────────────

def test_asignar_a_activos_con_fecha_pasada_sale_vencida(d):
    pasada = date.today() - timedelta(days=3)
    r = _post_assets(d, d["a1"], d["a2"], start_date=pasada.isoformat())
    assert r.status_code == 200, r.data
    for a in (d["a1"], d["a2"]):
        t = _abierta(d["plan"], a)
        assert t.scheduled_date == pasada and t.calculated_date == pasada


def test_asignar_a_activos_con_fecha_futura(d):
    futura = date.today() + timedelta(days=40)
    _post_assets(d, d["a1"], start_date=futura.isoformat())
    assert _abierta(d["plan"], d["a1"]).scheduled_date == futura


def test_asignar_sin_fecha_es_como_antes(d):
    d["pt"].start_date = date.today() + timedelta(days=9)
    d["pt"].save()
    _post_assets(d, d["a1"])
    assert _abierta(d["plan"], d["a1"]).scheduled_date == date.today() + timedelta(days=9)
    _post_assets(d, d["a2"], start_date=None)
    assert _abierta(d["plan"], d["a2"]).scheduled_date == date.today() + timedelta(days=9)


def test_la_fecha_elegida_manda_sobre_la_de_la_tarea_del_protocolo(d):
    d["pt"].start_date = date.today() + timedelta(days=90)
    d["pt"].save()
    elegida = date.today() + timedelta(days=1)
    _post_assets(d, d["a1"], start_date=elegida.isoformat())
    assert _abierta(d["plan"], d["a1"]).scheduled_date == elegida


def test_la_fecha_elegida_manda_sobre_la_heredada(d):
    viejo = MaintenancePlan.objects.create(name="VIEJO")
    PlanTask.objects.create(plan=viejo, name="Viejo", frequency_value=1, frequency_unit="YEARS")
    heredable = date.today() + timedelta(days=200)
    services.set_asset_plan(d["a1"], viejo, start_date=heredable)
    services.set_asset_plan(d["a2"], viejo, start_date=heredable)

    # Sin fecha elegida hereda; con ella, manda la elegida.
    r = _post_assets(d, d["a1"])
    assert r.data["moved"][0]["kept_date"] == heredable
    assert _abierta(d["plan"], d["a1"]).scheduled_date == heredable
    elegida = date.today() - timedelta(days=2)
    _post_assets(d, d["a2"], start_date=elegida.isoformat())
    assert _abierta(d["plan"], d["a2"]).scheduled_date == elegida


def test_asignar_a_ubicaciones_con_fecha(d):
    ayer = date.today() - timedelta(days=1)
    r = d["c"].post(
        f"/api/maintenance/plans/{d['plan'].id}/assign-locations/",
        {"node_ids": [str(d["nodo"].id)], "start_date": ayer.isoformat()}, format="json",
    )
    assert r.status_code == 200, r.data
    activo = Asset.objects.get(represents_node=d["nodo"])
    assert _abierta(d["plan"], activo).scheduled_date == ayer


def test_fecha_invalida_se_rechaza(d):
    r = _post_assets(d, d["a1"], start_date="manana")
    assert r.status_code == 400


def test_un_tecnico_no_asigna_protocolos(d):
    c = APIClient()
    c.force_authenticate(user=_user(User.Role.TEC))
    r = c.post(
        f"/api/maintenance/plans/{d['plan'].id}/assign-assets/",
        {"asset_ids": [str(d["a1"].id)], "start_date": "2026-10-01"}, format="json",
    )
    assert r.status_code in (403, 404)
    assert not Task.objects.filter(asset=d["a1"]).exists()


def test_formulario_del_activo_con_fecha_de_inicio(d):
    pasada = date.today() - timedelta(days=5)
    r = d["c"].patch(
        f"/api/assets/{d['a1'].id}/",
        {"plan": str(d["plan"].id), "plan_start_date": pasada.isoformat()}, format="json",
    )
    assert r.status_code == 200, r.data
    assert _abierta(d["plan"], d["a1"]).scheduled_date == pasada


def test_crear_activo_con_protocolo_y_fecha(d):
    futura = date.today() + timedelta(days=12)
    r = d["c"].post("/api/assets/", {
        "hospital": str(d["h"].id), "node": str(d["nodo"].id), "name": "Nuevo",
        "code": uuid.uuid4().hex[:8], "plan": str(d["plan"].id),
        "plan_start_date": futura.isoformat(),
    }, format="json")
    assert r.status_code == 201, r.data
    nuevo = Asset.objects.get(id=r.data["id"])
    assert _abierta(d["plan"], nuevo).scheduled_date == futura


def test_formulario_del_activo_sin_fecha_es_como_antes(d):
    r = d["c"].patch(f"/api/assets/{d['a1'].id}/", {"plan": str(d["plan"].id)}, format="json")
    assert r.status_code == 200, r.data
    assert _abierta(d["plan"], d["a1"]).scheduled_date == date.today()


# ── Checklist predeterminado ──────────────────────────────────────────────────

def _programar(d, asset):
    tarea = _abierta(d["plan"], asset)
    ot = WorkOrder(
        hospital=asset.hospital, created_by=d["admin"], title="OT", scheduled_date=date.today(),
    )
    ot.save()
    avisos = services.schedule_tasks([tarea], ot)
    tarea.refresh_from_db()
    return tarea, avisos


def test_tarea_sin_checklist_usa_el_predeterminado_del_activo(d):
    t, v = _plantilla("Predeterminada")
    d["a1"].default_checklist_template = t
    d["a1"].save()
    services.set_asset_plan(d["a1"], d["plan"])
    tarea, avisos = _programar(d, d["a1"])
    assert tarea.checklist_version_id == v.id
    assert avisos == []


def test_la_de_la_tarea_manda_sobre_la_predeterminada(d):
    pred, _ = _plantilla("Predeterminada")
    propia, v_propia = _plantilla("Propia")
    d["pt"].checklist_template = propia
    d["pt"].save()
    d["a1"].default_checklist_template = pred
    d["a1"].save()
    services.set_asset_plan(d["a1"], d["plan"])
    tarea, _ = _programar(d, d["a1"])
    assert tarea.checklist_version_id == v_propia.id


def test_sin_ninguna_checklist_entra_sin_checklist(d):
    services.set_asset_plan(d["a1"], d["plan"])
    tarea, avisos = _programar(d, d["a1"])
    assert tarea.checklist_version_id is None and avisos == []


def test_predeterminado_sin_version_publicada_avisa(d):
    t, _ = _plantilla("Sin publicar", publicada=False)
    d["a1"].default_checklist_template = t
    d["a1"].save()
    services.set_asset_plan(d["a1"], d["plan"])
    tarea, avisos = _programar(d, d["a1"])
    assert tarea.checklist_version_id is None
    assert any("Sin publicar" in a for a in avisos)


def test_configurar_el_predeterminado_desde_la_ficha(d):
    t, _ = _plantilla("Alarma anual")
    r = d["c"].patch(
        f"/api/assets/{d['a1'].id}/", {"default_checklist_template": str(t.id)}, format="json",
    )
    assert r.status_code == 200, r.data
    ficha = d["c"].get(f"/api/assets/{d['a1'].id}/").data
    assert str(ficha["default_checklist_template"]) == str(t.id)
    assert ficha["default_checklist_template_name"] == "Alarma anual"
    # Se puede quitar y cambiar.
    r = d["c"].patch(f"/api/assets/{d['a1'].id}/", {"default_checklist_template": None}, format="json")
    assert r.status_code == 200
    d["a1"].refresh_from_db()
    assert d["a1"].default_checklist_template_id is None


def test_plantilla_inactiva_no_se_predetermina(d):
    t, _ = _plantilla("Vieja", activa=False)
    r = d["c"].patch(
        f"/api/assets/{d['a1'].id}/", {"default_checklist_template": str(t.id)}, format="json",
    )
    assert r.status_code == 400
