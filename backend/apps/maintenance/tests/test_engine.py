from datetime import date, timedelta

import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from model_bakery import baker

from apps.assets.models import Asset, Hospital
from apps.maintenance import services
from apps.maintenance.engine import (
    generate_work_orders_for_plan,
    get_plans_due_today,
    run_daily_generation,
)
from apps.maintenance.models import MaintenancePlan, MaintenancePlanExecution, Task
from apps.maintenance.testing import make_plan, pending_task
from apps.users.models import User
from apps.work_orders.models import WorkOrder

MESES = MaintenancePlan.FrequencyUnit


@pytest.fixture
def admin_user(db):
    return baker.make(User, role=User.Role.ADMIN, is_active=True)


@pytest.fixture
def hospital(db):
    return baker.make(Hospital, is_active=True)


@pytest.fixture
def asset(db, hospital):
    return baker.make(Asset, hospital=hospital, status=Asset.Status.ACTIVE)


@pytest.fixture
def plan(db, asset):
    return make_plan(
        "Plan vencido", assets=[asset],
        next_due_date=date.today() - timedelta(days=1),
    )


def plan_wos(plan):
    return WorkOrder.objects.filter(tasks__plan_task__plan=plan)


# ── Frecuencias ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("valor,unidad,esperado", [
    (30, MESES.DAYS, date(2026, 1, 31)),
    (2, MESES.WEEKS, date(2026, 1, 15)),
    (3, MESES.MONTHS, date(2026, 4, 1)),
    (1, MESES.YEARS, date(2027, 1, 1)),
])
def test_add_frequency(valor, unidad, esperado):
    assert services.add_frequency(date(2026, 1, 1), valor, unidad) == esperado


def test_add_frequency_clamps_to_month_end():
    # Como Fracttal: 30 de agosto + 6 meses = 28 de febrero.
    assert services.add_frequency(date(2024, 8, 30), 6, MESES.MONTHS) == date(2025, 2, 28)


# ── Planes que tocan hoy ─────────────────────────────────────────────────────

def test_get_plans_due_today_returns_overdue(plan):
    assert plan in list(get_plans_due_today())


def test_get_plans_due_today_excludes_future_plan(db, asset):
    p = make_plan("Futuro", assets=[asset], next_due_date=date.today() + timedelta(days=10))
    assert p not in list(get_plans_due_today())


def test_get_plans_due_today_excludes_inactive(db, asset):
    p = make_plan(
        "Pausado", assets=[asset], is_active=False,
        next_due_date=date.today() - timedelta(days=1),
    )
    assert p not in list(get_plans_due_today())


# ── Generacion ───────────────────────────────────────────────────────────────

def test_generate_work_orders_creates_ot(plan, admin_user):
    result = generate_work_orders_for_plan(plan, triggered_by=admin_user)
    assert result['created'] == 1
    assert result['skipped'] == 0
    assert plan_wos(plan).count() == 1


def test_generated_ot_contains_the_pending_task(plan, admin_user, asset):
    tarea = pending_task(plan, asset)

    generate_work_orders_for_plan(plan, triggered_by=admin_user)

    tarea.refresh_from_db()
    assert tarea.status == Task.Status.SCHEDULED
    assert tarea.work_order == plan_wos(plan).get()
    assert tarea.work_order.hospital == asset.hospital


def test_generate_skips_existing_active_ot(plan, admin_user):
    generate_work_orders_for_plan(plan, triggered_by=admin_user)
    result = generate_work_orders_for_plan(plan, triggered_by=admin_user)
    assert result['skipped'] == 1
    assert result['created'] == 0
    assert len(result['warnings']) == 1


def test_generate_creates_execution_record(plan, admin_user):
    result = generate_work_orders_for_plan(plan, triggered_by=admin_user)
    exec_obj = MaintenancePlanExecution.objects.get(plan=plan)
    assert exec_obj.work_orders_created == 1
    assert str(exec_obj.id) == result['execution_id']


def test_next_date_is_set_when_the_ot_is_closed(plan, admin_user, asset):
    """
    Antes el motor adelantaba la fecha al generar la OT. Ahora la siguiente
    pendiente nace al cerrar la OT, contada desde la realizacion (decision D3).
    """
    generate_work_orders_for_plan(plan, triggered_by=admin_user)
    ot = plan_wos(plan).get()
    assert pending_task(plan, asset).work_order == ot, "hasta cerrar no hay otra"

    ot.status = WorkOrder.Status.COMPLETED
    ot.completed_at = timezone.now()
    ot.save()
    services.complete_work_order_tasks(ot)

    siguiente = pending_task(plan, asset)
    assert siguiente.status == Task.Status.PENDING
    assert siguiente.calculated_date == (
        timezone.localdate(ot.completed_at) + relativedelta(months=6)
    )


# ── Corrida diaria ───────────────────────────────────────────────────────────

def test_run_daily_generation(plan, admin_user, settings):
    settings.MAINTENANCE_AUTO_CREATE_WORK_ORDERS = True
    summary = run_daily_generation()
    assert summary['plans_processed'] == 1
    assert summary['total_created'] == 1
    assert summary['errors'] == []


def test_daily_run_without_auto_creation_only_keeps_pending(plan, admin_user, settings):
    """Como el cliente en Fracttal (D1): el proceso no crea OTs, solo mantiene
    las pendientes; las OTs las arma el planificador."""
    settings.MAINTENANCE_AUTO_CREATE_WORK_ORDERS = False
    summary = run_daily_generation()
    assert summary['total_created'] == 0
    assert not WorkOrder.objects.exists()


def test_daily_run_restores_missing_pending(db, asset, settings):
    settings.MAINTENANCE_AUTO_CREATE_WORK_ORDERS = False
    plan = make_plan("Sin pendiente", assets=[asset], next_due_date=date.today() + timedelta(days=5))
    Task.objects.filter(plan_task__plan=plan).update(
        status=Task.Status.CANCELLED, cancellation_note="prueba"
    )

    summary = run_daily_generation()

    assert summary['tasks_opened'] == 1
    assert pending_task(plan, asset) is not None
