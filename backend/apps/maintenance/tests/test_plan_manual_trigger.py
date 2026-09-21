"""«Disparar ahora» no debe hacer desaparecer la ejecucion programada.

Regresion (bug 3): el disparo manual y la corrida diaria llamaban a la misma
funcion sin distinguirse, y un disparo anticipado adelantaba el calendario un
periodo completo: la ejecucion que tocaba desaparecia sin dejar rastro.

Con el modelo de tareas (diseno aprobado el 2026-09-21) la regla es la de
Fracttal:

  - disparo manual ANTES del vencimiento -> la tarea pendiente se reprograma a
    hoy con causa ADELANTADO, queda registrado, y la OT es para hoy. La fecha
    calculada no cambia nunca.
  - la siguiente fecha se calcula al cerrar la OT: con programacion fija, desde
    la fecha calculada (el ciclo no se corre, que era la proteccion del bug 3);
    sin ella, que es el defecto y como trabaja el cliente, desde la realizacion.
  - disparo manual de una pendiente ya vencida, o corrida automatica -> la OT
    toma la fecha programada de la pendiente, sin reprogramar nada.
"""

from datetime import date, timedelta

import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from model_bakery import baker

from apps.assets.models import Asset, Hospital
from apps.maintenance import services
from apps.maintenance.engine import generate_work_orders_for_plan
from apps.maintenance.models import MaintenancePlanExecution, Task, TaskReschedule
from apps.maintenance.testing import make_plan, pending_task
from apps.users.models import User
from apps.work_orders.models import WorkOrder

FREQ_MONTHS = 6


@pytest.fixture
def admin_user(db):
    return baker.make(User, role=User.Role.ADMIN, is_active=True)


@pytest.fixture
def hospital(db):
    return baker.make(Hospital, is_active=True)


@pytest.fixture
def asset(db, hospital):
    return baker.make(Asset, hospital=hospital, status=Asset.Status.ACTIVE)


def plan_con_pendiente(asset, due, fixed_schedule=False):
    return make_plan(
        "Plan alarma", assets=[asset], next_due_date=due,
        frequency_value=FREQ_MONTHS, fixed_schedule=fixed_schedule,
    )


def only_work_order(plan):
    return WorkOrder.objects.get(tasks__plan_task__plan=plan)


def cerrar(work_order, cuando):
    """Completa la OT en `cuando` y cierra sus tareas como lo haria la transicion."""
    work_order.status = WorkOrder.Status.COMPLETED
    work_order.completed_at = cuando
    work_order.save()
    return services.complete_work_order_tasks(work_order)


# ── Disparo manual anticipado: se adelanta con causa ─────────────────────────

def test_manual_trigger_before_due_schedules_ot_for_today(asset, admin_user):
    plan = plan_con_pendiente(asset, date.today() + timedelta(days=90))

    result = generate_work_orders_for_plan(plan, triggered_by=admin_user, manual=True)

    assert result['created'] == 1
    assert only_work_order(plan).scheduled_date == date.today()


def test_manual_trigger_before_due_keeps_calculated_date(asset, admin_user):
    due = date.today() + timedelta(days=90)
    plan = plan_con_pendiente(asset, due)

    generate_work_orders_for_plan(plan, triggered_by=admin_user, manual=True)

    tarea = Task.objects.get(plan_task__plan=plan, asset=asset)
    assert tarea.calculated_date == due, 'el disparo anticipado no borra la fecha calculada'
    assert tarea.scheduled_date == date.today()


def test_manual_trigger_before_due_is_recorded_as_adelantado(asset, admin_user):
    due = date.today() + timedelta(days=90)
    plan = plan_con_pendiente(asset, due)

    result = generate_work_orders_for_plan(plan, triggered_by=admin_user, manual=True)

    registro = TaskReschedule.objects.get(task__plan_task__plan=plan)
    assert registro.cause.name == 'ADELANTADO'
    assert registro.from_date == due
    assert registro.to_date == date.today()
    assert registro.changed_by == admin_user
    assert any('ADELANTADO' in w for w in result['warnings'])


def test_manual_trigger_still_records_generation(asset, admin_user):
    plan = plan_con_pendiente(asset, date.today() + timedelta(days=90))

    generate_work_orders_for_plan(plan, triggered_by=admin_user, manual=True)

    assert MaintenancePlanExecution.objects.filter(plan=plan).count() == 1


# ── La siguiente fecha: fija o desde la realizacion ──────────────────────────

def test_fixed_schedule_keeps_cycle_after_early_execution(asset, admin_user):
    """La proteccion original del bug 3: con programacion fija, adelantar una
    visita no corre el ciclo."""
    due = date.today() + timedelta(days=90)
    plan = plan_con_pendiente(asset, due, fixed_schedule=True)
    generate_work_orders_for_plan(plan, triggered_by=admin_user, manual=True)

    cerrar(only_work_order(plan), timezone.now())

    siguiente = pending_task(plan, asset)
    assert siguiente.calculated_date == due + relativedelta(months=FREQ_MONTHS)


def test_floating_schedule_counts_from_completion(asset, admin_user):
    """Sin programacion fija (el defecto, como el cliente en Fracttal) la
    siguiente se cuenta desde el dia en que se hizo."""
    plan = plan_con_pendiente(asset, date.today() + timedelta(days=90))
    generate_work_orders_for_plan(plan, triggered_by=admin_user, manual=True)
    hecho = timezone.now()

    cerrar(only_work_order(plan), hecho)

    siguiente = pending_task(plan, asset)
    esperado = timezone.localdate(hecho) + relativedelta(months=FREQ_MONTHS)
    assert siguiente.calculated_date == esperado
    assert siguiente.scheduled_date == esperado


# ── Pendiente ya vencida y corrida programada: sin reprogramar ───────────────

def test_manual_trigger_when_overdue_uses_due_date(asset, admin_user):
    due = date.today() - timedelta(days=1)
    plan = plan_con_pendiente(asset, due)

    result = generate_work_orders_for_plan(plan, triggered_by=admin_user, manual=True)

    assert only_work_order(plan).scheduled_date == due
    assert not TaskReschedule.objects.exists()
    assert not any('ADELANTADO' in w for w in result['warnings'])


def test_scheduled_run_uses_due_date_not_today(asset, admin_user):
    due = date.today() - timedelta(days=3)
    plan = plan_con_pendiente(asset, due)

    generate_work_orders_for_plan(plan, triggered_by=admin_user)

    assert only_work_order(plan).scheduled_date == due


def test_scheduled_run_ignores_future_pending(asset, admin_user):
    plan = plan_con_pendiente(asset, date.today() + timedelta(days=10))

    result = generate_work_orders_for_plan(plan, triggered_by=admin_user)

    assert result['created'] == 0
    assert not WorkOrder.objects.exists()
