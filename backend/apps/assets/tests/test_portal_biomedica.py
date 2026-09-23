"""
Portal de la biomedica (decision del 2026-09-23): sus equipos con el
historial de cada uno y los mantenimientos programados con su cumplimiento.
No ve OTs en curso ni tareas anuladas.
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from model_bakery import baker
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.maintenance import services
from apps.maintenance.models import Task
from apps.maintenance.testing import make_plan
from apps.users.models import User

pytestmark = pytest.mark.django_db
HOY = timezone.localdate()


def cliente(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def datos():
    a = baker.make(Hospital, is_active=True)
    b = baker.make(Hospital, is_active=True)
    admin = baker.make(User, role=User.Role.ADMIN, is_active=True)
    cli = baker.make(User, role=User.Role.CLI, is_active=True, hospital=a)
    activo = Asset.objects.create(hospital=a, name="Alarma", code="ALR", status=Asset.Status.ACTIVE)
    ajeno = Asset.objects.create(hospital=b, name="Alarma B", code="ALR-B", status=Asset.Status.ACTIVE)
    return {"a": a, "admin": admin, "cli": cli, "activo": activo, "ajeno": ajeno}


def tarea(activo, dias, nombre="MANT"):
    """Tarea pendiente de plan con fecha HOY + dias."""
    plan = make_plan(f"{nombre}-{Task.objects.count()}", assets=[activo],
                     next_due_date=HOY + timedelta(days=dias))
    return Task.objects.get(plan_task__plan=plan, status=Task.Status.PENDING)


def hecha(t, admin, dias_tarde=0):
    """La tarea pasa a DONE con su OT finalizada, `dias_tarde` despues de su fecha."""
    ot, _ = services.create_work_order_for_tasks([t], admin)
    ot.status = "COMPLETED"
    ot.completed_at = timezone.now()
    ot.save()
    services.complete_work_order_tasks(ot)
    cuando = timezone.make_aware(
        timezone.datetime.combine(t.scheduled_date + timedelta(days=dias_tarde), timezone.datetime.min.time())
    ) + timedelta(hours=12)
    Task.objects.filter(pk=t.pk).update(completed_at=cuando)
    return ot


def test_la_biomedica_ve_el_historial_de_su_equipo(datos):
    hecho = tarea(datos["activo"], -30)
    ot = hecha(hecho, datos["admin"])
    anulada = tarea(datos["activo"], -10, "ANUL")
    services.cancel_tasks([anulada], "Retirado")
    proxima = tarea(datos["activo"], 20, "PROX")

    r = cliente(datos["cli"]).get(f"/api/assets/{datos['activo'].id}/tasks/")
    assert r.status_code == 200
    historial = r.data["history"]
    assert [h["id"] for h in historial] == [str(hecho.id)], "sin las anuladas"
    assert historial[0]["work_order"]["wo_code"] == ot.wo_code
    assert str(proxima.id) in {x["id"] for x in r.data["open"]}


def test_de_lo_que_viene_no_ve_la_ot_en_curso(datos):
    t = tarea(datos["activo"], 3)
    services.create_work_order_for_tasks([t], datos["admin"])
    r = cliente(datos["cli"]).get(f"/api/assets/{datos['activo'].id}/tasks/")
    abierta = next(x for x in r.data["open"] if x["id"] == str(t.id))
    assert abierta["work_order"] is None


def test_lo_que_viene_no_incluye_la_ot_manual_en_curso(datos):
    """Una OT manual abierta es trabajo en curso: no es un mantenimiento vencido."""
    from apps.maintenance.services import create_manual_work_order

    proxima = tarea(datos["activo"], 20)
    create_manual_work_order(
        [(datos["activo"], None)], datos["admin"],
        title="Correctivo", task_type="CORRECTIVE", scheduled_date=HOY - timedelta(days=3),
    )
    r = cliente(datos["cli"]).get(f"/api/assets/{datos['activo'].id}/tasks/")
    assert [x["id"] for x in r.data["open"]] == [str(proxima.id)]


def test_no_ve_el_historial_de_equipos_de_otro_hospital(datos):
    r = cliente(datos["cli"]).get(f"/api/assets/{datos['ajeno'].id}/tasks/")
    assert r.status_code == 404


def test_el_tecnico_sigue_sin_ver_el_historial_por_aqui(datos):
    tec = baker.make(User, role=User.Role.TEC, is_active=True)
    assert cliente(tec).get(f"/api/assets/{datos['activo'].id}/tasks/").status_code == 403


def otro_activo(hospital):
    """Cada activo tiene un solo plan: asignarle otro anula las pendientes del anterior."""
    n = Asset.objects.count()
    return Asset.objects.create(hospital=hospital, name=f"Toma {n}", code=f"T-{n}",
                                status=Asset.Status.ACTIVE)


def test_el_resumen_trae_lo_que_viene_y_el_cumplimiento(datos):
    a = datos["a"]
    hecha(tarea(otro_activo(a), -60), datos["admin"])                 # a tiempo
    hecha(tarea(otro_activo(a), -40), datos["admin"], dias_tarde=5)   # tarde
    vencida = tarea(otro_activo(a), -5)                               # sin hacer
    proxima = tarea(otro_activo(a), 15)
    ajena = tarea(datos["ajeno"], 10)                                 # de otro hospital

    r = cliente(datos["cli"]).get("/api/client-portal/summary/").data
    ids = [x["task_id"] for x in r["upcoming"]]
    # Por fecha. Detras vienen las siguientes de las dos hechas (a 6 meses).
    assert ids[:2] == [str(vencida.id), str(proxima.id)]
    assert len(ids) == 4
    assert str(ajena.id) not in ids
    assert r["upcoming"][0]["is_overdue"] is True
    assert r["overdue_count"] == 1
    assert r["compliance"] == {
        "period_days": 365, "planned": 3, "done": 2, "on_time": 1, "percentage": 67,
    }
