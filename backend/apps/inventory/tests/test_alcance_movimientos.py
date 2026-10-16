"""
Un supervisor limitado a un hospital no mueve inventario contra OTs de otro.

Regresion: StockMovementViewSet.create solo revisaba la OT para los tecnicos;
un SUP con hospital asignado podia vincular una salida a la OT de otra clinica
(y asi mezclar consumos entre hospitales). El listado tampoco filtraba.
"""

from decimal import Decimal

import pytest
from model_bakery import baker
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.inventory.models import InventoryItem, StockMovement
from apps.maintenance.testing import make_work_order
from apps.users.models import User
from apps.work_orders.models import WorkOrder

pytestmark = pytest.mark.django_db
URL = "/api/inventory/movements/"


def cliente(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def mundo():
    a = baker.make(Hospital, is_active=True, name="Clinica A")
    b = baker.make(Hospital, is_active=True, name="Clinica B")
    admin = baker.make(User, role=User.Role.ADMIN, is_active=True)
    sup_a = baker.make(User, role=User.Role.SUP, is_active=True, hospital=a)
    sup_global = baker.make(User, role=User.Role.SUP, is_active=True, hospital=None)
    activo_a = Asset.objects.create(hospital=a, name="Toma A", code="A-1", status=Asset.Status.ACTIVE)
    activo_b = Asset.objects.create(hospital=b, name="Toma B", code="B-1", status=Asset.Status.ACTIVE)
    ot_a = make_work_order(activo_a, admin, status=WorkOrder.Status.IN_PROGRESS)
    ot_b = make_work_order(activo_b, admin, status=WorkOrder.Status.IN_PROGRESS)
    item = InventoryItem.objects.create(name="Valvula", code="V-1", current_stock=Decimal(50),
                                        min_stock=Decimal(1))
    return {"a": a, "b": b, "admin": admin, "sup_a": sup_a, "sup_global": sup_global,
            "ot_a": ot_a, "ot_b": ot_b, "item": item}


def salida(m, user, ot):
    return cliente(user).post(URL, {
        "item": str(m["item"].id), "movement_type": "OUT", "quantity": "1",
        "work_order": str(ot.id),
    }, format="json")


def ids(r):
    datos = r.data
    filas = datos["results"] if isinstance(datos, dict) and "results" in datos else datos
    return {str(f["id"]) for f in filas}


def test_el_supervisor_limitado_no_vincula_una_ot_de_otro_hospital(mundo):
    r = salida(mundo, mundo["sup_a"], mundo["ot_b"])
    assert r.status_code == 400
    assert "work_order" in r.data
    assert not StockMovement.objects.exists()
    mundo["item"].refresh_from_db()
    assert mundo["item"].current_stock == Decimal(50)


def test_el_supervisor_limitado_vincula_una_ot_de_su_hospital(mundo):
    r = salida(mundo, mundo["sup_a"], mundo["ot_a"])
    assert r.status_code == 201
    assert StockMovement.objects.get().work_order_id == mundo["ot_a"].id


def test_el_supervisor_limitado_registra_movimientos_sin_ot(mundo):
    r = cliente(mundo["sup_a"]).post(URL, {
        "item": str(mundo["item"].id), "movement_type": "IN", "quantity": "5",
    }, format="json")
    assert r.status_code == 201


def test_el_admin_vincula_la_ot_de_cualquier_hospital(mundo):
    assert salida(mundo, mundo["admin"], mundo["ot_a"]).status_code == 201
    assert salida(mundo, mundo["admin"], mundo["ot_b"]).status_code == 201


def test_el_supervisor_sin_hospital_vincula_cualquier_ot(mundo):
    assert salida(mundo, mundo["sup_global"], mundo["ot_b"]).status_code == 201


def test_el_listado_de_movimientos_del_supervisor_limitado_es_solo_su_hospital(mundo):
    """Hoy el listado no filtra: el SUP de A ve los consumos de la OT de B."""
    propio = baker.make(StockMovement, item=mundo["item"], work_order=mundo["ot_a"],
                        movement_type="OUT", quantity=Decimal(1), performed_by=mundo["admin"])
    ajeno = baker.make(StockMovement, item=mundo["item"], work_order=mundo["ot_b"],
                       movement_type="OUT", quantity=Decimal(1), performed_by=mundo["admin"])

    visibles = ids(cliente(mundo["sup_a"]).get(URL))
    assert str(propio.id) in visibles
    assert str(ajeno.id) not in visibles
    assert {str(propio.id), str(ajeno.id)} <= ids(cliente(mundo["admin"]).get(URL))
