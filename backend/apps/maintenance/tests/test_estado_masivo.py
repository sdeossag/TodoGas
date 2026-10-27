"""
Baja y reactivacion masivas de activos (pedido del cliente, 2026-10-27).

Reactivar "desde hoy" deja las tareas por fecha del protocolo programadas para
hoy; "segun su ultimo mantenimiento" conserva lo de siempre.
"""

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.assets.models import Asset, AssetNode, Hospital
from apps.maintenance import services
from apps.maintenance.models import MaintenancePlan, PlanTask, Task, TaskReschedule
from apps.users.models import User
from apps.work_orders.models import WorkOrder

pytestmark = pytest.mark.django_db

URL = "/api/assets/bulk-status/"
PREVIEW = "/api/assets/bulk-status/preview/"


def _user(role, **extra):
    return User.objects.create_user(
        email=f"{uuid.uuid4()}@t.co", password="x", first_name="A", last_name="B", role=role, **extra,
    )


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _activo(h, plan=None, **extra):
    a = Asset.objects.create(hospital=h, name="Alarma", code=uuid.uuid4().hex[:8], **extra)
    if plan:
        services.set_asset_plan(a, plan)
    return a


@pytest.fixture
def d():
    admin = _user(User.Role.ADMIN)
    h = Hospital.objects.create(name="H", code=uuid.uuid4().hex[:8])
    plan = MaintenancePlan.objects.create(name=f"ALARMA {uuid.uuid4().hex[:4]}")
    PlanTask.objects.create(plan=plan, name="Preventivo", frequency_value=6, frequency_unit="MONTHS")
    PlanTask.objects.create(plan=plan, name="Prueba anual", frequency_value=1, frequency_unit="YEARS")
    activos = [_activo(h, plan) for _ in range(3)]
    return {"admin": admin, "h": h, "plan": plan, "activos": activos, "c": _client(admin)}


def ids(*activos):
    return [str(a.id) for a in activos]


def pendientes(a):
    return Task.objects.filter(asset=a, status=Task.Status.PENDING)


def baja(d, activos=None):
    return d["c"].post(URL, {"asset_ids": ids(*(activos or d["activos"])), "status": "DECOMMISSIONED"}, format="json")


def test_baja_masiva_anula_pendientes_y_avisa_ots(d):
    a1 = d["activos"][0]
    wo, _ = services.create_work_order_for_tasks([pendientes(a1).first()], d["admin"])
    r = baja(d)
    assert r.status_code == 200, r.data
    assert r.data == {
        "changed": 3, "unchanged": 0, "cancelled": 5, "reopened": 0, "in_work_orders": [wo.wo_code],
    }
    for a in d["activos"]:
        a.refresh_from_db()
        assert a.status == "DECOMMISSIONED" and pendientes(a).count() == 0
    assert Task.objects.filter(status=Task.Status.CANCELLED, cancellation_note=services.BAJA_NOTE).count() == 5
    assert AuditLog.objects.filter(entity_type="Asset", action="STATUS_CHANGE").count() == 3


def test_reactivar_desde_hoy_pone_las_fechas_en_hoy(d):
    a1, a2, _ = d["activos"]
    for t in pendientes(a1):
        t.scheduled_date = t.calculated_date = timezone.localdate() - timedelta(days=90)
        t.save()
    baja(d, [a1, a2])
    r = d["c"].post(URL, {"asset_ids": ids(a1, a2), "status": "ACTIVE"}, format="json")
    assert r.status_code == 200, r.data
    assert r.data["changed"] == 2 and r.data["reopened"] == 4
    hoy = timezone.localdate()
    for a in (a1, a2):
        ts = list(pendientes(a))
        assert len(ts) == 2
        assert all(t.scheduled_date == hoy and t.calculated_date == hoy for t in ts)


def test_reactivar_desde_hoy_reprograma_la_pendiente_de_un_fuera_de_servicio(d):
    a1 = d["activos"][0]
    viejo = timezone.localdate() + timedelta(days=45)
    for t in pendientes(a1):
        t.scheduled_date = t.calculated_date = viejo
        t.save()
    a1.status = "OUT_OF_SERVICE"
    a1.save()
    r = d["c"].post(URL, {"asset_ids": ids(a1), "status": "ACTIVE"}, format="json")
    assert r.status_code == 200, r.data
    assert r.data["changed"] == 1 and r.data["reopened"] == 2
    hoy = timezone.localdate()
    assert pendientes(a1).count() == 2
    assert all(t.scheduled_date == hoy and t.calculated_date == hoy for t in pendientes(a1))
    assert TaskReschedule.objects.filter(task__asset=a1, to_date=hoy).count() == 2


def test_reactivar_segun_ultimo_cierre_conserva_el_comportamiento_actual(d):
    a1 = d["activos"][0]
    t = pendientes(a1).get(title="Preventivo")
    hecho = timezone.now() - timedelta(days=200)
    wo, _ = services.create_work_order_for_tasks([t], d["admin"])
    wo.status = WorkOrder.Status.COMPLETED
    wo.completed_at = hecho
    wo.save()
    services.complete_work_order_tasks(wo)
    baja(d, [a1])
    r = d["c"].post(URL, {"asset_ids": ids(a1), "status": "ACTIVE", "start": "last_close"}, format="json")
    assert r.status_code == 200, r.data
    nueva = pendientes(a1).get(title="Preventivo")
    esperada = services.add_frequency(timezone.localdate(hecho), 6, "MONTHS")
    assert nueva.scheduled_date == esperada != timezone.localdate()


def test_los_que_ya_estan_en_el_estado_pedido_son_unchanged(d):
    a1, a2, _ = d["activos"]
    r = d["c"].post(URL, {"asset_ids": ids(a1, a2), "status": "ACTIVE"}, format="json")
    assert r.data["changed"] == 0 and r.data["unchanged"] == 2
    baja(d, [a1])
    r = baja(d, [a1, a2])
    assert r.data["changed"] == 1 and r.data["unchanged"] == 1 and r.data["cancelled"] == 2
    assert AuditLog.objects.filter(action="STATUS_CHANGE", entity_id=a2.id).count() == 1


def test_ids_repetidos_se_deduplican(d):
    a1 = d["activos"][0]
    r = baja(d, [a1, a1])
    assert r.data["changed"] == 1 and r.data["cancelled"] == 2


def test_acepta_ubicaciones(d):
    nodo = AssetNode.objects.create(hospital=d["h"], name="Piso 3")
    ubic = Asset.objects.create(
        hospital=d["h"], node=nodo, represents_node=nodo, name="Piso 3", code=uuid.uuid4().hex[:8],
    )
    services.set_asset_plan(ubic, d["plan"])
    r = baja(d, [ubic, d["activos"][0]])
    assert r.status_code == 200, r.data
    assert r.data["changed"] == 2
    ubic.refresh_from_db()
    assert ubic.status == "DECOMMISSIONED"


def test_sin_permiso_es_403(d):
    c = _client(_user(User.Role.TEC))
    body = {"asset_ids": ids(d["activos"][0]), "status": "DECOMMISSIONED"}
    assert c.post(URL, body, format="json").status_code == 403
    assert c.post(PREVIEW, body, format="json").status_code == 403
    d["activos"][0].refresh_from_db()
    assert d["activos"][0].status == "ACTIVE"


def test_activo_de_otro_hospital_es_400_y_no_cambia_nada(d):
    otro_h = Hospital.objects.create(name="Otro", code=uuid.uuid4().hex[:8])
    ajeno = _activo(otro_h, d["plan"])
    c = _client(_user(User.Role.SUP, hospital=d["h"]))
    r = c.post(URL, {"asset_ids": ids(d["activos"][0], ajeno), "status": "DECOMMISSIONED"}, format="json")
    assert r.status_code == 400
    assert r.data["missing_ids"] == [str(ajeno.id)]
    d["activos"][0].refresh_from_db()
    assert d["activos"][0].status == "ACTIVE"
    r = c.post(URL, {"asset_ids": ids(d["activos"][0]), "status": "DECOMMISSIONED"}, format="json")
    assert r.status_code == 200 and r.data["changed"] == 1


def test_id_inexistente_es_400(d):
    r = d["c"].post(URL, {"asset_ids": [str(uuid.uuid4())], "status": "DECOMMISSIONED"}, format="json")
    assert r.status_code == 400 and len(r.data["missing_ids"]) == 1


def test_limite_de_200(d):
    r = d["c"].post(
        URL, {"asset_ids": [str(uuid.uuid4()) for _ in range(201)], "status": "DECOMMISSIONED"}, format="json",
    )
    assert r.status_code == 400 and "asset_ids" in r.data
    r = d["c"].post(URL, {"asset_ids": [], "status": "DECOMMISSIONED"}, format="json")
    assert r.status_code == 400


def test_estado_o_inicio_invalidos_son_400(d):
    body = {"asset_ids": ids(d["activos"][0])}
    assert d["c"].post(URL, {**body, "status": "OUT_OF_SERVICE"}, format="json").status_code == 400
    assert d["c"].post(URL, {**body, "status": "ACTIVE", "start": "ayer"}, format="json").status_code == 400


def test_preview_cuenta_sin_escribir(d):
    a1 = d["activos"][0]
    wo, _ = services.create_work_order_for_tasks([pendientes(a1).first()], d["admin"])
    r = d["c"].post(PREVIEW, {"asset_ids": ids(*d["activos"]), "status": "DECOMMISSIONED"}, format="json")
    assert r.status_code == 200, r.data
    assert r.data == {
        "changed": 3, "unchanged": 0, "cancelled": 5, "reopened": 0, "in_work_orders": [wo.wo_code],
    }
    for a in d["activos"]:
        a.refresh_from_db()
        assert a.status == "ACTIVE"
    assert Task.objects.filter(status=Task.Status.CANCELLED).count() == 0
    assert not AuditLog.objects.filter(action="STATUS_CHANGE").exists()

    baja(d)  # la tarea de la OT abierta sigue viva: se reabren 5 de 6
    antes = Task.objects.count()
    p = d["c"].post(PREVIEW, {"asset_ids": ids(*d["activos"]), "status": "ACTIVE"}, format="json")
    assert p.data["changed"] == 3 and p.data["reopened"] == 5
    assert Task.objects.count() == antes
    a1.refresh_from_db()
    assert a1.status == "DECOMMISSIONED"
    r = d["c"].post(URL, {"asset_ids": ids(*d["activos"]), "status": "ACTIVE"}, format="json")
    assert {k: r.data[k] for k in p.data} == p.data
