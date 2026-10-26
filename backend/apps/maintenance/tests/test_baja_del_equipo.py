"""
Dar de baja un equipo (decision del 2026-10-01, audio2 11:04): "no se puede
borrar, pero desactivarlo... que se quede ahi, pero que aparezca como
cancelado, para que nos de trazabilidad".

- Sus pendientes se anulan con nota; no se borran.
- Las que ya estan en una OT abierta se dejan y se avisan.
- Fuera de servicio no toca nada; al volver a activo se reabren.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.assets.meters import meter_for, record_manual
from apps.assets.models import Asset, Hospital, MeterUnit
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


# ── A prueba de sorpresas ────────────────────────────────────────────────────

def baja(d):
    return d["c"].post(f"/api/assets/{d['activo'].id}/decommission/")


def reactivar(d):
    return d["c"].patch(f"/api/assets/{d['activo'].id}/", {"status": "ACTIVE"}, format="json")


def test_baja_y_reactivacion_repetidas_no_duplican_pendientes(d):
    activo = d["activo"]
    for _ in range(3):
        assert baja(d).status_code == 200
        assert pendientes(activo).count() == 0
        assert reactivar(d).status_code == 200
        assert pendientes(activo).count() == 2
    # Reactivar de nuevo sin cambio de estado tampoco duplica.
    assert reactivar(d).status_code == 200
    assert pendientes(activo).count() == 2
    assert Task.objects.filter(asset=activo, status=Task.Status.CANCELLED).count() == 6


def test_reactivar_con_el_protocolo_pausado_no_reabre_nada(d):
    activo = d["activo"]
    baja(d)
    activo.plan.is_active = False
    activo.plan.save()
    assert reactivar(d).status_code == 200
    assert pendientes(activo).count() == 0
    # Al reanudar el protocolo vuelven a abrirse.
    activo.plan.is_active = True
    activo.plan.save()
    r = d["c"].patch(f"/api/assets/{activo.id}/", {"status": "OUT_OF_SERVICE"}, format="json")
    assert r.status_code == 200
    reactivar(d)
    assert pendientes(activo).count() == 2


def test_baja_anula_tarea_por_evento_y_no_la_reabre(d):
    activo = d["activo"]
    pt = PlanTask.objects.create(plan=activo.plan, name="Acta", trigger="EVENT")
    services.create_event_task(pt, activo, date.today(), d["admin"])
    assert pendientes(activo).count() == 3
    r = baja(d)
    assert r.data["cancelled"] == 3
    reactivar(d)
    assert pendientes(activo).filter(plan_task=pt).count() == 0, "las de evento las crea el planificador"
    assert pendientes(activo).count() == 2


def test_no_se_crea_tarea_por_evento_en_un_equipo_de_baja(d):
    activo = d["activo"]
    pt = PlanTask.objects.create(plan=activo.plan, name="Acta", trigger="EVENT")
    baja(d)
    activo.refresh_from_db()
    with pytest.raises(services.TaskStateError):
        services.create_event_task(pt, activo, date.today(), d["admin"])
    r = d["c"].post(
        f"/api/maintenance/plan-tasks/{pt.id}/create-occurrence/",
        {"asset": str(activo.id), "scheduled_date": str(date.today())}, format="json",
    )
    assert r.status_code == 400, r.data


def test_baja_con_tarea_por_medidor(d):
    activo = d["activo"]
    plan = MaintenancePlan.objects.create(name=f"HORAS {uuid.uuid4().hex[:4]}")
    pt = PlanTask.objects.create(
        plan=plan, name="Cada 500 H", trigger="EVERY",
        meter_unit=MeterUnit.objects.get(symbol="H"), meter_interval=500,
    )
    services.set_asset_plan(activo, plan)
    meter = meter_for(activo, pt.meter_unit)
    ahora = timezone.now()
    record_manual(meter, Decimal(100), ahora)
    services.set_asset_plan(activo, plan)  # fija el primer vencimiento (600)
    record_manual(meter, Decimal(700), ahora + timedelta(minutes=1))
    assert Task.objects.filter(plan_task=pt, status=Task.Status.PENDING).count() == 1

    assert baja(d).data["cancelled"] == 1
    assert not Task.objects.filter(plan_task=pt, status=Task.Status.PENDING).exists()

    # De baja, otra lectura no abre nada.
    record_manual(meter, Decimal(900), ahora + timedelta(minutes=2))
    assert not Task.objects.filter(plan_task=pt, status=Task.Status.PENDING).exists()

    # Activo otra vez: la siguiente lectura la abre (no se reabre sola).
    reactivar(d)
    assert not Task.objects.filter(plan_task=pt, status=Task.Status.PENDING).exists()
    record_manual(meter, Decimal(950), ahora + timedelta(minutes=3))
    assert Task.objects.filter(plan_task=pt, status=Task.Status.PENDING).count() == 1


def test_un_equipo_de_baja_no_recibe_tareas_al_asignarle_protocolo(d):
    activo = d["activo"]
    baja(d)
    otro = MaintenancePlan.objects.create(name=f"OTRO {uuid.uuid4().hex[:4]}")
    PlanTask.objects.create(plan=otro, name="X", frequency_value=1, frequency_unit="MONTHS")
    r = d["c"].post(
        f"/api/maintenance/plans/{otro.id}/assign-assets/", {"asset_ids": [str(activo.id)]}, format="json",
    )
    assert r.status_code == 200, r.data
    assert r.data["inactive"] == [activo.code]
    assert pendientes(activo).count() == 0
    # Al reactivarlo se abren las del protocolo nuevo.
    reactivar(d)
    assert pendientes(activo).count() == 1


def test_un_equipo_de_baja_no_entra_en_una_ot_manual(d):
    activo = d["activo"]
    baja(d)
    r = d["c"].post("/api/work-orders/", {
        "asset": str(activo.id), "task_type": "CORRECTIVE", "title": "X",
        "scheduled_date": str(date.today()),
    }, format="json")
    assert r.status_code == 400, r.data


def test_cancelar_la_ot_de_un_equipo_de_baja_anula_sus_tareas_sin_reemitirlas(d):
    """
    Regla: la baja es definitiva hasta que se reactive. Si la OT que quedaba
    abierta se cancela, sus tareas quedan anuladas y NO vuelven a pendiente
    (los equipos de baja no tienen pendientes). Vale para las del protocolo y
    para las manuales.
    """
    activo = d["activo"]
    tarea = pendientes(activo).first()
    wo, _ = services.create_work_order_for_tasks([tarea], d["admin"])
    manual = services.create_manual_work_order(
        [(activo, None)], d["admin"], title="Correctivo", task_type="CORRECTIVE",
        priority="MEDIUM", scheduled_date=date.today(),
    )
    baja(d)
    activo.refresh_from_db()
    assert services.cancel_work_order_tasks(wo) == []
    assert services.cancel_work_order_tasks(manual) == []
    assert not pendientes(activo).exists()
    tarea.refresh_from_db()
    assert tarea.status == Task.Status.CANCELLED


# ── Vista previa (GET, sin efectos) ──────────────────────────────────────────

def test_vista_previa_cuenta_sin_cambiar_nada(d):
    activo = d["activo"]
    tarea = pendientes(activo).first()
    wo, _ = services.create_work_order_for_tasks([tarea], d["admin"])
    r = d["c"].get(f"/api/assets/{activo.id}/decommission-preview/")
    assert r.status_code == 200, r.data
    assert r.data["will_cancel"] == 1
    assert r.data["in_work_orders"] == [wo.wo_code]
    assert r.data["tasks_in_work_orders"] == 1
    activo.refresh_from_db()
    assert activo.status == "ACTIVE" and pendientes(activo).count() == 1


def test_vista_previa_solo_para_admin(d):
    tec = User.objects.create_user(
        email=f"{uuid.uuid4()}@t.co", password="x", first_name="T", last_name="C", role=User.Role.TEC,
    )
    c = APIClient()
    c.force_authenticate(user=tec)
    assert c.get(f"/api/assets/{d['activo'].id}/decommission-preview/").status_code in (403, 404)
