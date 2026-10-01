"""
Filtros de la lista de OT por hospital, ubicacion y activo (audio2 03:53):
"tendriamos que tener mas filtros de ubicacion o por activos". La ubicacion
trae lo de todo lo que tiene dentro, como en la pantalla de activos.
"""

import uuid

import pytest
from rest_framework.test import APIClient

from apps.assets.models import Asset, AssetNode, Hospital
from apps.maintenance.testing import make_work_order
from apps.users.models import User

pytestmark = pytest.mark.django_db
URL = "/api/work-orders/"


@pytest.fixture
def d():
    admin = User.objects.create_user(
        email=f"{uuid.uuid4()}@t.co", password="x", first_name="A", last_name="B", role=User.Role.ADMIN,
    )
    h1 = Hospital.objects.create(name="H1", code=uuid.uuid4().hex[:8])
    h2 = Hospital.objects.create(name="H2", code=uuid.uuid4().hex[:8])
    bloque = AssetNode.objects.create(hospital=h1, name="Bloque A")
    piso = AssetNode.objects.create(hospital=h1, name="Piso 3", parent=bloque)
    sala = AssetNode.objects.create(hospital=h1, name="UCI", parent=piso)
    otro_bloque = AssetNode.objects.create(hospital=h1, name="Bloque B")

    def activo(h, nodo, nombre):
        return Asset.objects.create(hospital=h, node=nodo, name=nombre, code=uuid.uuid4().hex[:8])

    en_uci = activo(h1, sala, "Toma UCI")
    en_b = activo(h1, otro_bloque, "Toma B")
    en_h2 = activo(h2, None, "Toma H2")
    ots = {
        "uci": make_work_order(en_uci, admin, title="uci"),
        "uci2": make_work_order(en_uci, admin, title="uci2"),
        "b": make_work_order(en_b, admin, title="b"),
        "h2": make_work_order(en_h2, admin, title="h2"),
    }
    # Una visita cuya ubicacion es el bloque B, aunque el activo este en la UCI.
    visita = make_work_order(en_uci, admin, title="visita")
    visita.location = otro_bloque
    visita.save(update_fields=["location"])
    ots["visita"] = visita

    c = APIClient()
    c.force_authenticate(user=admin)
    return {"c": c, "h1": h1, "bloque": bloque, "piso": piso, "otro_bloque": otro_bloque,
            "en_uci": en_uci, "ots": ots}


def titulos(d, **params):
    r = d["c"].get(URL, params)
    assert r.status_code == 200, r.data
    datos = r.data["results"] if isinstance(r.data, dict) else r.data
    return sorted(w["title"] for w in datos)


def test_por_hospital(d):
    assert titulos(d, hospital_id=d["h1"].id) == ["b", "uci", "uci2", "visita"]


def test_por_ubicacion_incluye_lo_que_tiene_dentro(d):
    assert titulos(d, node_id=d["bloque"].id) == ["uci", "uci2", "visita"]
    assert titulos(d, node_id=d["piso"].id) == ["uci", "uci2", "visita"]


def test_por_ubicacion_cuenta_la_de_la_visita(d):
    assert titulos(d, node_id=d["otro_bloque"].id) == ["b", "visita"]


def test_por_activo(d):
    assert titulos(d, asset_id=d["en_uci"].id) == ["uci", "uci2", "visita"]


def test_filtros_combinados_sin_repetir(d):
    assert titulos(d, hospital_id=d["h1"].id, node_id=d["otro_bloque"].id, search="visita") == ["visita"]


def test_un_id_mal_formado_no_encuentra_nada(d):
    for p in ("hospital_id", "node_id", "asset_id"):
        assert titulos(d, **{p: "no-es-un-id"}) == []
