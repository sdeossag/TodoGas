"""La ficha de un activo debe exponer el mismo estado de mantenimiento que el listado.

Regresion: AssetSerializer (retrieve) no incluia last_maintenance_date,
next_maintenance_date ni maintenance_status. AssetDetailPage los leia igual, asi
que llegaban undefined y la ficha pintaba "Sin plan"/"Nunca" para cualquier
activo, contradiciendo lo que mostraba /activos para ese mismo activo.
"""

from datetime import date, timedelta

import pytest
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.maintenance.models import MaintenancePlan
from apps.users.models import User
from apps.work_orders.models import WorkOrder

MAINTENANCE_FIELDS = (
    'last_maintenance_date',
    'next_maintenance_date',
    'maintenance_status',
)


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


def detail(client, asset):
    resp = client.get(f'/api/assets/{asset.id}/')
    assert resp.status_code == status.HTTP_200_OK
    return resp.json()


def list_item(client, asset):
    resp = client.get('/api/assets/')
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    items = body if isinstance(body, list) else body.get('results', [])
    return next((i for i in items if i['id'] == str(asset.id)), None)


def test_detail_exposes_maintenance_fields(asset, admin_user):
    data = detail(auth_client(admin_user), asset)
    for field in MAINTENANCE_FIELDS:
        assert field in data, f'la ficha no expone {field}'


def test_detail_reports_plan_due_date(asset, admin_user):
    due = date.today() + timedelta(days=30)
    plan = baker.make(
        MaintenancePlan,
        is_active=True,
        next_due_date=due,
        frequency_value=6,
        frequency_unit=MaintenancePlan.FrequencyUnit.MONTHS,
    )
    plan.assets.add(asset)

    data = detail(auth_client(admin_user), asset)
    assert data['next_maintenance_date'] == str(due)
    assert data['maintenance_status'] == 'on_time'


def test_detail_matches_list_for_same_asset(asset, admin_user):
    """El bug se veia justo aqui: listado con fecha, ficha diciendo "Sin plan"."""
    plan = baker.make(
        MaintenancePlan,
        is_active=True,
        next_due_date=date.today() + timedelta(days=200),
        frequency_value=6,
        frequency_unit=MaintenancePlan.FrequencyUnit.MONTHS,
    )
    plan.assets.add(asset)
    client = auth_client(admin_user)

    row = list_item(client, asset)
    data = detail(client, asset)
    assert row is not None
    for field in MAINTENANCE_FIELDS:
        assert data[field] == row[field], f'{field} difiere entre ficha y listado'


def test_detail_without_plan_reports_no_plan(asset, admin_user):
    data = detail(auth_client(admin_user), asset)
    assert data['maintenance_status'] == 'no_plan'
    assert data['next_maintenance_date'] is None
    assert data['last_maintenance_date'] is None


def test_detail_reports_last_completed_work_order(asset, admin_user):
    from django.utils import timezone

    wo = WorkOrder(
        asset=asset,
        task_type=WorkOrder.TaskType.PREVENTIVE,
        title='OT de cierre',
        status=WorkOrder.Status.COMPLETED,
        priority=WorkOrder.Priority.MEDIUM,
        scheduled_date=date.today(),
        created_by=admin_user,
    )
    wo.save()
    completed = timezone.now()
    wo.completed_at = completed
    wo.save(update_fields=['completed_at'])

    data = detail(auth_client(admin_user), asset)
    assert data['last_maintenance_date'] == completed.date().isoformat()
