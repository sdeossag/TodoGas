from dateutil.relativedelta import relativedelta
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
from apps.maintenance.models import Task
from apps.maintenance.testing import make_plan


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
    return make_plan(
        "Plan vistas", assets=[asset],
        next_due_date=date.today() + timedelta(days=30),
    )


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


def test_admin_can_create_plan(admin_user):
    """El plan es la cabecera: las tareas y los activos se agregan despues."""
    client = auth_client(admin_user)
    payload = {'name': 'Plan Test', 'priority': MaintenancePlan.Priority.HIGH}
    resp = client.post('/api/maintenance/plans/', payload, format='json')
    assert resp.status_code == status.HTTP_201_CREATED
    plan = MaintenancePlan.objects.get(id=resp.json()['id'])
    assert plan.name == 'Plan Test'
    assert plan.priority == MaintenancePlan.Priority.HIGH
    assert not plan.tasks.exists()


def test_duplicate_plan_name_is_explained(plan, admin_user):
    client = auth_client(admin_user)
    resp = client.post('/api/maintenance/plans/', {'name': plan.name}, format='json')
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json()['name'] == ['Ya existe un protocolo con ese nombre.']


def test_sup_cannot_create_plan(sup_user):
    client = auth_client(sup_user)
    resp = client.post('/api/maintenance/plans/', {'name': 'X'}, format='json')
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_trigger_no_longer_exists(plan, admin_user):
    """«Disparar ahora» desaparece: ahora es reprogramar a hoy y armar la OT."""
    client = auth_client(admin_user)
    resp = client.post(f'/api/maintenance/plans/{plan.id}/trigger/')
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_list_summarizes_tasks_assets_and_dates(plan, admin_user, asset):
    client = auth_client(admin_user)
    fila = client.get('/api/maintenance/plans/').json()['results'][0]
    assert fila['assets_count'] == 1
    assert fila['pending_count'] == 1
    assert fila['overdue_count'] == 0
    assert fila['next_due_date'] == str(date.today() + timedelta(days=30))
    assert [t['frequency_value'] for t in fila['tasks']] == [6]


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
    assert Task.objects.filter(plan_task__plan=plan, status=Task.Status.PENDING).exists()


def test_compliance_returns_12_months(plan, admin_user):
    client = auth_client(admin_user)
    resp = client.get(f'/api/maintenance/plans/{plan.id}/compliance/')
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data['plan_id'] == str(plan.id)
    assert len(data['monthly']) == 12
