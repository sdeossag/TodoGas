"""
Dar de baja un equipo (decision del 2026-10-01, audio2 11:04): "no se puede
borrar, pero desactivarlo... que se quede ahi, pero que aparezca como
cancelado, para que nos de trazabilidad".

- Sus pendientes se anulan con nota; no se borran.
- Las que ya estan en una OT abierta se dejan y se avisan.
- Fuera de servicio no toca nada; al volver a activo se reabren.
"""

import uuid

import pytest
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.maintenance import services
from apps.maintenance.models import MaintenancePlan, PlanTask, Task
from apps.users.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def d():
    admin = User.objects.create_user(
        email=f"{uuid.uuid4()}@t.co", password="x", first_name="A", last_name="B", role=User.Role.ADMIN,
    )
    h = Hospital.objects.create(name="H", code=uuid.uuid4().hex[:8])
    activo = Asset.objects.create(hospital=h, name="Alarma", code=uuid.uuid4().hex[:8])
    plan = MaintenancePlan.objects.create(name=f"ALARMA {uuid.uuid4().hex[:4]}")
    PlanTask.objects.create(plan=plan, name="Preventivo", frequency_value=6, frequency_unit="MONTHS")
    PlanTask.objects.create(plan=plan, name="Prueba anual", frequency_value=1, frequency_unit="YEARS")
    services.set_asset_plan(activo, plan)
    c = APIClient()
    c.force_authenticate(user=admin)
    return {"admin": admin, "activo": activo, "c": c}


def pendientes(activo):
    return Task.objects.filter(asset=activo, status=Task.Status.PENDING)


def test_dar_de_baja_anula_las_pendientes_sin_borrarlas(d):
    activo = d["activo"]
    assert pendientes(activo).count() == 2
    r = d["c"].post(f"/api/assets/{activo.id}/decommission/")
    assert r.status_code == 200, r.data
    assert r.data["status"] == "DECOMMISSIONED"
    assert r.data["cancelled"] == 2 and r.data["in_work_orders"] == []
    assert pendientes(activo).count() == 0
    anuladas = Task.objects.filter(asset=activo, status=Task.Status.CANCELLED)
    assert anuladas.count() == 2
    assert {t.cancellation_note for t in anuladas} == {services.BAJA_NOTE}


def test_las_que_estan_en_una_ot_se_dejan_y_se_avisan(d):
    activo = d["activo"]
    tarea = pendientes(activo).first()
    wo, _ = services.create_work_order_for_tasks([tarea], d["admin"])
    r = d["c"].post(f"/api/assets/{activo.id}/decommission/")
    assert r.data["cancelled"] == 1
    assert r.data["in_work_orders"] == [wo.wo_code]
    tarea.refresh_from_db()
    assert tarea.status == Task.Status.SCHEDULED, "la de la OT sigue viva"

    # Al cerrar esa OT no se abre la siguiente: el equipo ya no esta activo.
    services.complete_work_order_tasks(wo)
    assert not pendientes(activo).exists()


def test_fuera_de_servicio_no_anula(d):
    activo = d["activo"]
    r = d["c"].patch(f"/api/assets/{activo.id}/", {"status": "OUT_OF_SERVICE"}, format="json")
    assert r.status_code == 200, r.data
    assert pendientes(activo).count() == 2


def test_volver_a_activo_reabre_las_pendientes(d):
    activo = d["activo"]
    d["c"].post(f"/api/assets/{activo.id}/decommission/")
    assert pendientes(activo).count() == 0
    r = d["c"].patch(f"/api/assets/{activo.id}/", {"status": "ACTIVE"}, format="json")
    assert r.status_code == 200, r.data
    assert pendientes(activo).count() == 2


def test_dar_de_baja_desde_el_formulario_tambien_anula(d):
    activo = d["activo"]
    r = d["c"].patch(f"/api/assets/{activo.id}/", {"status": "DECOMMISSIONED"}, format="json")
    assert r.status_code == 200, r.data
    assert pendientes(activo).count() == 0


def test_dar_de_baja_dos_veces_no_hace_nada_mas(d):
    activo = d["activo"]
    d["c"].post(f"/api/assets/{activo.id}/decommission/")
    r = d["c"].post(f"/api/assets/{activo.id}/decommission/")
    assert r.data["cancelled"] == 0
