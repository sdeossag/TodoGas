"""
Catalogo de tipos de tarea (decision del 2026-09-23): arranca con los tipos
del cliente en Fracttal, cada tipo dice en que indicador cuenta, lo edita el
administrador y un tipo en uso no se borra.
"""

from datetime import date, timedelta

import pytest
from django.utils import timezone
from model_bakery import baker
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.maintenance.models import TaskTypeCatalog
from apps.maintenance.testing import make_plan, make_work_order
from apps.users.models import User
from apps.work_orders.dashboard import calculate_compliance_percentage, calculate_mttr
from apps.work_orders.models import WorkOrder

pytestmark = pytest.mark.django_db


def cliente(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def admin():
    return baker.make(User, role=User.Role.ADMIN, is_active=True)


@pytest.fixture
def activo():
    h = baker.make(Hospital, is_active=True)
    return Asset.objects.create(hospital=h, name="Compresor", code="CMP-1")


def tipo(code):
    return TaskTypeCatalog.objects.get(code=code)


# ── Lo que trae la migracion ─────────────────────────────────────────────────

def test_arranca_con_los_tipos_del_cliente():
    codigos = set(TaskTypeCatalog.objects.values_list("code", flat=True))
    assert len(codigos) == 20, "los 20 de Fracttal, sin la ubicacion cargada por error"
    assert {"PREVENTIVE", "CORRECTIVE", "CAMBIO_DE_FILTROS", "CAPACITACION", "PRUEBA_DE_REDES"} <= codigos
    assert set(TaskTypeCatalog.objects.filter(is_system=True).values_list("code", flat=True)) == {
        "PREVENTIVE", "CORRECTIVE", "VERIFICATION", "INSTALLATION", "DELIVERY",
    }
    assert tipo("CAMBIO_DE_FILTROS").counts_as == "PREVENTIVE"
    assert tipo("DIAGNOSTICO").counts_as == "CORRECTIVE"
    assert tipo("CAPACITACION").counts_as == "OTHER"


def test_todos_lo_leen_y_solo_el_admin_lo_cambia(admin):
    tec = baker.make(User, role=User.Role.TEC, is_active=True)
    sup = baker.make(User, role=User.Role.SUP, is_active=True)
    TaskTypeCatalog.objects.filter(code="RETIRO").update(is_active=False)
    r = cliente(tec).get("/api/task-types/?active=1")
    assert r.status_code == 200
    assert "RETIRO" not in {t["code"] for t in r.data}
    assert r.data[0]["in_use"] is None, "el conteo de usos es para el administrador"
    assert cliente(sup).post("/api/task-types/", {"name": "X"}, format="json").status_code == 403


# ── Alta y edicion ───────────────────────────────────────────────────────────

def test_el_codigo_sale_del_nombre_y_no_cambia(admin):
    c = cliente(admin)
    r = c.post("/api/task-types/", {"name": "Revisión de válvulas", "counts_as": "PREVENTIVE"}, format="json")
    assert r.status_code == 201, r.data
    assert r.data["code"] == "REVISION_DE_VALVULAS"
    r2 = c.post("/api/task-types/", {"name": "Revision de valvulas!"}, format="json")
    assert r2.data["code"] == "REVISION_DE_VALVULAS_2"
    assert c.post("/api/task-types/", {"name": "Revisión de válvulas"}, format="json").status_code == 400

    r = c.patch(f"/api/task-types/{r.data['id']}/", {"name": "Revisión de válvulas de zona", "code": "OTRO"}, format="json")
    assert r.status_code == 200
    assert r.data["code"] == "REVISION_DE_VALVULAS"


def test_los_tipos_del_sistema_se_protegen(admin):
    c = cliente(admin)
    prev = tipo("PREVENTIVE")
    r = c.patch(f"/api/task-types/{prev.id}/", {"is_active": False}, format="json")
    assert r.status_code == 400 and "is_active" in r.data
    r = c.patch(f"/api/task-types/{prev.id}/", {"counts_as": "OTHER"}, format="json")
    assert r.status_code == 400 and "counts_as" in r.data
    r = c.patch(f"/api/task-types/{prev.id}/", {"name": "Mantenimiento preventivo"}, format="json")
    assert r.status_code == 200
    ver = tipo("VERIFICATION")
    r = c.patch(f"/api/task-types/{ver.id}/", {"counts_as": "PREVENTIVE"}, format="json")
    assert r.status_code == 200, "los demas del sistema si pueden cambiar de indicador"
    assert c.delete(f"/api/task-types/{ver.id}/").status_code == 400


def test_un_tipo_en_uso_no_se_borra(admin, activo):
    c = cliente(admin)
    make_work_order(activo, admin, task_type="RETIRO")
    r = c.delete(f"/api/task-types/{tipo('RETIRO').id}/")
    assert r.status_code == 400 and "Desactivalo" in r.data["detail"]
    assert c.get("/api/task-types/").data[[t["code"] for t in c.get("/api/task-types/").data].index("RETIRO")]["in_use"] == 2
    assert c.delete(f"/api/task-types/{tipo('FIDELIZACION').id}/").status_code == 204


# ── Uso en planes y OTs ──────────────────────────────────────────────────────

def test_la_tarea_del_plan_usa_el_catalogo(admin, activo):
    plan = make_plan("PLAN FILTROS", assets=[activo])
    pt = plan.tasks.first()
    c = cliente(admin)
    r = c.patch(f"/api/maintenance/plan-tasks/{pt.id}/", {"task_type": "CAMBIO_DE_FILTROS"}, format="json")
    assert r.status_code == 200, r.data
    pt.refresh_from_db()
    assert pt.get_task_type_display() == "Cambio de filtros"

    TaskTypeCatalog.objects.filter(code="CAMBIO_DE_FILTROS").update(is_active=False)
    r = c.patch(f"/api/maintenance/plan-tasks/{pt.id}/", {"task_type": "CAMBIO_DE_FILTROS", "name": "Filtros"}, format="json")
    assert r.status_code == 200, "conserva su tipo aunque se haya desactivado"
    r = c.patch(f"/api/maintenance/plan-tasks/{pt.id}/", {"task_type": "NO_EXISTE"}, format="json")
    assert r.status_code == 400 and "task_type" in r.data


def test_la_ot_muestra_el_nombre_del_tipo(admin, activo):
    ot = make_work_order(activo, admin, task_type="DIAGNOSTICO")
    assert ot.get_task_type_display() == "Diagnóstico"
    assert WorkOrder(task_type="VIEJO").get_task_type_display() == "VIEJO"


# ── Indicadores ──────────────────────────────────────────────────────────────

def test_los_indicadores_siguen_al_catalogo(admin, activo):
    hoy = date.today()
    h = activo.hospital.id
    for code in ("PREVENTIVE", "CAMBIO_DE_FILTROS", "CAPACITACION"):
        make_work_order(activo, admin, task_type=code, scheduled_date=hoy)
    assert calculate_compliance_percentage(hospital_id=h)["generated"] == 2, "capacitacion no cuenta"

    ahora = timezone.now()
    for code in ("CORRECTIVE", "DIAGNOSTICO", "RETIRO"):
        ot = make_work_order(activo, admin, task_type=code, status=WorkOrder.Status.COMPLETED)
        WorkOrder.objects.filter(pk=ot.pk).update(started_at=ahora - timedelta(hours=2), completed_at=ahora)
    assert calculate_mttr(hospital_id=h)["sample_size"] == 2, "retiro no cuenta"
