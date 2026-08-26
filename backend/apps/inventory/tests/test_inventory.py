import uuid
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.inventory.models import InventoryItem, StockMovement
from apps.users.models import User
from apps.work_orders.models import WorkOrder


# ── Helpers ──────────────────────────────────────────────────────────────────

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


def make_asset(hospital):
    return Asset.objects.create(
        hospital=hospital,
        name="Equipo",
        code=str(uuid.uuid4())[:10],
        status=Asset.Status.ACTIVE,
    )


def make_item(name="Repuesto", stock=Decimal("10"), min_stock=Decimal("2")):
    return InventoryItem.objects.create(
        name=name,
        code=str(uuid.uuid4())[:10],
        current_stock=stock,
        min_stock=min_stock,
    )


def make_wo(asset, assigned_to, created_by):
    return WorkOrder.objects.create(
        asset=asset,
        task_type=WorkOrder.TaskType.CORRECTIVE,
        title="OT Test",
        status=WorkOrder.Status.IN_PROGRESS,
        priority=WorkOrder.Priority.MEDIUM,
        scheduled_date="2026-09-01",
        assigned_to=assigned_to,
        created_by=created_by,
    )


# ── Item CRUD ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_admin_can_create_inventory_item():
    admin = make_user(User.Role.ADMIN)
    c = auth_client(admin)
    payload = {
        'name': 'Filtro HEPA',
        'code': 'FH-001',
        'unit_of_measure': 'und',
        'min_stock': '5',
        'unit_cost': '25000',
    }
    resp = c.post('/api/inventory/items/', payload)
    assert resp.status_code == status.HTTP_201_CREATED
    assert InventoryItem.objects.filter(code='FH-001').exists()


@pytest.mark.django_db
def test_sup_cannot_create_inventory_item():
    sup = make_user(User.Role.SUP)
    resp = auth_client(sup).post('/api/inventory/items/', {'name': 'X', 'code': 'X1'})
    assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_admin_can_list_inventory_items():
    admin = make_user(User.Role.ADMIN)
    make_item('Item A')
    resp = auth_client(admin).get('/api/inventory/items/')
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# ── Stock IN ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_stock_in_increments_current_stock():
    admin = make_user(User.Role.ADMIN)
    item = make_item(stock=Decimal("10"))
    payload = {
        'item': str(item.id),
        'movement_type': 'IN',
        'quantity': '5',
    }
    resp = auth_client(admin).post('/api/inventory/movements/', payload)
    assert resp.status_code == status.HTTP_201_CREATED
    item.refresh_from_db()
    assert item.current_stock == Decimal("15")


# ── Stock OUT ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_stock_out_decrements_current_stock():
    admin = make_user(User.Role.ADMIN)
    item = make_item(stock=Decimal("10"))
    payload = {
        'item': str(item.id),
        'movement_type': 'OUT',
        'quantity': '3',
    }
    resp = auth_client(admin).post('/api/inventory/movements/', payload)
    assert resp.status_code == status.HTTP_201_CREATED
    item.refresh_from_db()
    assert item.current_stock == Decimal("7")


@pytest.mark.django_db
def test_stock_out_insufficient_returns_400():
    admin = make_user(User.Role.ADMIN)
    item = make_item(stock=Decimal("2"))
    payload = {
        'item': str(item.id),
        'movement_type': 'OUT',
        'quantity': '5',
    }
    resp = auth_client(admin).post('/api/inventory/movements/', payload)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ── Stock ADJUSTMENT ──────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_stock_adjustment_sets_absolute_value():
    admin = make_user(User.Role.ADMIN)
    item = make_item(stock=Decimal("10"))
    payload = {
        'item': str(item.id),
        'movement_type': 'ADJUSTMENT',
        'quantity': '7',
    }
    resp = auth_client(admin).post('/api/inventory/movements/', payload)
    assert resp.status_code == status.HTTP_201_CREATED
    item.refresh_from_db()
    assert item.current_stock == Decimal("7")


# ── Immutability ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_stock_movement_cannot_be_edited():
    admin = make_user(User.Role.ADMIN)
    item = make_item(stock=Decimal("10"))
    movement = StockMovement.objects.create(
        item=item,
        movement_type=StockMovement.MovementType.IN,
        quantity=Decimal("5"),
        performed_by=admin,
    )
    # PUT/PATCH are not routed, but test at model level too
    movement.notes = "changed"
    with pytest.raises(ValueError, match="inmutable"):
        movement.save()


@pytest.mark.django_db
def test_stock_movement_cannot_be_deleted():
    admin = make_user(User.Role.ADMIN)
    item = make_item(stock=Decimal("10"))
    movement = StockMovement.objects.create(
        item=item,
        movement_type=StockMovement.MovementType.IN,
        quantity=Decimal("5"),
        performed_by=admin,
    )
    with pytest.raises(ValueError, match="inmutable"):
        movement.delete()


@pytest.mark.django_db
def test_movement_api_patch_returns_405():
    admin = make_user(User.Role.ADMIN)
    item = make_item(stock=Decimal("10"))
    movement = StockMovement.objects.create(
        item=item,
        movement_type=StockMovement.MovementType.IN,
        quantity=Decimal("5"),
        performed_by=admin,
    )
    resp = auth_client(admin).patch(
        f'/api/inventory/movements/{movement.id}/', {'notes': 'x'}
    )
    # Router doesn't route PATCH since we use only CreateModelMixin/ListModelMixin/RetrieveModelMixin
    assert resp.status_code in (status.HTTP_405_METHOD_NOT_ALLOWED, 404)


# ── Low stock ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_low_stock_returns_only_low_items():
    admin = make_user(User.Role.ADMIN)
    low_item = make_item('Low', stock=Decimal("1"), min_stock=Decimal("5"))
    ok_item = make_item('OK', stock=Decimal("10"), min_stock=Decimal("5"))

    resp = auth_client(admin).get('/api/inventory/items/low-stock/')
    assert resp.status_code == 200
    ids = [r['id'] for r in resp.json()]
    assert str(low_item.id) in ids
    assert str(ok_item.id) not in ids


# ── TEC movement ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_tec_can_register_out_on_own_wo():
    admin = make_user(User.Role.ADMIN)
    tec = make_user(User.Role.TEC)
    hospital = make_hospital()
    asset = make_asset(hospital)
    wo = make_wo(asset, tec, admin)
    item = make_item(stock=Decimal("10"))

    payload = {
        'item': str(item.id),
        'movement_type': 'OUT',
        'quantity': '2',
        'work_order': str(wo.id),
    }
    resp = auth_client(tec).post('/api/inventory/movements/', payload)
    assert resp.status_code == status.HTTP_201_CREATED
    item.refresh_from_db()
    assert item.current_stock == Decimal("8")


@pytest.mark.django_db
def test_tec_cannot_register_out_on_another_tec_wo():
    admin = make_user(User.Role.ADMIN)
    tec1 = make_user(User.Role.TEC)
    tec2 = make_user(User.Role.TEC)
    hospital = make_hospital()
    asset = make_asset(hospital)
    wo = make_wo(asset, tec1, admin)  # assigned to tec1
    item = make_item(stock=Decimal("10"))

    payload = {
        'item': str(item.id),
        'movement_type': 'OUT',
        'quantity': '2',
        'work_order': str(wo.id),
    }
    resp = auth_client(tec2).post('/api/inventory/movements/', payload)
    assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_tec_cannot_register_in_movement():
    admin = make_user(User.Role.ADMIN)
    tec = make_user(User.Role.TEC)
    hospital = make_hospital()
    asset = make_asset(hospital)
    wo = make_wo(asset, tec, admin)
    item = make_item(stock=Decimal("10"))

    payload = {
        'item': str(item.id),
        'movement_type': 'IN',
        'quantity': '2',
        'work_order': str(wo.id),
    }
    resp = auth_client(tec).post('/api/inventory/movements/', payload)
    assert resp.status_code == status.HTTP_403_FORBIDDEN


# ── CLI access control ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_cli_cannot_list_inventory_items():
    cli = make_user(User.Role.CLI)
    resp = auth_client(cli).get('/api/inventory/items/')
    assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_cli_cannot_view_low_stock():
    cli = make_user(User.Role.CLI)
    resp = auth_client(cli).get('/api/inventory/items/low-stock/')
    assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_cli_cannot_list_stock_movements():
    cli = make_user(User.Role.CLI)
    resp = auth_client(cli).get('/api/inventory/movements/')
    assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_cli_cannot_retrieve_stock_movement():
    admin = make_user(User.Role.ADMIN)
    cli = make_user(User.Role.CLI)
    item = make_item(stock=Decimal("10"))
    movement = StockMovement.objects.create(
        item=item,
        movement_type=StockMovement.MovementType.IN,
        quantity=Decimal("3"),
        performed_by=admin,
    )
    resp = auth_client(cli).get(f'/api/inventory/movements/{movement.id}/')
    assert resp.status_code == status.HTTP_403_FORBIDDEN


# ── TEC read access ───────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_tec_can_list_inventory_items():
    tec = make_user(User.Role.TEC)
    make_item('Repuesto TEC')
    resp = auth_client(tec).get('/api/inventory/items/')
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.json()) >= 1


@pytest.mark.django_db
def test_tec_can_list_stock_movements():
    admin = make_user(User.Role.ADMIN)
    tec = make_user(User.Role.TEC)
    item = make_item(stock=Decimal("10"))
    StockMovement.objects.create(
        item=item,
        movement_type=StockMovement.MovementType.IN,
        quantity=Decimal("5"),
        performed_by=admin,
    )
    resp = auth_client(tec).get('/api/inventory/movements/')
    assert resp.status_code == status.HTTP_200_OK
