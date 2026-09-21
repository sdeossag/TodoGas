"""El listado de ubicaciones alimenta el editor de arbol de la interfaz.

La pantalla necesita, por cada nodo, cuantas sububicaciones y cuantos activos
cuelgan de el: con eso decide si ofrece "Eliminar" (el backend lo rechaza si hay
cualquiera de los dos) y enlaza a los activos de la ubicacion. Antes el listado
no traia `asset_count`, y `children_count` lanzaba una consulta por nodo.
"""

import uuid

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.assets.models import Asset, AssetNode, Hospital
from apps.users.models import User

URL = "/api/asset-nodes/"


@pytest.fixture
def cliente(db):
    usuario = User.objects.create_user(
        email=f"{uuid.uuid4()}@test.com", password="pass",
        first_name="A", last_name="B", role=User.Role.ADMIN,
    )
    c = APIClient()
    c.force_authenticate(user=usuario)
    return c


@pytest.fixture
def hospital(db):
    return Hospital.objects.create(name="H1", code=str(uuid.uuid4())[:8])


def nodo(hospital, nombre, padre=None, **extra):
    return AssetNode.objects.create(
        hospital=hospital, parent=padre, name=nombre, **extra
    )


def activo(hospital, ubicacion, estado=Asset.Status.ACTIVE):
    return Asset.objects.create(
        hospital=hospital, node=ubicacion, name="Equipo",
        code=str(uuid.uuid4())[:10], status=estado,
    )


def listar(cliente, hospital):
    resp = cliente.get(URL, {"hospital_id": str(hospital.id), "page_size": 200})
    assert resp.status_code == 200
    return {fila["name"]: fila for fila in resp.json()["results"]}


def test_conteos_son_directos_no_acumulan_descendientes(cliente, hospital):
    torre = nodo(hospital, "Torre A")
    piso = nodo(hospital, "Piso 3", padre=torre)
    urgencias = nodo(hospital, "Urgencias", padre=piso)
    nodo(hospital, "UCI", padre=piso)
    activo(hospital, urgencias)
    activo(hospital, urgencias)
    activo(hospital, piso)

    filas = listar(cliente, hospital)

    assert filas["Torre A"]["children_count"] == 1
    assert filas["Torre A"]["asset_count"] == 0
    assert filas["Piso 3"]["children_count"] == 2
    assert filas["Piso 3"]["asset_count"] == 1
    assert filas["Urgencias"]["children_count"] == 0
    assert filas["Urgencias"]["asset_count"] == 2
    assert filas["UCI"]["asset_count"] == 0


def test_cuenta_activos_de_cualquier_estado(cliente, hospital):
    # Un activo dado de baja tambien impide borrar la ubicacion
    # (on_delete=PROTECT). Si el conteo lo omitiera, la interfaz ofreceria
    # "Eliminar" y el servidor lo rechazaria.
    sala = nodo(hospital, "Sala")
    activo(hospital, sala, estado=Asset.Status.DECOMMISSIONED)
    activo(hospital, sala, estado=Asset.Status.OUT_OF_SERVICE)

    assert listar(cliente, hospital)["Sala"]["asset_count"] == 2


def test_incluye_ubicaciones_inactivas(cliente, hospital):
    # El endpoint /tree/ oculta las inactivas; el editor necesita verlas para
    # poder reactivarlas.
    nodo(hospital, "Activa")
    nodo(hospital, "Archivada", is_active=False)

    filas = listar(cliente, hospital)

    assert filas["Archivada"]["is_active"] is False
    assert "Activa" in filas


def test_no_mezcla_hospitales(cliente, hospital):
    otro = Hospital.objects.create(name="H2", code=str(uuid.uuid4())[:8])
    nodo(otro, "Ajena")
    nodo(hospital, "Propia")

    assert set(listar(cliente, hospital)) == {"Propia"}


def test_numero_de_consultas_no_crece_con_los_nodos(cliente, hospital):
    def consultas_para_listar():
        with CaptureQueriesContext(connection) as ctx:
            listar(cliente, hospital)
        return len(ctx.captured_queries)

    raiz = nodo(hospital, "Raiz")
    activo(hospital, raiz)
    con_uno = consultas_para_listar()

    for i in range(15):
        hijo = nodo(hospital, f"Hijo {i}", padre=raiz)
        activo(hospital, hijo)
    con_dieciseis = consultas_para_listar()

    assert con_dieciseis == con_uno


def test_crear_devuelve_conteos_en_cero(cliente, hospital):
    # La respuesta del POST usa el serializer de lectura sobre un nodo sin
    # anotaciones: debe caer al conteo directo y no romper.
    resp = cliente.post(
        URL, {"hospital": str(hospital.id), "name": "Nuevo"}, format="json"
    )

    assert resp.status_code == 201
    assert resp.json()["children_count"] == 0
    assert resp.json()["asset_count"] == 0


def test_mover_conserva_conteos_en_la_respuesta(cliente, hospital):
    origen = nodo(hospital, "Origen")
    destino = nodo(hospital, "Destino")
    movido = nodo(hospital, "Movido", padre=origen)
    nodo(hospital, "Nieto", padre=movido)
    activo(hospital, movido)

    resp = cliente.patch(
        f"{URL}{movido.id}/", {"parent": str(destino.id)}, format="json"
    )

    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["path"] == "Destino/Movido"
    assert cuerpo["children_count"] == 1
    assert cuerpo["asset_count"] == 1
    assert AssetNode.objects.get(name="Nieto").path == "Destino/Movido/Nieto"
