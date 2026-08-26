from datetime import date, timedelta

import pytest
from model_bakery import baker

from apps.assets.models import Asset, Hospital
from apps.maintenance.engine import (
    calculate_next_due_date,
    generate_work_orders_for_plan,
    get_plans_due_today,
    run_daily_generation,
)
from apps.maintenance.models import MaintenancePlan, MaintenancePlanExecution
from apps.users.models import User
from apps.work_orders.models import WorkOrder


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
    p = baker.make(
        MaintenancePlan,
        frequency_value=6,
        frequency_unit=MaintenancePlan.FrequencyUnit.MONTHS,
        is_active=True,
        next_due_date=date.today() - timedelta(days=1),
        task_type=MaintenancePlan.TaskType.PREVENTIVE,
    )
    p.assets.add(asset)
    return p


def test_calculate_next_due_date_days(db):
    p = baker.prepare(
        MaintenancePlan,
        frequency_value=30,
        frequency_unit=MaintenancePlan.FrequencyUnit.DAYS,
    )
    result = calculate_next_due_date(p, from_date=date(2026, 1, 1))
    assert result == date(2026, 1, 31)


def test_calculate_next_due_date_weeks(db):
    p = baker.prepare(
        MaintenancePlan,
        frequency_value=2,
        frequency_unit=MaintenancePlan.FrequencyUnit.WEEKS,
    )
    result = calculate_next_due_date(p, from_date=date(2026, 1, 1))
    assert result == date(2026, 1, 15)


def test_calculate_next_due_date_months(db):
    p = baker.prepare(
        MaintenancePlan,
        frequency_value=3,
        frequency_unit=MaintenancePlan.FrequencyUnit.MONTHS,
    )
    result = calculate_next_due_date(p, from_date=date(2026, 1, 1))
    assert result == date(2026, 4, 1)


def test_calculate_next_due_date_years(db):
    p = baker.prepare(
        MaintenancePlan,
        frequency_value=1,
        frequency_unit=MaintenancePlan.FrequencyUnit.YEARS,
    )
    result = calculate_next_due_date(p, from_date=date(2026, 1, 1))
    assert result == date(2027, 1, 1)


def test_get_plans_due_today_returns_overdue(plan):
    results = list(get_plans_due_today())
    assert plan in results


def test_get_plans_due_today_excludes_future_plan(db, asset):
    p = baker.make(
        MaintenancePlan,
        is_active=True,
        next_due_date=date.today() + timedelta(days=10),
    )
    p.assets.add(asset)
    results = list(get_plans_due_today())
    assert p not in results


def test_get_plans_due_today_excludes_inactive(db, asset):
    p = baker.make(
        MaintenancePlan,
        is_active=False,
        next_due_date=date.today() - timedelta(days=1),
    )
    p.assets.add(asset)
    results = list(get_plans_due_today())
    assert p not in results


def test_generate_work_orders_creates_ot(plan, admin_user):
    result = generate_work_orders_for_plan(plan, triggered_by=admin_user)
    assert result['created'] == 1
    assert result['skipped'] == 0
    assert WorkOrder.objects.filter(maintenance_plan=plan).count() == 1


def test_generate_skips_existing_active_ot(plan, admin_user, asset):
    generate_work_orders_for_plan(plan, triggered_by=admin_user)
    plan.refresh_from_db()
    plan.next_due_date = date.today() - timedelta(days=1)
    plan.save()
    result = generate_work_orders_for_plan(plan, triggered_by=admin_user)
    assert result['skipped'] == 1
    assert result['created'] == 0
    assert len(result['warnings']) == 1


def test_generate_creates_execution_record(plan, admin_user):
    result = generate_work_orders_for_plan(plan, triggered_by=admin_user)
    assert MaintenancePlanExecution.objects.filter(plan=plan).count() == 1
    exec_obj = MaintenancePlanExecution.objects.get(plan=plan)
    assert exec_obj.work_orders_created == 1
    assert str(exec_obj.id) == result['execution_id']


def test_generate_advances_next_due_date(plan, admin_user):
    original_date = plan.next_due_date
    generate_work_orders_for_plan(plan, triggered_by=admin_user)
    plan.refresh_from_db()
    assert plan.next_due_date > original_date
    assert plan.last_generated_at is not None


def test_run_daily_generation(plan, admin_user):
    summary = run_daily_generation()
    assert summary['plans_processed'] == 1
    assert summary['total_created'] == 1
    assert summary['errors'] == []
