"""Crear ubicaciones por API debe funcionar y fallar con 400, nunca con 500.

Regresion: AssetNodeViewSet usaba AssetNodeSerializer tambien para escribir, y
ahi `hospital` y `parent` son SerializerMethodField (solo lectura). El POST los
descartaba en silencio y el INSERT chocaba contra el NOT NULL de hospital_id,
devolviendo HTTP 500 (IntegrityError). Crear ubicaciones era imposible, y por eso
todos los activos mostraban "Ubicacion —".
"""

import uuid

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.assets.models import Asset, AssetNode, Hospital
from apps.users.models import User

URL = "/api/asset-nodes/"


def auth_client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email=f"{uuid.uuid4()}@test.com", password="pass",
        first_name="A", last_name="B", role=User.Role.ADMIN,
    )


@pytest.fixture
def hospital(db):
    return Hospital.objects.create(name="H1", code=str(uuid.uuid4())[:8])


@pytest.fixture
def otro_hospital(db):
    return Hospital.objects.create(name="H2", code=str(uuid.uuid4())[:8])


def payload(hospital, **extra):
    datos = {
        "hospital": str(hospital.id),
        "name": "Piso 1",
        "node_type": AssetNode.NodeType.AREA,
        "code": "P1",
    }
    datos.update(extra)
    return datos


def node_id(resp):
    return resp.json()["id"]


# -- Creacion ---------------------------------------------------------------

def test_create_node_succeeds(hospital, admin_user):
    resp = auth_client(admin_user).post(URL, payload(hospital), format="json")

    assert resp.status_code == status.HTTP_201_CREATED, resp.data
    nodo = AssetNode.objects.get(id=node_id(resp))
    assert nodo.hospital_id == hospital.id


def test_create_response_uses_the_read_shape(hospital, admin_user):
    """El cliente recibe hospital anidado y el path ya materializado."""
    resp = auth_client(admin_user).post(URL, payload(hospital), format="json")

    cuerpo = resp.json()
    assert cuerpo["hospital"]["id"] == str(hospital.id)
    assert cuerpo["path"] == "Piso 1"


def test_create_without_hospital_returns_400_not_500(admin_user):
    """El nucleo del bug: faltar hospital tiene que ser validacion, no crash."""
    resp = auth_client(admin_user).post(
        URL, {"name": "Sin hospital", "node_type": AssetNode.NodeType.AREA},
        format="json",
    )

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "hospital" in resp.json()


def test_child_node_builds_its_path_from_the_parent(hospital, admin_user):
    client = auth_client(admin_user)
    padre = node_id(client.post(URL, payload(hospital, name="Piso 1"), format="json"))

    hijo = client.post(
        URL, payload(hospital, name="Sala 101", parent=padre), format="json"
    )

    assert hijo.status_code == status.HTTP_201_CREATED
    assert hijo.json()["path"] == "Piso 1/Sala 101"


def test_path_is_not_taken_from_the_client(hospital, admin_user):
    """`path` lo materializa el modelo; mandarlo no debe colarse."""
    resp = auth_client(admin_user).post(
        URL, payload(hospital, path="ruta/inventada"), format="json"
    )

    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.json()["path"] == "Piso 1"


# -- Validaciones -----------------------------------------------------------

def test_parent_from_another_hospital_is_rejected(hospital, otro_hospital, admin_user):
    client = auth_client(admin_user)
    ajeno = node_id(
        client.post(URL, payload(otro_hospital, name="Ajeno"), format="json")
    )

    resp = client.post(
        URL, payload(hospital, name="Sala", parent=ajeno), format="json"
    )

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "parent" in resp.json()


def test_duplicate_name_under_same_parent_returns_400_not_500(hospital, admin_user):
    """La restriccion unica saltaba como IntegrityError, otro 500."""
    client = auth_client(admin_user)
    client.post(URL, payload(hospital, name="Piso 1"), format="json")

    resp = client.post(URL, payload(hospital, name="Piso 1"), format="json")

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "name" in resp.json()


def test_same_name_under_different_parents_is_allowed(hospital, admin_user):
    client = auth_client(admin_user)
    a = node_id(client.post(URL, payload(hospital, name="Ala A"), format="json"))
    b = node_id(client.post(URL, payload(hospital, name="Ala B"), format="json"))

    client.post(URL, payload(hospital, name="Sala 1", parent=a), format="json")
    resp = client.post(
        URL, payload(hospital, name="Sala 1", parent=b), format="json"
    )

    assert resp.status_code == status.HTTP_201_CREATED


def test_node_cannot_become_its_own_descendant(hospital, admin_user):
    client = auth_client(admin_user)
    padre = node_id(client.post(URL, payload(hospital, name="Piso 1"), format="json"))
    hijo = node_id(
        client.post(URL, payload(hospital, name="Sala", parent=padre), format="json")
    )

    resp = client.patch(URL + padre + "/", {"parent": hijo}, format="json")

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "parent" in resp.json()


# -- Actualizacion ----------------------------------------------------------

def test_renaming_a_node_repaths_its_descendants(hospital, admin_user):
    client = auth_client(admin_user)
    padre = node_id(client.post(URL, payload(hospital, name="Piso 1"), format="json"))
    hijo = node_id(
        client.post(URL, payload(hospital, name="Sala", parent=padre), format="json")
    )

    client.patch(URL + padre + "/", {"name": "Piso Uno"}, format="json")

    assert AssetNode.objects.get(id=hijo).path == "Piso Uno/Sala"


def test_moving_a_node_repaths_its_descendants(hospital, admin_user):
    """Antes solo se recalculaba al renombrar, asi que mover dejaba rutas viejas."""
    client = auth_client(admin_user)
    a = node_id(client.post(URL, payload(hospital, name="Ala A"), format="json"))
    b = node_id(client.post(URL, payload(hospital, name="Ala B"), format="json"))
    medio = node_id(
        client.post(URL, payload(hospital, name="Piso 1", parent=a), format="json")
    )
    hoja = node_id(
        client.post(URL, payload(hospital, name="Sala", parent=medio), format="json")
    )

    client.patch(URL + medio + "/", {"parent": b}, format="json")

    assert AssetNode.objects.get(id=hoja).path == "Ala B/Piso 1/Sala"


# -- Borrado ----------------------------------------------------------------

def test_delete_node_with_children_returns_400_not_500(hospital, admin_user):
    client = auth_client(admin_user)
    padre = node_id(client.post(URL, payload(hospital, name="Piso 1"), format="json"))
    client.post(URL, payload(hospital, name="Sala", parent=padre), format="json")

    resp = client.delete(URL + padre + "/")

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "sububicaciones" in resp.json()["detail"]


def test_delete_node_with_assets_returns_400_not_500(hospital, admin_user):
    client = auth_client(admin_user)
    nodo = node_id(client.post(URL, payload(hospital, name="Piso 1"), format="json"))
    Asset.objects.create(
        hospital=hospital, node_id=nodo, name="Equipo",
        code=str(uuid.uuid4())[:10], status=Asset.Status.ACTIVE,
    )

    resp = client.delete(URL + nodo + "/")

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "activos" in resp.json()["detail"]


def test_delete_empty_node_works(hospital, admin_user):
    client = auth_client(admin_user)
    nodo = node_id(client.post(URL, payload(hospital, name="Piso 1"), format="json"))

    resp = client.delete(URL + nodo + "/")

    assert resp.status_code == status.HTTP_204_NO_CONTENT
    assert not AssetNode.objects.filter(id=nodo).exists()
