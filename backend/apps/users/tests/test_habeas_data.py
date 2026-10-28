"""Habeas Data (Ley 1581): consentimiento, datos personales y anonimizacion."""

import re
import uuid
from datetime import timedelta
from pathlib import Path

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.audit.models import AuditLog
from apps.evidence.models import Signature, UserSignature
from apps.evidence.tests.firmas import firmar
from apps.maintenance.testing import make_work_order
from apps.users.models import PrivacyConsent, User

CONSENT = "/api/users/me/privacy-consent/"
MIS_DATOS = "/api/users/me/personal-data/"


def cliente(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def crear(role=User.Role.TEC, **kw):
    return User.objects.create_user(
        email=f"{uuid.uuid4()}@test.com", password="pass", first_name="Ana",
        last_name="Lopez", role=role, phone="3001112233", **kw,
    )


@pytest.fixture(autouse=True)
def _cache(settings):
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


@pytest.fixture
def admin(db):
    return crear(User.Role.ADMIN)


@pytest.fixture
def tec(db):
    return crear()


def inactivar(user, hace_dias, *, last_login=None):
    antes = timezone.now() - timedelta(days=hace_dias)
    User.objects.filter(pk=user.pk).update(
        is_active=False, deactivated_at=antes, last_login=last_login or antes,
        created_at=antes - timedelta(days=30),
    )
    user.refresh_from_db()


# -- Consentimiento ----------------------------------------------------------

def test_sin_aceptar_es_requerido(tec, settings):
    settings.PRIVACY_NOTICE_VERSION = "v1"
    r = cliente(tec).get(CONSENT)
    assert r.status_code == 200
    assert r.data["required"] is True
    assert r.data["version"] == "v1"
    assert r.data["accepted_at"] is None
    assert r.data["policy_url"] == ""


def test_aceptar_registra_version_ip_y_agente(tec, settings):
    settings.PRIVACY_NOTICE_VERSION = "v1"
    c = cliente(tec)
    r = c.post(CONSENT, HTTP_USER_AGENT="TestAgent/1", REMOTE_ADDR="10.1.2.3")
    assert r.status_code == 200
    assert r.data["required"] is False
    assert r.data["accepted_at"] is not None
    pc = PrivacyConsent.objects.get(user=tec)
    assert (pc.version, pc.ip_address, pc.user_agent) == ("v1", "10.1.2.3", "TestAgent/1")
    assert c.get(CONSENT).data["required"] is False


def test_aceptar_dos_veces_no_duplica(tec, settings):
    settings.PRIVACY_NOTICE_VERSION = "v1"
    c = cliente(tec)
    c.post(CONSENT)
    c.post(CONSENT)
    assert PrivacyConsent.objects.filter(user=tec).count() == 1


def test_cambio_de_version_vuelve_a_pedir(tec, settings):
    settings.PRIVACY_NOTICE_VERSION = "v1"
    c = cliente(tec)
    c.post(CONSENT)
    settings.PRIVACY_NOTICE_VERSION = "v2"
    assert c.get(CONSENT).data["required"] is True
    c.post(CONSENT)
    assert c.get(CONSENT).data["required"] is False
    assert PrivacyConsent.objects.filter(user=tec).count() == 2


def test_consentimiento_exige_sesion(db):
    assert APIClient().get(CONSENT).status_code == 401
    assert APIClient().post(CONSENT).status_code == 401


def test_no_hay_borrado_de_consentimientos(tec):
    pc = PrivacyConsent.objects.create(user=tec, version="v1")
    c = cliente(tec)
    assert c.delete(CONSENT).status_code == 405
    assert c.delete(f"/api/users/{pc.id}/").status_code in (403, 404)
    assert PrivacyConsent.objects.filter(pk=pc.pk).exists()


def test_version_del_aviso_coincide_con_el_frontend():
    from django.conf import settings

    fuente = Path(__file__).resolve().parents[4] / "frontend" / "src" / "legal" / "avisoPrivacidad.js"
    version = re.search(r"VERSION\s*=\s*'([^']+)'", fuente.read_text(encoding="utf-8")).group(1)
    assert version == settings.PRIVACY_NOTICE_VERSION


# -- Mis datos ---------------------------------------------------------------

def test_mis_datos_personales(tec, admin):
    firmar(tec)
    PrivacyConsent.objects.create(user=tec, version="v1")
    h = Hospital.objects.create(name="H", code="HH1")
    asset = Asset.objects.create(hospital=h, name="E", code="E1", status=Asset.Status.ACTIVE)
    make_work_order(asset, admin, status="COMPLETED", assigned_to=tec)
    r = cliente(tec).get(MIS_DATOS)
    assert r.status_code == 200
    d = r.data
    assert d["perfil"]["correo"] == tec.email
    assert d["perfil"]["telefono"] == "3001112233"
    assert d["firma_guardada"]["tiene"] is True
    assert "file_url" not in str(d) and "image" not in str(d)
    assert [c["version"] for c in d["consentimientos"]] == ["v1"]
    assert d["actividad"]["ot_asignadas"] == 1
    assert d["actividad"]["ot_ejecutadas"] == 1
    assert d["actividad"]["fotos"] == 0


def test_mis_datos_exige_sesion(db):
    assert APIClient().get(MIS_DATOS).status_code == 401


# -- Permisos ----------------------------------------------------------------

@pytest.mark.parametrize("rol", [User.Role.TEC, User.Role.SUP, User.Role.CLI])
def test_no_admin_no_exporta_ni_anonimiza(rol, db):
    h = Hospital.objects.create(name="H", code="HH2") if rol == User.Role.CLI else None
    otro = crear(rol, hospital=h)
    objetivo = crear()
    inactivar(objetivo, 900)
    c = cliente(otro)
    assert c.get(f"/api/users/{objetivo.id}/personal-data/").status_code == 403
    assert c.post(f"/api/users/{objetivo.id}/anonymize/").status_code == 403
    objetivo.refresh_from_db()
    assert objetivo.first_name == "Ana"


def test_admin_exporta_datos_de_otro_y_queda_auditoria(admin, tec):
    r = cliente(admin).get(f"/api/users/{tec.id}/personal-data/")
    assert r.status_code == 200
    assert r.data["perfil"]["correo"] == tec.email
    log = AuditLog.objects.get(action=AuditLog.Action.EXPORT, entity_id=tec.id)
    assert log.user == admin and log.entity_type == "User"


# -- Anonimizar --------------------------------------------------------------

def test_rechaza_cuenta_activa(admin, tec):
    r = cliente(admin).post(f"/api/users/{tec.id}/anonymize/")
    assert r.status_code == 400
    assert "activa" in r.data["detail"]


def test_rechaza_inactiva_reciente(admin, tec):
    inactivar(tec, 100)
    r = cliente(admin).post(f"/api/users/{tec.id}/anonymize/")
    assert r.status_code == 400
    assert "730" in r.data["detail"]


def test_rechaza_si_entro_hace_poco_aunque_la_desactivacion_sea_vieja(admin, tec):
    inactivar(tec, 900, last_login=timezone.now() - timedelta(days=10))
    assert cliente(admin).post(f"/api/users/{tec.id}/anonymize/").status_code == 400


def test_no_se_anonimiza_a_si_mismo(admin):
    assert cliente(admin).post(f"/api/users/{admin.id}/anonymize/").status_code == 400


def test_desactivar_guarda_la_fecha_y_reactivar_la_limpia(admin, tec):
    c = cliente(admin)
    c.post(f"/api/users/{tec.id}/deactivate/")
    tec.refresh_from_db()
    assert tec.deactivated_at is not None
    c.patch(f"/api/users/{tec.id}/", {"is_active": True}, format="json")
    tec.refresh_from_db()
    assert tec.is_active and tec.deactivated_at is None


def test_anonimiza_y_conserva_el_historial(admin, tec):
    h = Hospital.objects.create(name="H", code="HH3")
    asset = Asset.objects.create(hospital=h, name="E", code="E3", status=Asset.Status.ACTIVE)
    wo = make_work_order(asset, admin, status="COMPLETED", assigned_to=tec)
    sig = Signature.objects.create(
        work_order=wo, signature_type="TECHNICIAN", file_url="x/y.png",
        signer_name="Ana Lopez", file_hash="a" * 64,
    )
    firmar(tec)
    pc = PrivacyConsent.objects.create(user=tec, version="v1")
    log_previo = AuditLog.objects.create(
        user=tec, action="UPDATE", entity_type="WorkOrder", entity_id=wo.id,
    )
    inactivar(tec, 800)

    r = cliente(admin).post(f"/api/users/{tec.id}/anonymize/")
    assert r.status_code == 200, r.data

    tec.refresh_from_db()
    assert tec.first_name == "Usuario anonimizado"
    assert tec.last_name == f"#{str(tec.id)[:8]}"
    assert tec.email == f"anonimizado-{str(tec.id)[:8]}@anonimizado.invalid"
    assert tec.phone == "" and tec.employee_code == ""
    assert not tec.has_usable_password()
    assert not UserSignature.objects.filter(user=tec).exists()
    # Lo que la normativa sanitaria exige conservar
    wo.refresh_from_db()
    assert wo.assigned_to_id == tec.id
    assert Signature.objects.filter(pk=sig.pk, signer_name="Ana Lopez").exists()
    assert AuditLog.objects.filter(pk=log_previo.pk).exists()
    assert PrivacyConsent.objects.filter(pk=pc.pk).exists()
    # Auditoria de la anonimizacion
    log = AuditLog.objects.get(action=AuditLog.Action.ANONYMIZE)
    assert log.user == admin and log.entity_id == tec.id
    assert log.changes["firma_guardada_borrada"] is True
    assert "Ana" not in str(log.changes) and "@test.com" not in str(log.changes)


def test_no_se_anonimiza_dos_veces(admin, tec):
    inactivar(tec, 800)
    c = cliente(admin)
    assert c.post(f"/api/users/{tec.id}/anonymize/").status_code == 200
    assert c.post(f"/api/users/{tec.id}/anonymize/").status_code == 400
    assert AuditLog.objects.filter(action=AuditLog.Action.ANONYMIZE).count() == 1
