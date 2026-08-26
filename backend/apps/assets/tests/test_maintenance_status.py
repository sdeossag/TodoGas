from datetime import date, timedelta

import pytest
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.maintenance.models import MaintenancePlan
from apps.users.models import User
from apps.work_orders.models import WorkOrder


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def admin_user(db):
    return baker.make(User, role=User.Role.ADMIN, is_active=True)


@pytest.fixture
def hospital(db):
    return baker.make(Hospital, is_active=True)


@pytest.fixture
def asset(db, hospital):
    return baker.make(Asset, hospital=hospital, status=Asset.Status.ACTIVE)


def test_maintenance_status_no_plan(asset, admin_user):
    client = auth_client(admin_user)
    resp = client.get('/api/assets/')
    assert resp.status_code == status.HTTP_200_OK
    items = resp.json() if isinstance(resp.json(), list) else resp.json().get('results', [])
    item = next((i for i in items if i['id'] == str(asset.id)), None)
    assert item is not None
    assert item['maintenance_status'] == 'no_plan'


def test_maintenance_status_on_time(asset, admin_user):
    p = baker.make(
        MaintenancePlan,
        is_active=True,
        next_due_date=date.today() + timedelta(days=30),
        frequency_value=6,
        frequency_unit=MaintenancePlan.FrequencyUnit.MONTHS,
    )
    p.assets.add(asset)
    client = auth_client(admin_user)
    resp = client.get('/api/assets/')
    items = resp.json() if isinstance(resp.json(), list) else resp.json().get('results', [])
    item = next((i for i in items if i['id'] == str(asset.id)), None)
    assert item['maintenance_status'] == 'on_time'


def test_maintenance_status_due_soon(asset, admin_user):
    p = baker.make(
        MaintenancePlan,
        is_active=True,
        next_due_date=date.today() + timedelta(days=5),
        frequency_value=6,
        frequency_unit=MaintenancePlan.FrequencyUnit.MONTHS,
    )
    p.assets.add(asset)
    client = auth_client(admin_user)
    resp = client.get('/api/assets/')
    items = resp.json() if isinstance(resp.json(), list) else resp.json().get('results', [])
    item = next((i for i in items if i['id'] == str(asset.id)), None)
    assert item['maintenance_status'] == 'due_soon'


def test_maintenance_status_overdue(asset, admin_user):
    p = baker.make(
        MaintenancePlan,
        is_active=True,
        next_due_date=date.today() - timedelta(days=1),
        frequency_value=6,
        frequency_unit=MaintenancePlan.FrequencyUnit.MONTHS,
    )
    p.assets.add(asset)
    client = auth_client(admin_user)
    resp = client.get('/api/assets/')
    items = resp.json() if isinstance(resp.json(), list) else resp.json().get('results', [])
    item = next((i for i in items if i['id'] == str(asset.id)), None)
    assert item['maintenance_status'] == 'overdue'


def test_last_maintenance_date_from_completed_wo(asset, admin_user):
    wo = WorkOrder(
        asset=asset,
        task_type=WorkOrder.TaskType.PREVENTIVE,
        title='Test OT',
        status=WorkOrder.Status.COMPLETED,
        priority=WorkOrder.Priority.MEDIUM,
        scheduled_date=date.today(),
        created_by=admin_user,
    )
    wo.save()
    from django.utils import timezone
    wo.completed_at = timezone.now()
    wo.save(update_fields=['completed_at'])

    client = auth_client(admin_user)
    resp = client.get('/api/assets/')
    items = resp.json() if isinstance(resp.json(), list) else resp.json().get('results', [])
    item = next((i for i in items if i['id'] == str(asset.id)), None)
    assert item['last_maintenance_date'] is not None
