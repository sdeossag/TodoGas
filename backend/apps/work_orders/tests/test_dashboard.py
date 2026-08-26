import uuid
from datetime import date, timedelta

import pytest
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.users.models import User
from apps.work_orders.dashboard import (
    calculate_compliance_percentage,
    calculate_mttr,
    calculate_overdue_count,
)
from apps.work_orders.models import WorkOrder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(role, hospital=None):
    return User.objects.create_user(
        email=f"{uuid.uuid4()}@test.com",
        password="pass",
        first_name="Test",
        last_name="User",
        role=role,
        hospital=hospital,
    )


def make_hospital():
    return Hospital.objects.create(name=f"H-{uuid.uuid4()}", code=str(uuid.uuid4())[:8])


def make_asset(hospital):
    return Asset.objects.create(
        hospital=hospital,
        name="Equipo",
        code=str(uuid.uuid4())[:10],
    )


def make_wo(
    asset,
    created_by,
    task_type=WorkOrder.TaskType.PREVENTIVE,
    wo_status=WorkOrder.Status.PENDING,
    scheduled_date=None,
    completed_at=None,
    started_at=None,
    priority=WorkOrder.Priority.MEDIUM,
):
    if scheduled_date is None:
        scheduled_date = date.today()
    wo = WorkOrder(
        asset=asset,
        task_type=task_type,
        title="OT test",
        status=wo_status,
        priority=priority,
        scheduled_date=scheduled_date,
        created_by=created_by,
    )
    wo.save()
    if completed_at or started_at:
        WorkOrder.objects.filter(pk=wo.pk).update(
            completed_at=completed_at,
            started_at=started_at,
        )
        wo.refresh_from_db()
    return wo


def auth_client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def hospital(db):
    return make_hospital()


@pytest.fixture
def hospital_b(db):
    return make_hospital()


@pytest.fixture
def admin(db):
    return make_user(User.Role.ADMIN)


@pytest.fixture
def sup(db):
    return make_user(User.Role.SUP)


@pytest.fixture
def cli(db, hospital):
    return make_user(User.Role.CLI, hospital=hospital)


@pytest.fixture
def asset(db, hospital):
    return make_asset(hospital)


@pytest.fixture
def asset_b(db, hospital_b):
    return make_asset(hospital_b)


# ---------------------------------------------------------------------------
# calculate_compliance_percentage
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_compliance_calculates_correctly(hospital, asset, admin):
    today = date.today()
    # 3 OTs preventivas este mes, 2 completadas a tiempo
    for i in range(3):
        wo = make_wo(
            asset, admin,
            task_type=WorkOrder.TaskType.PREVENTIVE,
            scheduled_date=today,
        )
    # Mark 2 as COMPLETED on time
    wos = list(WorkOrder.objects.filter(asset=asset, task_type=WorkOrder.TaskType.PREVENTIVE))
    on_time_ts = timezone.now()
    WorkOrder.objects.filter(pk=wos[0].pk).update(
        status=WorkOrder.Status.COMPLETED, completed_at=on_time_ts
    )
    WorkOrder.objects.filter(pk=wos[1].pk).update(
        status=WorkOrder.Status.COMPLETED, completed_at=on_time_ts
    )

    result = calculate_compliance_percentage(
        month=today.month, year=today.year, hospital_id=str(hospital.id)
    )

    assert result["generated"] == 3
    assert result["completed"] == 2
    assert result["percentage"] == pytest.approx(66.7, abs=0.1)
    assert result["month"] == today.strftime("%Y-%m")


@pytest.mark.django_db
def test_compliance_returns_zero_when_no_ots(hospital):
    result = calculate_compliance_percentage(
        month=1, year=2000, hospital_id=str(hospital.id)
    )
    assert result["percentage"] == 0.0
    assert result["generated"] == 0
    assert result["completed"] == 0


# ---------------------------------------------------------------------------
# calculate_mttr
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_mttr_calculates_average_correctly(hospital, asset, admin):
    now = timezone.now()
    # Two corrective WOs: 2h and 4h repair time
    for hours in (2, 4):
        wo = make_wo(
            asset, admin,
            task_type=WorkOrder.TaskType.CORRECTIVE,
            wo_status=WorkOrder.Status.COMPLETED,
            started_at=now - timedelta(hours=hours),
            completed_at=now,
        )

    result = calculate_mttr(hospital_id=str(hospital.id), days=30)
    assert result["sample_size"] == 2
    assert result["mttr_hours"] == pytest.approx(3.0, abs=0.1)


@pytest.mark.django_db
def test_mttr_returns_zero_when_no_data(hospital):
    result = calculate_mttr(hospital_id=str(hospital.id), days=30)
    assert result["mttr_hours"] == 0.0
    assert result["sample_size"] == 0


# ---------------------------------------------------------------------------
# calculate_overdue_count
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_overdue_count_counts_correctly(hospital, asset, admin):
    yesterday = date.today() - timedelta(days=1)
    make_wo(asset, admin, scheduled_date=yesterday, priority=WorkOrder.Priority.HIGH)
    make_wo(asset, admin, scheduled_date=yesterday, priority=WorkOrder.Priority.MEDIUM)
    # completed one should NOT count
    wo_done = make_wo(asset, admin, scheduled_date=yesterday)
    WorkOrder.objects.filter(pk=wo_done.pk).update(status=WorkOrder.Status.COMPLETED)

    result = calculate_overdue_count(hospital_id=str(hospital.id))
    assert result["count"] == 2
    assert result["critical"] == 1


# ---------------------------------------------------------------------------
# DashboardView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_dashboard_view_returns_200_with_all_kpis(admin):
    client = auth_client(admin)
    url = "/api/dashboard/"
    response = client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert "compliance" in data
    assert "mttr" in data
    assert "overdue" in data
    assert "ots_by_status" in data
    assert "ots_by_technician" in data
    assert "assets_without_maintenance" in data


@pytest.mark.django_db
def test_dashboard_view_uses_cache(admin, mocker):
    client = auth_client(admin)
    url = "/api/dashboard/"
    spy = mocker.spy(cache, "set")

    client.get(url)
    assert spy.call_count == 1  # first call stores in cache

    spy.reset_mock()
    client.get(url)
    assert spy.call_count == 0  # second call served from cache


@pytest.mark.django_db
def test_dashboard_view_cli_forbidden(cli):
    client = auth_client(cli)
    response = client.get("/api/dashboard/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_dashboard_view_hospital_id_filters(admin, hospital, hospital_b, asset, asset_b):
    today = date.today()
    # OT in hospital
    make_wo(asset, admin, scheduled_date=today - timedelta(days=1), priority=WorkOrder.Priority.HIGH)
    # OT in hospital_b
    make_wo(asset_b, admin, scheduled_date=today - timedelta(days=1), priority=WorkOrder.Priority.HIGH)

    client = auth_client(admin)
    resp_a = client.get(f"/api/dashboard/?hospital_id={hospital.id}")
    resp_b = client.get(f"/api/dashboard/?hospital_id={hospital_b.id}")

    assert resp_a.status_code == 200
    assert resp_b.status_code == 200
    overdue_a = resp_a.json()["overdue"]["count"]
    overdue_b = resp_b.json()["overdue"]["count"]
    assert overdue_a == 1
    assert overdue_b == 1
    assert overdue_a != overdue_b or hospital.id != hospital_b.id
