"""
Firma guardada por usuario (revision del 23-oct-2026): el tecnico, supervisor
o administrador registra su firma una vez y se aplica a sus OT como una copia.
La firma de quien recibe (CLIENT) se sigue dibujando en cada visita.
"""

import base64
import hashlib
import io

import pytest
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.evidence.models import Signature, UserSignature
from apps.evidence.tests.test_evidence import (
    auth_client,
    make_asset,
    make_hospital,
    make_user,
    make_wo,
)
from apps.users.models import User
from apps.work_orders.integrity import compute_wo_content_hash

URL = "/api/evidence/my-signature/"
SIGS_URL = "/api/evidence/signatures/"


def png_b64(color=(0, 0, 0)):
    buf = io.BytesIO()
    Image.new("RGB", (12, 12), color=color).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


@pytest.fixture(autouse=True)
def almacenamiento_temporal(settings, tmp_path):
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {"location": str(tmp_path), "base_url": "/media/"},
        },
    }


@pytest.fixture
def hospital(db):
    return make_hospital()


@pytest.fixture
def tec(db, hospital):
    return make_user(User.Role.TEC, hospital=hospital)


@pytest.fixture
def admin(db):
    return make_user(User.Role.ADMIN)


@pytest.fixture
def wo(db, hospital, admin, tec):
    return make_wo(make_asset(hospital), admin, assigned_to=tec)


def guardar(user, b64=None):
    return auth_client(user).put(URL, {"image_data": b64 or png_b64()}, format="json")


# ── Guardar, reemplazar, borrar ───────────────────────────────────────────────

def test_sin_firma_guardada_responde_vacio(tec):
    r = auth_client(tec).get(URL)
    assert r.status_code == 200
    assert r.data["exists"] is False


@pytest.mark.parametrize("role", [User.Role.TEC, User.Role.SUP, User.Role.ADMIN])
def test_usuarios_del_sistema_guardan_su_firma(db, role, hospital):
    user = make_user(role, hospital=hospital)
    b64 = png_b64()
    r = guardar(user, b64)
    assert r.status_code == status.HTTP_201_CREATED, r.data
    assert r.data["exists"] is True
    assert r.data["image_data"] == f"data:image/png;base64,{b64}"
    assert UserSignature.objects.get(user=user).file_hash == hashlib.sha256(
        base64.b64decode(b64)
    ).hexdigest()
    r = auth_client(user).get(URL)
    assert r.data["image_data"].endswith(b64)


def test_reemplazar_deja_una_sola_y_borra_el_archivo_anterior(tec):
    from django.core.files.storage import default_storage

    guardar(tec, png_b64((0, 0, 0)))
    clave_vieja = UserSignature.objects.get(user=tec).file_url
    nueva_b64 = png_b64((10, 20, 30))

    r = guardar(tec, nueva_b64)
    assert r.status_code == status.HTTP_200_OK
    assert UserSignature.objects.filter(user=tec).count() == 1
    assert auth_client(tec).get(URL).data["image_data"].endswith(nueva_b64)
    assert not default_storage.exists(clave_vieja)


def test_borrar_la_propia_firma(tec):
    from django.core.files.storage import default_storage

    guardar(tec)
    clave = UserSignature.objects.get(user=tec).file_url
    r = auth_client(tec).delete(URL)
    assert r.status_code == status.HTTP_204_NO_CONTENT
    assert not UserSignature.objects.filter(user=tec).exists()
    assert not default_storage.exists(clave)
    assert auth_client(tec).get(URL).data["exists"] is False


def test_borrar_sin_firma_es_404(tec):
    assert auth_client(tec).delete(URL).status_code == 404


def test_imagen_invalida_se_rechaza(tec):
    for malo in ["", "no-es-base64!!", base64.b64encode(b"hola").decode()]:
        r = auth_client(tec).put(URL, {"image_data": malo}, format="json")
        assert r.status_code == 400, malo
    assert not UserSignature.objects.exists()


def test_imagen_demasiado_grande_se_rechaza(tec):
    grande = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * (1024 * 1024 + 1)).decode()
    assert auth_client(tec).put(URL, {"image_data": grande}, format="json").status_code == 400


def test_exige_autenticacion(db):
    assert APIClient().get(URL).status_code == 401


# ── Cada quien la suya; la cuenta de hospital no puede ───────────────────────

def test_cada_usuario_ve_solo_la_suya(db, tec, hospital):
    otro = make_user(User.Role.TEC, hospital=hospital)
    mia, suya = png_b64((1, 1, 1)), png_b64((200, 0, 0))
    guardar(tec, mia)
    guardar(otro, suya)
    assert auth_client(tec).get(URL).data["image_data"].endswith(mia)
    assert auth_client(otro).get(URL).data["image_data"].endswith(suya)
    auth_client(tec).delete(URL)
    assert UserSignature.objects.filter(user=otro).exists()


def test_la_vista_no_acepta_un_usuario_ajeno(db, tec, hospital):
    otro = make_user(User.Role.TEC, hospital=hospital)
    r = auth_client(tec).put(
        URL, {"image_data": png_b64(), "user": str(otro.id)}, format="json"
    )
    assert r.status_code == 201
    assert UserSignature.objects.filter(user=tec).exists()
    assert not UserSignature.objects.filter(user=otro).exists()


def test_cuenta_de_hospital_no_puede_tener_firma_guardada(db, hospital):
    cli = make_user(User.Role.CLI, hospital=hospital)
    c = auth_client(cli)
    assert c.get(URL).status_code == 403
    assert c.put(URL, {"image_data": png_b64()}, format="json").status_code == 403
    assert c.delete(URL).status_code == 403
    assert not UserSignature.objects.exists()


# ── Auditoria ────────────────────────────────────────────────────────────────

def test_crear_cambiar_y_borrar_quedan_en_auditoria(tec):
    guardar(tec)
    guardar(tec, png_b64((9, 9, 9)))
    auth_client(tec).delete(URL)
    logs = list(
        AuditLog.objects.filter(entity_type="UserSignature", user=tec).order_by("timestamp")
    )
    eventos = [lg.changes["evento"] for lg in logs if "evento" in lg.changes]
    assert eventos == ["creada", "reemplazada", "borrada"]
    # La imagen nunca va a la auditoria.
    assert all("image_data" not in lg.changes for lg in logs)


# ── Aplicar a una OT ─────────────────────────────────────────────────────────

def aplicar(user, wo, **extra):
    return auth_client(user).post(
        SIGS_URL,
        {"work_order": str(wo.id), "use_saved": True, "signer_name": "Tec Uno", **extra},
        format="json",
    )


def test_aplicar_la_guardada_crea_una_copia_propia_de_la_ot(tec, wo):
    from django.core.files.storage import default_storage

    b64 = png_b64()
    guardar(tec, b64)
    r = aplicar(tec, wo)
    assert r.status_code == status.HTTP_201_CREATED, r.data
    sig = Signature.objects.get(work_order=wo)
    saved = UserSignature.objects.get(user=tec)
    assert sig.signature_type == Signature.SignatureType.TECHNICIAN
    assert sig.file_hash == saved.file_hash
    # Archivo distinto: es una copia, no una referencia.
    assert sig.file_url != saved.file_url
    assert default_storage.open(sig.file_url).read() == base64.b64decode(b64)
    logs = AuditLog.objects.filter(entity_type="Signature", entity_id=sig.id)
    assert any(lg.changes.get("firma_guardada") is True for lg in logs)


def test_cambiar_o_borrar_la_firma_no_altera_la_de_la_ot(tec, wo):
    from django.core.files.storage import default_storage

    b64 = png_b64((5, 5, 5))
    guardar(tec, b64)
    aplicar(tec, wo)
    sig = Signature.objects.get(work_order=wo)
    hash_antes, clave = sig.file_hash, sig.file_url
    acta_antes = compute_wo_content_hash(wo)

    guardar(tec, png_b64((250, 250, 0)))
    auth_client(tec).delete(URL)

    sig.refresh_from_db()
    assert (sig.file_hash, sig.file_url) == (hash_antes, clave)
    assert default_storage.open(clave).read() == base64.b64decode(b64)
    assert compute_wo_content_hash(wo) == acta_antes


def test_aplicar_sin_firma_guardada_es_400(tec, wo):
    r = aplicar(tec, wo)
    assert r.status_code == 400
    assert not Signature.objects.exists()


def test_la_firma_de_quien_recibe_no_usa_la_guardada(tec, wo):
    guardar(tec)
    r = aplicar(tec, wo, signature_type="CLIENT")
    assert r.status_code == 400
    assert not Signature.objects.filter(work_order=wo).exists()


def test_la_firma_de_quien_recibe_se_dibuja_y_no_se_guarda(tec, wo):
    r = auth_client(tec).post(
        SIGS_URL,
        {
            "work_order": str(wo.id), "signature_type": "CLIENT",
            "image_data": png_b64(), "signer_name": "Enfermera",
        },
        format="json",
    )
    assert r.status_code == 201
    assert not UserSignature.objects.exists()


def test_no_se_aplica_la_firma_de_otro_usuario(db, tec, wo, hospital):
    otro = make_user(User.Role.TEC, hospital=hospital)
    guardar(otro)
    # tec no tiene firma guardada: no puede usar la de otro.
    assert aplicar(tec, wo).status_code == 400


def test_sin_use_saved_sigue_exigiendo_la_imagen(tec, wo):
    r = auth_client(tec).post(
        SIGS_URL, {"work_order": str(wo.id), "signer_name": "X"}, format="json"
    )
    assert r.status_code == 400
