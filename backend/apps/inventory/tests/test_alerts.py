import uuid
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.assets.models import Hospital
from apps.inventory.models import InventoryItem
from apps.users.models import User


def auth_client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def make_user(role, hospital=None):
    return User.objects.create_user(
        email=f"{uuid.uuid4()}@test.com",
        password="pass",
        first_name="T",
        last_name="U",
        role=role,
        hospital=hospital,
    )


def make_hospital():
    return Hospital.objects.create(name="H", code=str(uuid.uuid4())[:8])


def make_item(stock, min_stock):
    return InventoryItem.objects.create(
        name=f"Item {uuid.uuid4().hex[:4]}",
        code=str(uuid.uuid4())[:10],
        current_stock=Decimal(str(stock)),
        min_stock=Decimal(str(min_stock)),
    )


@pytest.mark.django_db
def test_alerts_returns_correct_low_stock_count():
    admin = make_user(User.Role.ADMIN)
    make_item(stock=1, min_stock=5)   # low
    make_item(stock=2, min_stock=5)   # low
    make_item(stock=10, min_stock=5)  # ok

    resp = auth_client(admin).get('/api/inventory/alerts/')
    assert resp.status_code == 200
    data = resp.json()
    assert data['low_stock_count'] >= 2
    assert len(data['items']) >= 2


@pytest.mark.django_db
def test_alerts_items_are_only_low_stock():
    admin = make_user(User.Role.ADMIN)
    low = make_item(stock=1, min_stock=10)
    ok = make_item(stock=20, min_stock=10)

    resp = auth_client(admin).get('/api/inventory/alerts/')
    assert resp.status_code == 200
    ids = [i['id'] for i in resp.json()['items']]
    assert str(low.id) in ids
    assert str(ok.id) not in ids


@pytest.mark.django_db
def test_cli_cannot_access_alerts():
    hospital = make_hospital()
    cli = make_user(User.Role.CLI, hospital=hospital)
    resp = auth_client(cli).get('/api/inventory/alerts/')
    assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_tec_cannot_access_alerts():
    tec = make_user(User.Role.TEC)
    resp = auth_client(tec).get('/api/inventory/alerts/')
    assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_sup_can_access_alerts():
    sup = make_user(User.Role.SUP)
    resp = auth_client(sup).get('/api/inventory/alerts/')
    assert resp.status_code == 200
