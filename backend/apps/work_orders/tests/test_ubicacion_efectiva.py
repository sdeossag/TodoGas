"""
Sububicacion efectiva de cada equipo en el detalle de la OT (audios del
cliente, 2026-10): la direccion y el punto propios del nodo o, si no los tiene,
los de la ubicacion de arriba o los del hospital, y de donde vienen.
"""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from model_bakery import baker
from rest_framework.test import APIClient

from apps.assets.models import Asset, AssetNode, Hospital
from apps.maintenance.models import Task
from apps.maintenance.testing import make_work_order
from apps.users.models import User
from apps.work_orders.integrity import compute_wo_content_hash

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin():
    return baker.make(User, role=User.Role.ADMIN, is_active=True)


@pytest.fixture
def arbol():
    h = baker.make(Hospital, name="Clinica Demo Norte", is_active=True,
                   address="Cra 48 #10-45, Medellin", latitude="6.2100000", longitude="-75.5700000")
    bloque = AssetNode.objects.create(hospital=h, name="Bloque A", node_type="BUILDING",
                                      address="Calle 10 #20-30, Medellin",
                                      latitude="6.2442000", longitude="-75.5812000")
    piso = AssetNode.objects.create(hospital=h, parent=bloque, name="Piso 1", node_type="FLOOR")
    urg = AssetNode.objects.create(hospital=h, parent=piso, name="Urgencias", node_type="AREA")
    return h, bloque, piso, urg


def _ot(h, admin, nodo, **extra):
    a = baker.make(Asset, hospital=h, node=nodo, status=Asset.Status.ACTIVE)
    return make_work_order(a, admin, **extra), a


def _detalle(admin, ot):
    c = APIClient()
    c.force_authenticate(user=admin)
    resp = c.get(f"/api/work-orders/{ot.id}/")
    assert resp.status_code == 200
    return resp.data


def test_sububicacion_con_punto_propio(arbol, admin):
    h, bloque, piso, urg = arbol
    ot, _ = _ot(h, admin, bloque)
    sub = _detalle(admin, ot)["tasks"][0]["asset"]["sublocation"]
    assert sub["name"] == "Bloque A"
    assert sub["address"] == "Calle 10 #20-30, Medellin"
    assert sub["latitude"] == pytest.approx(6.2442)
    assert sub["longitude"] == pytest.approx(-75.5812)
    assert sub["point_origin"] == {"kind": "own", "name": "Bloque A", "label": "propio"}
    assert sub["address_origin"]["kind"] == "own"


def test_sububicacion_hereda_de_la_de_arriba(arbol, admin):
    h, bloque, piso, urg = arbol
    ot, _ = _ot(h, admin, urg)
    sub = _detalle(admin, ot)["tasks"][0]["asset"]["sublocation"]
    assert sub["name"] == "Urgencias"
    assert sub["path"] == "Bloque A/Piso 1/Urgencias"
    assert sub["latitude"] == pytest.approx(6.2442)
    assert sub["address"] == "Calle 10 #20-30, Medellin"
    # Piso 1 no tiene punto: el primero que lo tiene hacia arriba es Bloque A.
    assert sub["point_origin"] == {"kind": "inherited", "name": "Bloque A", "label": "heredado de Bloque A"}


def test_sububicacion_hereda_del_hospital_si_nadie_tiene_punto(admin):
    h = baker.make(Hospital, name="H2", is_active=True, address="Av 1", latitude="6.1", longitude="-75.6")
    nodo = AssetNode.objects.create(hospital=h, name="Sala")
    ot, _ = _ot(h, admin, nodo)
    sub = _detalle(admin, ot)["tasks"][0]["asset"]["sublocation"]
    assert sub["point_origin"]["label"] == "heredado de H2"
    assert sub["address"] == "Av 1"


def test_sin_punto_en_ningun_lado_no_inventa_nada(admin):
    h = baker.make(Hospital, is_active=True, address="", latitude=None, longitude=None)
    nodo = AssetNode.objects.create(hospital=h, name="Sala")
    ot, _ = _ot(h, admin, nodo)
    sub = _detalle(admin, ot)["tasks"][0]["asset"]["sublocation"]
    assert sub["latitude"] is None and sub["longitude"] is None
    assert sub["point_origin"] is None
    assert sub["address"] == ""


def test_equipo_sin_nodo_no_tiene_sububicacion(arbol, admin):
    h, *_ = arbol
    ot, _ = _ot(h, admin, None)
    assert _detalle(admin, ot)["tasks"][0]["asset"]["sublocation"] is None


def test_la_ubicacion_de_la_visita_tambien_es_efectiva(arbol, admin):
    h, bloque, piso, urg = arbol
    ot, _ = _ot(h, admin, urg, location=piso)
    det = _detalle(admin, ot)["location_detail"]
    assert det["name"] == "Piso 1"
    assert det["point_origin"]["label"] == "heredado de Bloque A"


def test_ot_sin_ubicacion_de_visita(arbol, admin):
    h, bloque, *_ = arbol
    ot, _ = _ot(h, admin, bloque)
    assert _detalle(admin, ot)["location_detail"] is None


def test_sin_n_mas_uno_por_numero_de_tareas(arbol, admin):
    h, bloque, piso, urg = arbol

    def consultas(n):
        ot, _ = _ot(h, admin, urg)
        base = ot.tasks.first()
        for i in range(n - 1):
            extra = baker.make(Asset, hospital=h, node=[bloque, piso, urg][i % 3],
                               status=Asset.Status.ACTIVE)
            Task.objects.create(work_order=ot, asset=extra, status=base.status, title="otra",
                                task_type=base.task_type, sort_order=i + 1,
                                calculated_date=base.calculated_date, scheduled_date=base.scheduled_date)
        with CaptureQueriesContext(connection) as c:
            _detalle(admin, ot)
        return len(c)

    pocas = consultas(1)
    muchas = consultas(8)
    assert muchas <= pocas + 1, (pocas, muchas)


def test_la_direccion_de_la_sububicacion_no_entra_en_el_hash(arbol, admin):
    h, bloque, piso, urg = arbol
    ot, _ = _ot(h, admin, urg, location=piso)
    antes = compute_wo_content_hash(ot)
    AssetNode.objects.filter(pk=bloque.pk).update(address="Otra calle 99", latitude="6.3", longitude="-75.4")
    AssetNode.objects.filter(pk=urg.pk).update(address="Urgencias, torre sur")
    assert compute_wo_content_hash(ot) == antes


def test_el_paquete_offline_trae_la_sububicacion(arbol, admin):
    """La app del tecnico guarda el detalle del paquete: sin red ve lo mismo."""
    h, bloque, piso, urg = arbol
    ot, _ = _ot(h, admin, urg, location=piso)
    c = APIClient()
    c.force_authenticate(user=admin)
    resp = c.get(f"/api/work-orders/{ot.id}/offline-bundle/")
    assert resp.status_code == 200
    detalle = resp.data["work_order"]
    assert detalle["tasks"][0]["asset"]["sublocation"]["address"] == "Calle 10 #20-30, Medellin"
    assert detalle["location_detail"]["name"] == "Piso 1"
