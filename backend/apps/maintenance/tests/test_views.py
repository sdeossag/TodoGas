from datetime import date, timedelta

import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.maintenance.models import MaintenancePlan, MaintenancePlanExecution
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
def sup_user(db):
    return baker.make(User, role=User.Role.SUP, is_active=True)


@pytest.fixture
def tec_user(db):
    return baker.make(User, role=User.Role.TEC, is_active=True)


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
        next_due_date=date.today() + timedelta(days=30),
        task_type=MaintenancePlan.TaskType.PREVENTIVE,
    )
    p.assets.add(asset)
    return p


def test_admin_can_list_plans(plan, admin_user):
    client = auth_client(admin_user)
    resp = client.get('/api/maintenance/plans/')
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    ids = [item['id'] for item in (data if isinstance(data, list) else data.get('results', []))]
    assert str(plan.id) in ids


def test_sup_can_list_plans(plan, sup_user):
    client = auth_client(sup_user)
    resp = client.get('/api/maintenance/plans/')
    assert resp.status_code == status.HTTP_200_OK


def test_tec_cannot_list_plans(tec_user):
    client = auth_client(tec_user)
    resp = client.get('/api/maintenance/plans/')
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_admin_can_create_plan(admin_user, asset):
    client = auth_client(admin_user)
    payload = {
        'name': 'Plan Test',
        'task_type': MaintenancePlan.TaskType.PREVENTIVE,
        'frequency_value': 3,
        'frequency_unit': MaintenancePlan.FrequencyUnit.MONTHS,
        'assets': [str(asset.id)],
        'priority': MaintenancePlan.Priority.MEDIUM,
    }
    resp = client.post('/api/maintenance/plans/', payload, format='json')
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert data['name'] == 'Plan Test'
    plan = MaintenancePlan.objects.get(id=data['id'])
    assert plan.next_due_date is not None


def test_create_plan_requires_assets(admin_user):
    client = auth_client(admin_user)
    payload = {
        'name': 'Plan sin activos',
        'task_type': MaintenancePlan.TaskType.PREVENTIVE,
        'frequency_value': 6,
        'frequency_unit': MaintenancePlan.FrequencyUnit.MONTHS,
        'assets': [],
        'priority': MaintenancePlan.Priority.MEDIUM,
    }
    resp = client.post('/api/maintenance/plans/', payload, format='json')
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_trigger_generates_work_orders(plan, admin_user):
    client = auth_client(admin_user)
    resp = client.post(f'/api/maintenance/plans/{plan.id}/trigger/')
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data['created'] == 1
    assert WorkOrder.objects.filter(maintenance_plan=plan).count() == 1


def test_pause_deactivates_plan(plan, admin_user):
    client = auth_client(admin_user)
    resp = client.post(f'/api/maintenance/plans/{plan.id}/pause/')
    assert resp.status_code == status.HTTP_200_OK
    plan.refresh_from_db()
    assert plan.is_active is False


def test_resume_activates_plan(plan, admin_user):
    plan.is_active = False
    plan.save()
    client = auth_client(admin_user)
    resp = client.post(f'/api/maintenance/plans/{plan.id}/resume/')
    assert resp.status_code == status.HTTP_200_OK
    plan.refresh_from_db()
    assert plan.is_active is True
    assert plan.next_due_date is not None


def test_compliance_returns_12_months(plan, admin_user):
    client = auth_client(admin_user)
    resp = client.get(f'/api/maintenance/plans/{plan.id}/compliance/')
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data['plan_id'] == str(plan.id)
    assert len(data['monthly']) == 12
