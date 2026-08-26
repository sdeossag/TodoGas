import uuid
from datetime import date

import pytest

from apps.assets.models import Asset, Hospital
from apps.notifications.models import NotificationLog
from apps.users.models import User
from apps.work_orders.models import WorkOrder


# ── Helpers ─────────────────────────────────────────────────────────────────

def make_user(role, hospital=None):
    return User.objects.create_user(
        email=f"{uuid.uuid4()}@test.com",
        password="pass",
        first_name="A",
        last_name="B",
        role=role,
        hospital=hospital,
    )


def make_hospital():
    return Hospital.objects.create(name="H", code=str(uuid.uuid4())[:8])


def make_asset(hospital):
    return Asset.objects.create(
        hospital=hospital,
        name="Equipo",
        code=str(uuid.uuid4())[:10],
        status=Asset.Status.ACTIVE,
    )


def make_wo(asset, created_by, assigned_to=None):
    wo = WorkOrder(
        asset=asset,
        task_type=WorkOrder.TaskType.CORRECTIVE,
        title="OT test",
        status=WorkOrder.Status.PENDING,
        priority=WorkOrder.Priority.MEDIUM,
        scheduled_date=date.today(),
        assigned_to=assigned_to,
        created_by=created_by,
    )
    wo.save()
    return wo


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def hospital(db):
    return make_hospital()


@pytest.fixture
def admin(db):
    return make_user(User.Role.ADMIN)


@pytest.fixture
def tec(db, hospital):
    return make_user(User.Role.TEC, hospital=hospital)


@pytest.fixture
def asset(db, hospital):
    return make_asset(hospital)


@pytest.fixture
def wo(db, asset, admin, tec):
    return make_wo(asset, admin, assigned_to=tec)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_send_assignment_notification_creates_notification_log(db, wo, tec):
    from apps.notifications.service import send_assignment_notification

    send_assignment_notification(wo)

    log = NotificationLog.objects.filter(user=tec).first()
    assert log is not None
    assert log.notification_type == NotificationLog.NotificationType.WO_ASSIGNED
    assert log.channel == NotificationLog.Channel.PUSH


def test_notification_log_has_correct_type_and_user(db, wo, tec):
    from apps.notifications.service import send_assignment_notification

    send_assignment_notification(wo)

    log = NotificationLog.objects.get(user=tec)
    assert str(wo.id) in log.body or wo.asset.name in log.body
    assert f"OT-{wo.wo_number}" in log.title


def test_send_assignment_notification_without_assignee_does_not_raise(db, asset, admin):
    from apps.notifications.service import send_assignment_notification

    wo = make_wo(asset, admin, assigned_to=None)
    send_assignment_notification(wo)
    assert NotificationLog.objects.count() == 0
