"""
Contratos de mantenimiento y garantias (decision del 2026-09-23): el contrato
cubre un hospital o una rama del arbol, la garantia una lista de equipos. Un
vencimiento solo avisa; los administradores reciben un correo a los 60 dias,
a los 30 y al vencer. El hospital ve los suyos y descarga el documento.
"""

from datetime import timedelta

import pytest
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from model_bakery import baker
from rest_framework.test import APIClient

from apps.assets.contracts import avisos_pendientes, cobertura_del_activo, hoy
from apps.assets.models import Asset, AssetNode, Contract, ContractAsset, Hospital
from apps.assets.tasks import send_contract_expiry_notices
from apps.users.models import User

pytestmark = pytest.mark.django_db
HOY = hoy()


def cliente(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture(autouse=True)
def almacenamiento(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    }


@pytest.fixture
def d():
    a = baker.make(Hospital, name="Clinica A", is_active=True)
    b = baker.make(Hospital, name="Clinica B", is_active=True)
    torre = AssetNode.objects.create(hospital=a, name="Torre 1")
    piso = AssetNode.objects.create(hospital=a, name="Piso 3", parent=torre)
    otro_piso = AssetNode.objects.create(hospital=a, name="Piso 4", parent=torre)
    return {
        "a": a, "b": b, "torre": torre, "piso": piso, "otro_piso": otro_piso,
        "admin": baker.make(User, role=User.Role.ADMIN, is_active=True, email="jefe@todogas.co"),
        "sup": baker.make(User, role=User.Role.SUP, is_active=True),
        "tec": baker.make(User, role=User.Role.TEC, is_active=True),
        "cli": baker.make(User, role=User.Role.CLI, is_active=True, hospital=a),
        "cli_piso": baker.make(User, role=User.Role.CLI, is_active=True, hospital=a, scope_node=piso),
        "equipo": Asset.objects.create(hospital=a, node=piso, name="Alarma", code="ALR-3"),
        "equipo_4": Asset.objects.create(hospital=a, node=otro_piso, name="Alarma 4", code="ALR-4"),
        "ajeno": Asset.objects.create(hospital=b, name="Alarma B", code="ALR-B"),
    }


def contrato(hospital, inicio=-100, fin=265, node=None, name="CONTRATO", **kw):
    return Contract.objects.create(
        kind=Contract.Kind.MAINTENANCE, name=name, hospital=hospital, node=node,
        start_date=HOY + timedelta(days=inicio), end_date=HOY + timedelta(days=fin), **kw,
    )


def garantia(hospital, equipos, inicio=-100, fin=265, name="GARANTIA"):
    g = Contract.objects.create(
        kind=Contract.Kind.WARRANTY, name=name, hospital=hospital,
        start_date=HOY + timedelta(days=inicio), end_date=HOY + timedelta(days=fin),
    )
    for e in equipos:
        ContractAsset.objects.create(contract=g, asset=e)
    return g


# ── Alta y validaciones ───────────────────────────────────────────────────────

def test_el_admin_carga_un_contrato_del_hospital(d):
    r = cliente(d["admin"]).post("/api/contracts/", {
        "kind": "MAINTENANCE", "name": "CONTRATO 2026-2027 A", "hospital": str(d["a"].id),
        "start_date": str(HOY), "end_date": str(HOY + timedelta(days=364)),
    }, format="json")
    assert r.status_code == 201, r.data
    assert r.data["status"] == "ACTIVE"
    assert r.data["created_by_name"] is not None
    assert Contract.objects.get(pk=r.data["id"]).created_by == d["admin"]


def test_la_garantia_sube_con_su_documento_y_sus_equipos(d):
    pdf = SimpleUploadedFile("garantia.pdf", b"%PDF-1.4 prueba", content_type="application/pdf")
    r = cliente(d["admin"]).post("/api/contracts/", {
        "kind": "WARRANTY", "name": "GARANTIA ALARMAS", "hospital": str(d["a"].id),
        "asset_ids": [str(d["equipo"].id), str(d["equipo_4"].id)],
        "start_date": str(HOY - timedelta(days=10)), "end_date": str(HOY + timedelta(days=720)),
        "file": pdf,
    }, format="multipart")
    assert r.status_code == 201, r.data
    assert r.data["file_name"] == "garantia.pdf"
    assert r.data["file_url"]
    assert {a["code"] for a in r.data["assets_info"]} == {"ALR-3", "ALR-4"}


@pytest.mark.parametrize("cambio, campo", [
    ({"kind": "WARRANTY"}, "asset_ids"),                       # garantia sin equipos
    ({"asset_ids": ["EQUIPO"]}, "asset_ids"),                  # contrato con equipos sueltos
    ({"end_date": str(HOY - timedelta(days=1))}, "end_date"),  # fin antes del inicio
    ({"node": "NODO_B"}, "node"),                              # ubicacion de otro hospital
])
def test_lo_que_no_se_acepta(d, cambio, campo):
    nodo_b = AssetNode.objects.create(hospital=d["b"], name="Sede B")
    datos = {
        "kind": "MAINTENANCE", "name": "X", "hospital": str(d["a"].id),
        "start_date": str(HOY), "end_date": str(HOY + timedelta(days=30)),
    }
    for k, v in cambio.items():
        datos[k] = [str(d["equipo"].id)] if v == ["EQUIPO"] else str(nodo_b.id) if v == "NODO_B" else v
    r = cliente(d["admin"]).post("/api/contracts/", datos, format="json")
    assert r.status_code == 400
    assert campo in r.data


def test_la_garantia_no_cubre_equipos_de_otro_hospital(d):
    r = cliente(d["admin"]).post("/api/contracts/", {
        "kind": "WARRANTY", "name": "G", "hospital": str(d["a"].id),
        "asset_ids": [str(d["ajeno"].id)],
        "start_date": str(HOY), "end_date": str(HOY + timedelta(days=30)),
    }, format="json")
    assert r.status_code == 400
    assert "ALR-B" in str(r.data["asset_ids"])


def test_no_se_cambia_el_tipo_y_se_editan_los_equipos(d):
    g = garantia(d["a"], [d["equipo"]])
    c = cliente(d["admin"])
    r = c.patch(f"/api/contracts/{g.id}/", {"kind": "MAINTENANCE"}, format="json")
    assert r.status_code == 400 and "kind" in r.data
    r = c.patch(f"/api/contracts/{g.id}/", {"asset_ids": [str(d["equipo_4"].id)]}, format="json")
    assert r.status_code == 200, r.data
    assert list(g.assets.values_list("code", flat=True)) == ["ALR-4"]


def test_quitar_el_documento_y_borrar_la_garantia(d):
    g = garantia(d["a"], [d["equipo"]])
    g.file_key, g.file_name = "contracts/x.pdf", "x.pdf"
    g.save()
    c = cliente(d["admin"])
    r = c.patch(f"/api/contracts/{g.id}/", {"remove_file": True}, format="json")
    assert r.data["file_url"] is None and r.data["file_name"] == ""
    assert c.delete(f"/api/contracts/{g.id}/").status_code == 204
    assert not ContractAsset.objects.exists()


def test_solo_el_admin_los_carga_y_el_tecnico_no_los_ve(d):
    datos = {"kind": "MAINTENANCE", "name": "X", "hospital": str(d["a"].id),
             "start_date": str(HOY), "end_date": str(HOY)}
    assert cliente(d["sup"]).post("/api/contracts/", datos, format="json").status_code == 403
    assert cliente(d["cli"]).post("/api/contracts/", datos, format="json").status_code == 403
    assert cliente(d["sup"]).get("/api/contracts/").status_code == 200
    assert cliente(d["tec"]).get("/api/contracts/").status_code == 403


# ── Alcance ───────────────────────────────────────────────────────────────────

def test_el_hospital_solo_ve_los_suyos(d):
    propio = contrato(d["a"])
    contrato(d["b"])
    r = cliente(d["cli"]).get("/api/contracts/")
    assert [x["id"] for x in r.data["results"]] == [str(propio.id)]


def test_la_cuenta_de_un_piso_ve_lo_que_la_cubre(d):
    todo = contrato(d["a"], name="TODO EL HOSPITAL")
    torre = contrato(d["a"], node=d["torre"], name="TORRE")
    piso = contrato(d["a"], node=d["piso"], name="PISO 3")
    contrato(d["a"], node=d["otro_piso"], name="PISO 4")
    suya = garantia(d["a"], [d["equipo"]], name="G PISO 3")
    garantia(d["a"], [d["equipo_4"]], name="G PISO 4")
    r = cliente(d["cli_piso"]).get("/api/contracts/")
    assert {x["id"] for x in r.data["results"]} == {str(c.id) for c in (todo, torre, piso, suya)}


# ── Cobertura ─────────────────────────────────────────────────────────────────

def test_el_equipo_sabe_si_esta_en_garantia_y_bajo_contrato(d):
    garantia(d["a"], [d["equipo"]], fin=-1, name="VENCIDA")
    vigente = garantia(d["a"], [d["equipo"]], name="VIGENTE")
    contrato(d["a"], node=d["otro_piso"], name="OTRO PISO")
    torre = contrato(d["a"], node=d["torre"], name="TORRE")

    r = cliente(d["admin"]).get(f"/api/assets/{d['equipo'].id}/")
    assert r.data["coverage"]["warranty"]["id"] == str(vigente.id)
    assert r.data["coverage"]["contract"]["id"] == str(torre.id), "cuelga de la torre"

    sin_nada = cobertura_del_activo(d["ajeno"])
    assert sin_nada == {"warranty": None, "contract": None}


def test_el_hospital_sin_contrato_vigente_queda_marcado(d):
    contrato(d["a"], fin=-1)
    vigente = contrato(d["b"])
    r = cliente(d["admin"]).get("/api/hospitals/")
    estado = {h["id"]: h["contract_status"] for h in r.data["results"]}
    assert estado[str(d["a"].id)] == {"has_active": False, "current": None}
    assert estado[str(d["b"].id)]["current"]["id"] == str(vigente.id)
    r = cliente(d["admin"]).get(f"/api/hospitals/{d['b'].id}/")
    assert r.data["contract_status"]["has_active"] is True


# ── Tablero ───────────────────────────────────────────────────────────────────

def test_el_resumen_del_tablero(d):
    por_vencer = contrato(d["a"], fin=20, name="POR VENCER")
    vencido = contrato(d["b"], fin=-5, name="VENCIDO")
    renovado = contrato(d["b"], inicio=-400, fin=-40, name="VIEJO")
    contrato(d["b"], inicio=-39, fin=-10, name="YA RENOVADO")
    contrato(d["b"], inicio=-9, fin=-6, name="PUENTE")  # renueva al anterior
    r = cliente(d["sup"]).get("/api/contracts/summary/")
    assert r.status_code == 200
    assert [x["id"] for x in r.data["expiring"]] == [str(por_vencer.id)]
    vencidos = {x["name"] for x in r.data["recently_expired"]}
    assert "VENCIDO" in vencidos and "YA RENOVADO" not in vencidos
    assert str(renovado.id) not in {x["id"] for x in r.data["recently_expired"]}, "hace mas de 30 dias"
    assert {h["name"] for h in r.data["hospitals_without_contract"]} == {"Clinica B"}
    assert cliente(d["cli"]).get("/api/contracts/summary/").status_code == 403


def test_filtro_por_estado(d):
    contrato(d["a"], fin=20, name="POR VENCER")
    contrato(d["a"], fin=200, name="VIGENTE")
    contrato(d["a"], fin=-3, name="VENCIDO")
    contrato(d["a"], inicio=10, fin=400, name="FUTURO")
    c = cliente(d["admin"])

    def nombres(estado):
        return {x["name"] for x in c.get(f"/api/contracts/?status={estado}").data["results"]}

    assert nombres("ACTIVE") == {"POR VENCER", "VIGENTE"}
    assert nombres("EXPIRING") == {"POR VENCER"}
    assert nombres("EXPIRED") == {"VENCIDO"}
    assert nombres("UPCOMING") == {"FUTURO"}


# ── Avisos de vencimiento ─────────────────────────────────────────────────────

def test_cada_documento_avisa_una_vez_a_60_a_30_y_al_vencer(d):
    c = contrato(d["a"], fin=45)
    assert [a for _, a in avisos_pendientes(HOY)] == ["60"]
    send_contract_expiry_notices()
    assert len(mail.outbox) == 1 and mail.outbox[0].to == ["jefe@todogas.co"]
    assert "CONTRATO" in mail.outbox[0].body

    send_contract_expiry_notices()
    assert len(mail.outbox) == 1, "el mismo dia no repite"
    assert [a for _, a in avisos_pendientes(HOY + timedelta(days=15))] == ["30"]
    c.refresh_from_db()
    c.last_notice = "30"
    c.save()
    assert [a for _, a in avisos_pendientes(HOY + timedelta(days=46))] == ["EXPIRED"]


def test_una_prorroga_reinicia_los_avisos(d):
    c = contrato(d["a"], fin=20, last_notice="30")
    r = cliente(d["admin"]).patch(
        f"/api/contracts/{c.id}/", {"end_date": str(HOY + timedelta(days=50))}, format="json",
    )
    assert r.status_code == 200
    c.refresh_from_db()
    assert c.last_notice == ""
    assert [a for _, a in avisos_pendientes(HOY)] == ["60"]


def test_no_avisa_lo_renovado_ni_lo_vencido_hace_tiempo(d):
    viejo = contrato(d["a"], fin=10, name="2025-2026")
    contrato(d["a"], inicio=11, fin=376, name="2026-2027")
    contrato(d["b"], fin=-90, name="HISTORICO")
    assert avisos_pendientes(HOY) == []
    viejo.refresh_from_db()
    assert viejo.last_notice == "30", "queda marcado para no volver a mirarlo"
    send_contract_expiry_notices()
    assert mail.outbox == []


# ── Portal ────────────────────────────────────────────────────────────────────

def test_el_portal_trae_sus_contratos_con_el_documento(d):
    g = garantia(d["a"], [d["equipo"]])
    g.file_key, g.file_name = "contracts/g.pdf", "g.pdf"
    g.save()
    contrato(d["a"], inicio=-800, fin=-400, name="MUY VIEJO")
    contrato(d["b"], name="DE OTRO")
    r = cliente(d["cli"]).get("/api/client-portal/summary/")
    assert r.status_code == 200
    assert [x["name"] for x in r.data["contracts"]] == ["GARANTIA"]
    assert r.data["contracts"][0]["file_url"].endswith("contracts/g.pdf")
    assert r.data["contracts"][0]["assets"][0]["code"] == "ALR-3"
    assert r.data["has_active_contract"] is False
