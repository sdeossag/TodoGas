"""API de la fase 2: planes de tareas, tareas pendientes y OT desde pendientes.

Lo que el planificador hace en pantalla, de punta a punta: define las tareas
del plan, asigna el plan a los activos de un piso, ve las pendientes filtradas
por ubicacion, reprograma con causa y arma una OT con las del piso.
"""

from datetime import date, timedelta

import pytest
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from apps.assets.models import Asset, AssetNode, Hospital
from apps.checklists.models import ChecklistTemplate, ChecklistTemplateVersion
from apps.maintenance import services
from apps.maintenance.models import MaintenancePlan, PlanTask, RescheduleCause, Task, TaskReschedule
from apps.maintenance.testing import make_plan, pending_task
from apps.reports.models import GeneratedReport
from apps.users.models import User
from apps.work_orders.models import WorkOrder

HOY = date.today()
pytestmark = pytest.mark.django_db


def cliente(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def admin():
    return baker.make(User, role=User.Role.ADMIN, is_active=True)


@pytest.fixture
def sup():
    return baker.make(User, role=User.Role.SUP, is_active=True)


@pytest.fixture
def tec():
    return baker.make(User, role=User.Role.TEC, is_active=True)


@pytest.fixture
def hospital():
    return baker.make(Hospital, is_active=True, name="Clinica Norte")


@pytest.fixture
def piso3(hospital):
    """Piso 3 con dos habitaciones: filtrar por el piso trae las habitaciones."""
    piso = AssetNode.objects.create(hospital=hospital, name="Piso 3", node_type="FLOOR")
    h301 = AssetNode.objects.create(hospital=hospital, parent=piso, name="Hab 301")
    h302 = AssetNode.objects.create(hospital=hospital, parent=piso, name="Hab 302")
    return piso, h301, h302


def activo(hospital, node=None, **extra):
    extra.setdefault("status", Asset.Status.ACTIVE)
    return baker.make(Asset, hospital=hospital, node=node, **extra)


def plan_vacio(nombre="Tomas de gases"):
    return MaintenancePlan.objects.create(name=nombre)


def ids(resp):
    return {r["id"] for r in resp.json()["results"]}


# ── Tareas del plan ───────────────────────────────────────────────────────────

class TestTareasDelPlan:
    def test_crear_una_tarea_abre_la_pendiente_de_cada_activo(self, admin, hospital):
        plan = plan_vacio()
        a, b = activo(hospital), activo(hospital)
        services.assign_plan_to_assets(plan, [a, b])
        inicio = HOY + timedelta(days=7)

        resp = cliente(admin).post("/api/maintenance/plan-tasks/", {
            "plan": str(plan.id), "name": "Preventivo", "task_type": "PREVENTIVE",
            "frequency_value": 6, "frequency_unit": "MONTHS", "start_date": str(inicio),
        }, format="json")

        assert resp.status_code == status.HTTP_201_CREATED, resp.json()
        assert resp.json()["open_count"] == 2
        pendientes = Task.objects.filter(plan_task_id=resp.json()["id"], status=Task.Status.PENDING)
        assert {t.scheduled_date for t in pendientes} == {inicio}

    def test_hereda_la_prioridad_del_plan(self, admin):
        plan = MaintenancePlan.objects.create(name="Urgentes", priority="HIGH")
        resp = cliente(admin).post("/api/maintenance/plan-tasks/", {
            "plan": str(plan.id), "name": "Revision", "task_type": "PREVENTIVE",
            "frequency_value": 1, "frequency_unit": "MONTHS",
        }, format="json")
        assert resp.json()["priority"] == "HIGH"

    def test_por_fecha_exige_frecuencia(self, admin):
        resp = cliente(admin).post("/api/maintenance/plan-tasks/", {
            "plan": str(plan_vacio().id), "name": "Sin frecuencia", "task_type": "PREVENTIVE",
        }, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "frequency_value" in resp.json()

    def test_por_evento_no_abre_pendientes(self, admin, hospital):
        plan = plan_vacio()
        services.assign_plan_to_assets(plan, [activo(hospital)])
        resp = cliente(admin).post("/api/maintenance/plan-tasks/", {
            "plan": str(plan.id), "name": "Acta de entrega", "task_type": "DELIVERY",
            "trigger": "EVENT", "repeat_count": 1,
        }, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.json()
        assert not Task.objects.filter(plan_task_id=resp.json()["id"]).exists()

    def test_la_ocurrencia_por_evento_la_crea_el_planificador(self, admin, hospital):
        plan = plan_vacio()
        a = activo(hospital)
        services.assign_plan_to_assets(plan, [a])
        pt = PlanTask.objects.create(plan=plan, name="Acta de entrega", trigger="EVENT")
        url = f"/api/maintenance/plan-tasks/{pt.id}/create-occurrence/"

        resp = cliente(admin).post(url, {"asset": str(a.id), "scheduled_date": str(HOY)}, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["status"] == "PENDING"

        otra = cliente(admin).post(url, {"asset": str(a.id), "scheduled_date": str(HOY)}, format="json")
        assert otra.status_code == status.HTTP_400_BAD_REQUEST
        assert "ya tiene esta tarea abierta" in otra.json()["detail"]

    def test_desactivar_por_api_anula_las_pendientes(self, admin, hospital):
        a = activo(hospital)
        plan = make_plan("Alarmas", assets=[a])
        pt = plan.tasks.get()

        resp = cliente(admin).patch(
            f"/api/maintenance/plan-tasks/{pt.id}/", {"is_active": False}, format="json"
        )

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["open_count"] == 0

    def test_no_se_borra_una_tarea_con_historial(self, admin, hospital):
        plan = make_plan("Alarmas", assets=[activo(hospital)])
        resp = cliente(admin).delete(f"/api/maintenance/plan-tasks/{plan.tasks.get().id}/")
        assert resp.status_code == status.HTTP_409_CONFLICT

    def test_se_borra_una_tarea_sin_ocurrencias(self, admin):
        pt = PlanTask.objects.create(plan=plan_vacio(), name="Por error", trigger="EVENT")
        resp = cliente(admin).delete(f"/api/maintenance/plan-tasks/{pt.id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_el_supervisor_no_edita_planes(self, sup):
        resp = cliente(sup).post("/api/maintenance/plan-tasks/", {
            "plan": str(plan_vacio().id), "name": "X", "frequency_value": 1, "frequency_unit": "MONTHS",
        }, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ── Asignar el plan a varios activos ──────────────────────────────────────────

class TestAsignarActivos:
    def test_asigna_y_cambia_de_plan_heredando_la_fecha(self, admin, hospital):
        a, b = activo(hospital, code="T-1"), activo(hospital, code="T-2")
        viejo = make_plan("3 TOMAS", assets=[b], next_due_date=HOY + timedelta(days=40))
        nuevo = make_plan("4 TOMAS", next_due_date=HOY)

        resp = cliente(admin).post(
            f"/api/maintenance/plans/{nuevo.id}/assign-assets/",
            {"asset_ids": [str(a.id), str(b.id)]}, format="json",
        )

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["assigned"] == 2
        assert resp.json()["moved"] == [
            {"code": "T-2", "from_plan": "3 TOMAS", "kept_date": str(HOY + timedelta(days=40))}
        ]
        assert pending_task(nuevo, b).scheduled_date == HOY + timedelta(days=40)
        assert pending_task(viejo, b) is None

    def test_quitar_activos_anula_sus_pendientes(self, admin, hospital):
        a = activo(hospital)
        plan = make_plan("Alarmas", assets=[a])

        resp = cliente(admin).post(
            f"/api/maintenance/plans/{plan.id}/remove-assets/",
            {"asset_ids": [str(a.id)]}, format="json",
        )

        assert resp.json()["removed"] == 1
        a.refresh_from_db()
        assert a.plan is None
        assert Task.objects.get(asset=a).status == Task.Status.CANCELLED

    def test_filtro_de_activos_por_ubicacion_y_plan(self, admin, hospital, piso3):
        piso, h301, _ = piso3
        en_hab = activo(hospital, node=h301)
        en_piso = activo(hospital, node=piso)
        fuera = activo(hospital)
        make_plan("Alarmas", assets=[en_piso])
        c = cliente(admin)

        exacta = c.get("/api/assets/", {"node_id": piso.id})
        con_sub = c.get("/api/assets/", {"node_id": piso.id, "include_sublocations": "true"})
        sin_plan = c.get("/api/assets/", {"plan_id": "none"})

        assert ids(exacta) == {str(en_piso.id)}
        assert ids(con_sub) == {str(en_piso.id), str(en_hab.id)}
        assert ids(sin_plan) == {str(en_hab.id), str(fuera.id)}
        fila = next(r for r in con_sub.json()["results"] if r["id"] == str(en_piso.id))
        assert fila["plan"]["name"] == "Alarmas"


# ── Tareas pendientes ─────────────────────────────────────────────────────────

class TestPendientes:
    def test_filtro_por_ubicacion_incluye_la_sububicacion(self, sup, hospital, piso3):
        piso, h301, h302 = piso3
        a1, a2 = activo(hospital, node=h301), activo(hospital, node=h302)
        fuera = activo(hospital)
        plan = make_plan("Alarmas", assets=[a1, a2, fuera])

        resp = cliente(sup).get("/api/tasks/", {"status": "PENDING", "node_id": piso.id})

        assert resp.status_code == status.HTTP_200_OK
        assert ids(resp) == {str(pending_task(plan, a1).id), str(pending_task(plan, a2).id)}
        fila = resp.json()["results"][0]
        assert fila["asset"]["node_path"].startswith("Piso 3/")
        assert fila["plan"]["name"] == "Alarmas"

    def test_filtros_de_fecha_vencidas_y_plan(self, sup, hospital):
        a, b = activo(hospital), activo(hospital)
        vencido = make_plan("Vencido", assets=[a], next_due_date=HOY - timedelta(days=3))
        futuro = make_plan("Futuro", assets=[b], next_due_date=HOY + timedelta(days=60))
        c = cliente(sup)

        assert ids(c.get("/api/tasks/", {"overdue": "true"})) == {str(pending_task(vencido, a).id)}
        assert ids(c.get("/api/tasks/", {"due_after": str(HOY)})) == {str(pending_task(futuro, b).id)}
        assert ids(c.get("/api/tasks/", {"plan_id": futuro.id})) == {str(pending_task(futuro, b).id)}
        vencida = c.get("/api/tasks/", {"overdue": "true"}).json()["results"][0]
        assert vencida["is_overdue"] is True

    def test_no_muestra_pendientes_de_planes_pausados(self, sup, hospital):
        a = activo(hospital)
        plan = make_plan("Pausado", assets=[a])
        plan.is_active = False
        plan.save()

        assert ids(cliente(sup).get("/api/tasks/", {"status": "PENDING"})) == set()

    def test_fecha_invalida_es_400(self, sup):
        resp = cliente(sup).get("/api/tasks/", {"due_after": "mañana"})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_el_tecnico_no_ve_la_planificacion(self, tec):
        assert cliente(tec).get("/api/tasks/").status_code == status.HTTP_403_FORBIDDEN

    def test_catalogo_de_causas(self, sup):
        nombres = [c["name"] for c in cliente(sup).get("/api/reschedule-causes/").json()]
        assert "APLAZADO" in nombres and "ADELANTADO" in nombres


# ── Reprogramar y anular ──────────────────────────────────────────────────────

class TestReprogramar:
    def test_reprograma_con_causa_y_deja_registro(self, sup, hospital):
        a = activo(hospital)
        plan = make_plan("Alarmas", assets=[a])
        tarea = pending_task(plan, a)
        causa = RescheduleCause.objects.get(name="NO DISPONIBLE")
        nueva = HOY + timedelta(days=14)

        resp = cliente(sup).post(f"/api/tasks/{tarea.id}/reschedule/", {
            "scheduled_date": str(nueva), "cause_id": str(causa.id), "note": "Quirofano ocupado",
        }, format="json")

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["scheduled_date"] == str(nueva)
        assert resp.json()["calculated_date"] == str(HOY)
        assert resp.json()["is_rescheduled"] is True
        historial = cliente(sup).get(f"/api/tasks/{tarea.id}/reschedules/").json()
        assert historial[0]["cause"] == "NO DISPONIBLE"
        assert historial[0]["note"] == "Quirofano ocupado"

    def test_sin_causa_no_se_reprograma(self, sup, hospital):
        a = activo(hospital)
        tarea = pending_task(make_plan("Alarmas", assets=[a]), a)
        resp = cliente(sup).post(
            f"/api/tasks/{tarea.id}/reschedule/", {"scheduled_date": str(HOY)}, format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["cause_id"] == ["La causa es obligatoria."]

    def test_reprogramar_varias(self, sup, hospital):
        a, b = activo(hospital), activo(hospital)
        plan = make_plan("Alarmas", assets=[a, b])
        causa = RescheduleCause.objects.get(name="APLAZADO")

        resp = cliente(sup).post("/api/tasks/reschedule/", {
            "task_ids": [str(pending_task(plan, a).id), str(pending_task(plan, b).id)],
            "scheduled_date": str(HOY + timedelta(days=5)), "cause_id": str(causa.id),
        }, format="json")

        assert resp.json() == {"rescheduled": 2}
        assert TaskReschedule.objects.count() == 2

    def test_anular_varias_exige_nota(self, sup, hospital):
        a = activo(hospital)
        tarea = pending_task(make_plan("Alarmas", assets=[a]), a)
        c = cliente(sup)

        sin_nota = c.post("/api/tasks/cancel/", {"task_ids": [str(tarea.id)], "note": ""}, format="json")
        con_nota = c.post(
            "/api/tasks/cancel/", {"task_ids": [str(tarea.id)], "note": "Equipo retirado"}, format="json"
        )

        assert sin_nota.status_code == status.HTTP_400_BAD_REQUEST
        assert con_nota.json() == {"cancelled": 1}
        tarea.refresh_from_db()
        assert tarea.cancellation_note == "Equipo retirado"


# ── OT desde pendientes ───────────────────────────────────────────────────────

@pytest.fixture
def checklist(admin):
    plantilla = baker.make(ChecklistTemplate, name="Preventivo tomas")
    baker.make(ChecklistTemplateVersion, template=plantilla, version_number=1, is_current=True)
    return plantilla


class TestOTDesdePendientes:
    def test_el_supervisor_arma_la_ot_del_piso(self, sup, tec, hospital, piso3, checklist):
        piso, h301, h302 = piso3
        a1, a2 = activo(hospital, node=h301), activo(hospital, node=h302)
        plan = make_plan("Tomas", assets=[a1, a2], checklist_template=checklist)
        PlanTask.objects.filter(plan=plan).update(estimated_duration=timedelta(minutes=40))
        Task.objects.filter(plan_task__plan=plan).update(estimated_duration=timedelta(minutes=40))
        tareas = [pending_task(plan, a1), pending_task(plan, a2)]

        resp = cliente(sup).post("/api/work-orders/", {
            "task_ids": [str(t.id) for t in tareas],
            "assigned_to": str(tec.id), "scheduled_date": str(HOY + timedelta(days=2)),
            "priority": "HIGH", "location": str(piso.id),
        }, format="json")

        assert resp.status_code == status.HTTP_201_CREATED, resp.json()
        ot = WorkOrder.objects.get(pk=resp.json()["id"])
        assert ot.hospital == hospital and ot.location == piso
        assert ot.assigned_to == tec and ot.priority == "HIGH"
        assert ot.estimated_duration == timedelta(minutes=80)
        assert ot.title == "Preventivo — 2 activos"
        assert len(resp.json()["tasks"]) == 2
        assert resp.json()["warnings"] == []
        for t in tareas:
            t.refresh_from_db()
            assert t.status == Task.Status.SCHEDULED
            assert t.checklist_version.template == checklist

    def test_una_ot_es_de_un_solo_hospital(self, sup, hospital):
        otro = baker.make(Hospital, is_active=True, name="Clinica Sur")
        a, b = activo(hospital), activo(otro)
        plan = make_plan("Alarmas", assets=[a, b])

        resp = cliente(sup).post("/api/work-orders/", {
            "task_ids": [str(pending_task(plan, a).id), str(pending_task(plan, b).id)],
        }, format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "Clinica Norte y Clinica Sur" in str(resp.json())

    def test_solo_pendientes(self, sup, admin, hospital):
        a = activo(hospital)
        tarea = pending_task(make_plan("Alarmas", assets=[a]), a)
        services.create_work_order_for_tasks([tarea], admin)

        resp = cliente(sup).post("/api/work-orders/", {"task_ids": [str(tarea.id)]}, format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "Programada" in str(resp.json())

    def test_la_ubicacion_debe_ser_del_hospital(self, sup, hospital):
        a = activo(hospital)
        tarea = pending_task(make_plan("Alarmas", assets=[a]), a)
        ajena = AssetNode.objects.create(hospital=baker.make(Hospital), name="Piso 1")

        resp = cliente(sup).post("/api/work-orders/", {
            "task_ids": [str(tarea.id)], "location": str(ajena.id),
        }, format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "location" in resp.json()

    def test_el_alta_manual_sigue_siendo_solo_del_admin(self, sup, hospital):
        resp = cliente(sup).post("/api/work-orders/", {
            "asset": str(activo(hospital).id), "task_type": "CORRECTIVE", "title": "Fuga",
            "priority": "HIGH", "scheduled_date": str(HOY),
        }, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ── Tareas del activo ─────────────────────────────────────────────────────────

def test_tareas_del_activo_con_las_tres_fechas_y_el_acta(admin, hospital):
    a = activo(hospital)
    plan = make_plan("Alarmas", assets=[a], next_due_date=HOY - timedelta(days=2))
    tarea = pending_task(plan, a)
    ot, _ = services.create_work_order_for_tasks([tarea], admin)
    ot.status = WorkOrder.Status.COMPLETED
    ot.save()
    services.complete_work_order_tasks(ot)
    acta = GeneratedReport.objects.create(
        work_order=ot, report_type=GeneratedReport.ReportType.WORK_ORDER,
        title="Acta", file_url="acta.pdf", file_hash="f" * 64,
    )

    resp = cliente(admin).get(f"/api/assets/{a.id}/tasks/")

    assert resp.status_code == status.HTTP_200_OK
    [abierta] = resp.json()["open"]
    [hecha] = resp.json()["history"]
    assert abierta["status"] == "PENDING"
    assert hecha["calculated_date"] == str(HOY - timedelta(days=2))
    assert hecha["completed_at"] is not None
    assert hecha["work_order"]["wo_code"] == ot.wo_code
    assert hecha["work_order"]["report_id"] == str(acta.id)
