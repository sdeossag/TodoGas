"""
Cumplimiento mensual de un protocolo (GET /api/maintenance/plans/<id>/compliance/).

Dos cosas: que los numeros no cambien (se fijan con datos conocidos) y que el
endpoint no haga dos consultas por mes. Antes eran 24 count() por pedido.
"""

from datetime import date

import pytest
from dateutil.relativedelta import relativedelta
from model_bakery import baker
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.maintenance.models import Task
from apps.maintenance.testing import make_plan
from apps.users.models import User
from apps.work_orders.models import WorkOrder

pytestmark = pytest.mark.django_db


def mes(atras):
    """Primer dia del mes de hace `atras` meses."""
    return date.today().replace(day=1) - relativedelta(months=atras)


@pytest.fixture
def mundo():
    hospital = baker.make(Hospital, is_active=True)
    admin = baker.make(User, role=User.Role.ADMIN, is_active=True)
    plan = make_plan("Protocolo A")
    otro = make_plan("Protocolo B")
    pt, pt_otro = plan.tasks.get(), otro.tasks.get()
    n = [0]

    def tarea(plan_task, atras, estado, dia=10):
        n[0] += 1
        activo = Asset.objects.create(hospital=hospital, name=f"E{n[0]}", code=f"C-{n[0]}",
                                      status=Asset.Status.ACTIVE)
        # La restriccion de la BD exige OT en las programadas y finalizadas.
        ot = None
        if estado in (Task.Status.SCHEDULED, Task.Status.DONE):
            ot = baker.make(WorkOrder, hospital=hospital, created_by=admin)
        return baker.make(Task, asset=activo, plan_task=plan_task, status=estado,
                          scheduled_date=mes(atras).replace(day=dia), work_order=ot)

    S = Task.Status
    # Este mes: 2 hechas + 1 pendiente (+ 1 cancelada, que no cuenta) => 3, 2, 66.7
    tarea(pt, 0, S.DONE); tarea(pt, 0, S.DONE, dia=28); tarea(pt, 0, S.PENDING)
    tarea(pt, 0, S.CANCELLED)
    # Hace 1 mes: 1 hecha => 1, 1, 100.0
    tarea(pt, 1, S.DONE)
    # Hace 3 meses: 2 programadas => 2, 0, 0.0
    tarea(pt, 3, S.SCHEDULED); tarea(pt, 3, S.SCHEDULED)
    # Hace 11 meses (el mas antiguo de la ventana): 1 hecha
    tarea(pt, 11, S.DONE)
    # Fuera de la ventana (hace 12 meses) y de otro protocolo: no cuentan
    tarea(pt, 12, S.DONE)
    tarea(pt_otro, 0, S.DONE)
    c = APIClient()
    c.force_authenticate(user=admin)
    return {"c": c, "plan": plan}


def pedir(m):
    return m["c"].get(f"/api/maintenance/plans/{m['plan'].id}/compliance/")


def test_el_cumplimiento_trae_doce_meses_del_mas_antiguo_al_actual(mundo):
    r = pedir(mundo)
    assert r.status_code == 200
    assert r.data["plan_id"] == str(mundo["plan"].id)
    assert r.data["plan_name"] == "Protocolo A"
    meses = [(f["year"], f["month"]) for f in r.data["monthly"]]
    esperado = [(mes(i).year, mes(i).month) for i in range(11, -1, -1)]
    assert meses == esperado


def test_el_cumplimiento_fija_totales_y_porcentajes_por_mes(mundo):
    por_mes = {(f["year"], f["month"]): f for f in pedir(mundo).data["monthly"]}

    def fila(atras):
        f = por_mes[(mes(atras).year, mes(atras).month)]
        return f["total"], f["completed"], f["percentage"]

    assert fila(0) == (3, 2, 66.7)     # la cancelada no cuenta
    assert fila(1) == (1, 1, 100.0)
    assert fila(3) == (2, 0, 0.0)
    assert fila(11) == (1, 1, 100.0)
    for vacio in (2, 4, 5, 6, 7, 8, 9, 10):
        assert fila(vacio) == (0, 0, None), f"mes de hace {vacio}"


def test_el_cumplimiento_no_cuenta_otros_protocolos_ni_fuera_de_la_ventana(mundo):
    total = sum(f["total"] for f in pedir(mundo).data["monthly"])
    assert total == 3 + 1 + 2 + 1


def test_el_cumplimiento_usa_un_numero_constante_de_consultas(mundo, django_assert_max_num_queries):
    # Sesion + usuario + plan + una o dos agregaciones. Lo que importa es que
    # no dependa de los 12 meses (antes: 24 count()).
    with django_assert_max_num_queries(6):
        r = pedir(mundo)
    assert r.status_code == 200
