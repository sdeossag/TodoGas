"""«Disparar ahora» no debe consumir el ciclo programado del plan.

Regresion: el disparo manual y la corrida diaria llamaban a la misma funcion sin
distinguirse. Siempre creaba la OT con scheduled_date = next_due_date (una fecha
futura, no "ahora") y despues adelantaba next_due_date un periodo completo, asi
que un disparo anticipado hacia desaparecer la ejecucion programada siguiente.

Regla actual:
  - disparo manual ANTES del vencimiento -> mantenimiento extraordinario:
    OT para hoy y calendario intacto.
  - disparo manual con el plan ya vencido -> es la corrida programada hecha a
    mano: ejecuta el ciclo y avanza.
  - corrida automatica -> siempre ejecuta el ciclo.
"""

from datetime import date, timedelta

import pytest
from dateutil.relativedelta import relativedelta
from model_bakery import baker

from apps.assets.models import Asset, Hospital
from apps.maintenance.engine import generate_work_orders_for_plan
from apps.maintenance.models import MaintenancePlan
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


def make_plan(asset, next_due_date):
    plan = baker.make(
        MaintenancePlan,
        is_active=True,
        task_type=MaintenancePlan.TaskType.PREVENTIVE,
        frequency_value=FREQ_MONTHS,
        frequency_unit=MaintenancePlan.FrequencyUnit.MONTHS,
        next_due_date=next_due_date,
    )
    plan.assets.add(asset)
    return plan


def only_work_order(plan):
    return WorkOrder.objects.get(maintenance_plan=plan)


# ── Disparo manual anticipado: extraordinario ────────────────────────────────

def test_manual_trigger_before_due_keeps_schedule(asset, admin_user):
    due = date.today() + timedelta(days=90)
    plan = make_plan(asset, due)

    generate_work_orders_for_plan(plan, triggered_by=admin_user, manual=True)

    plan.refresh_from_db()
    assert plan.next_due_date == due, 'el disparo anticipado no debe mover el calendario'


def test_manual_trigger_before_due_schedules_ot_for_today(asset, admin_user):
    plan = make_plan(asset, date.today() + timedelta(days=90))

    result = generate_work_orders_for_plan(plan, triggered_by=admin_user, manual=True)

    assert result['created'] == 1
    assert only_work_order(plan).scheduled_date == date.today()


def test_manual_trigger_before_due_warns_it_was_extraordinary(asset, admin_user):
    plan = make_plan(asset, date.today() + timedelta(days=90))

    result = generate_work_orders_for_plan(plan, triggered_by=admin_user, manual=True)

    assert any('extraordinario' in w for w in result['warnings'])


def test_manual_trigger_before_due_still_records_generation(asset, admin_user):
    plan = make_plan(asset, date.today() + timedelta(days=90))

    generate_work_orders_for_plan(plan, triggered_by=admin_user, manual=True)

    plan.refresh_from_db()
    assert plan.last_generated_at is not None


# ── Disparo manual de un plan vencido: ejecuta el ciclo ──────────────────────

def test_manual_trigger_when_overdue_advances_schedule(asset, admin_user):
    due = date.today() - timedelta(days=1)
    plan = make_plan(asset, due)

    result = generate_work_orders_for_plan(plan, triggered_by=admin_user, manual=True)

    plan.refresh_from_db()
    assert plan.next_due_date == due + relativedelta(months=FREQ_MONTHS)
    assert only_work_order(plan).scheduled_date == due
    assert not any('extraordinario' in w for w in result['warnings'])


def test_manual_trigger_without_due_date_initialises_schedule(asset, admin_user):
    plan = make_plan(asset, None)

    generate_work_orders_for_plan(plan, triggered_by=admin_user, manual=True)

    plan.refresh_from_db()
    assert plan.next_due_date == date.today() + relativedelta(months=FREQ_MONTHS)


# ── Corrida programada: siempre avanza ───────────────────────────────────────

def test_scheduled_run_advances_schedule(asset, admin_user):
    due = date.today() - timedelta(days=1)
    plan = make_plan(asset, due)

    generate_work_orders_for_plan(plan, triggered_by=admin_user)

    plan.refresh_from_db()
    assert plan.next_due_date == due + relativedelta(months=FREQ_MONTHS)


def test_scheduled_run_uses_due_date_not_today(asset, admin_user):
    due = date.today() - timedelta(days=3)
    plan = make_plan(asset, due)

    generate_work_orders_for_plan(plan, triggered_by=admin_user)

    assert only_work_order(plan).scheduled_date == due
