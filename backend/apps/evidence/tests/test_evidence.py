import base64
import hashlib
import io
import uuid
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.users.models import User
from apps.work_orders.models import WorkOrder
from apps.evidence.models import Photo, Signature

FAKE_S3_KEY = "evidence/photos/test/fake.jpg"
FAKE_S3_URL = "https://s3.amazonaws.com/todogas-media-dev/evidence/photos/test/fake.jpg?Signature=xxx"
FAKE_SIG_KEY = "evidence/signatures/test/TECHNICIAN_fake.png"
FAKE_SIG_URL = "https://s3.amazonaws.com/todogas-media-dev/evidence/signatures/test/TECHNICIAN_fake.png?Signature=yyy"


# ── Helpers ────────────────────────────────────────────────────────────────────

def auth_client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def make_user(role, hospital=None):
    return User.objects.create_user(
        email=f"{uuid.uuid4()}@test.com",
        password="pass",
        first_name="A",
        last_name="B",
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


def make_wo(asset, created_by, assigned_to=None, wo_status=WorkOrder.Status.IN_PROGRESS):
    wo = WorkOrder(
        asset=asset,
        task_type=WorkOrder.TaskType.CORRECTIVE,
        title="OT test",
        status=wo_status,
        priority=WorkOrder.Priority.MEDIUM,
        scheduled_date=date.today(),
        assigned_to=assigned_to,
        created_by=created_by,
    )
    wo.save()
    return wo


def make_image_bytes(width=10, height=10, fmt="JPEG"):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=(200, 100, 50)).save(buf, format=fmt)
    return buf.getvalue()


def make_png_b64():
    return base64.b64encode(make_image_bytes(fmt="PNG")).decode()


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def hospital(db):
    return make_hospital()


@pytest.fixture
def admin(db):
    return make_user(User.Role.ADMIN)


@pytest.fixture
def tec(db, hospital):
    return make_user(User.Role.TEC, hospital=hospital)


@pytest.fixture
def tec2(db, hospital):
    return make_user(User.Role.TEC, hospital=hospital)


@pytest.fixture
def asset(db, hospital):
    return make_asset(hospital)


@pytest.fixture
def wo_in_progress(db, asset, admin, tec):
    return make_wo(asset, admin, assigned_to=tec, wo_status=WorkOrder.Status.IN_PROGRESS)


@pytest.fixture
def wo_pending(db, asset, admin, tec):
    return make_wo(asset, admin, assigned_to=tec, wo_status=WorkOrder.Status.PENDING)


# ── Photo tests ───────────────────────────────────────────────────────────────

PHOTOS_URL = "/api/evidence/photos/"

@patch("apps.evidence.serializers.default_storage")
def test_upload_photo_calculates_correct_sha256(mock_storage, db, tec, wo_in_progress):
    """SHA-256 almacenado en file_hash debe coincidir con el del archivo subido."""
    mock_storage.save.return_value = FAKE_S3_KEY
    mock_storage.url.return_value = FAKE_S3_URL

    img_bytes = make_image_bytes()
    expected_hash = hashlib.sha256(img_bytes).hexdigest()

    img_file = io.BytesIO(img_bytes)
    img_file.name = "photo.jpg"

    client = auth_client(tec)
    resp = client.post(
        PHOTOS_URL,
        {
            "work_order": str(wo_in_progress.id),
            "file": img_file,
            "taken_at": "2026-08-19T10:00:00Z",
        },
        format="multipart",
    )

    assert resp.status_code == status.HTTP_201_CREATED, resp.data
    photo = Photo.objects.get(id=resp.data["id"])
    assert photo.file_hash == expected_hash


@patch("apps.evidence.serializers.default_storage")
def test_upload_photo_rejects_file_over_10mb(mock_storage, db, tec, wo_in_progress):
    """Archivos mayores a 10 MB deben ser rechazados con 400."""
    mock_storage.save.return_value = FAKE_S3_KEY
    mock_storage.url.return_value = FAKE_S3_URL

    large_file = io.BytesIO(b"x" * (10 * 1024 * 1024 + 1))
    large_file.name = "big.jpg"

    client = auth_client(tec)
    resp = client.post(
        PHOTOS_URL,
        {
            "work_order": str(wo_in_progress.id),
            "file": large_file,
            "taken_at": "2026-08-19T10:00:00Z",
        },
        format="multipart",
    )

    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_tec_cannot_upload_to_another_tec_wo(db, tec2, wo_in_progress):
    """TEC no asignado recibe 403 al intentar subir foto."""
    client = auth_client(tec2)
    img_file = io.BytesIO(make_image_bytes())
    img_file.name = "photo.jpg"

    resp = client.post(
        PHOTOS_URL,
        {
            "work_order": str(wo_in_progress.id),
            "file": img_file,
            "taken_at": "2026-08-19T10:00:00Z",
        },
        format="multipart",
    )

    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_cannot_upload_photo_to_pending_wo(db, tec, wo_pending):
    """OT en estado distinto de IN_PROGRESS rechaza subida de fotos con 400."""
    client = auth_client(tec)
    img_file = io.BytesIO(make_image_bytes())
    img_file.name = "photo.jpg"

    resp = client.post(
        PHOTOS_URL,
        {
            "work_order": str(wo_pending.id),
            "file": img_file,
            "taken_at": "2026-08-19T10:00:00Z",
        },
        format="multipart",
    )

    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@patch("apps.evidence.serializers.default_storage")
def test_list_photos_filters_by_work_order(mock_storage, db, admin, tec, asset, hospital):
    """GET /api/evidence/photos/?work_order=X solo devuelve fotos de esa OT."""
    mock_storage.save.return_value = FAKE_S3_KEY
    mock_storage.url.return_value = FAKE_S3_URL

    wo_a = make_wo(asset, admin, assigned_to=tec)
    wo_b = make_wo(asset, admin, assigned_to=tec)

    Photo.objects.create(
        work_order=wo_a, file_url="a.jpg", taken_at="2026-08-19T10:00:00Z",
        file_hash="h1", uploaded_by=tec,
    )
    Photo.objects.create(
        work_order=wo_b, file_url="b.jpg", taken_at="2026-08-19T11:00:00Z",
        file_hash="h2", uploaded_by=tec,
    )

    client = auth_client(admin)
    resp = client.get(PHOTOS_URL, {"work_order": str(wo_a.id)})

    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.data) == 1
    assert str(resp.data[0]["work_order"]) == str(wo_a.id)


# ── Signature tests ───────────────────────────────────────────────────────────

SIGS_URL = "/api/evidence/signatures/"

@patch("apps.evidence.serializers.default_storage")
def test_create_signature_technician(mock_storage, db, tec, wo_in_progress):
    """Crear firma TECHNICIAN exitosamente devuelve 201 con hash correcto."""
    mock_storage.save.return_value = FAKE_SIG_KEY
    mock_storage.url.return_value = FAKE_SIG_URL

    b64 = make_png_b64()
    img_bytes = base64.b64decode(b64)
    expected_hash = hashlib.sha256(img_bytes).hexdigest()

    client = auth_client(tec)
    resp = client.post(
        SIGS_URL,
        {
            "work_order": str(wo_in_progress.id),
            "image_data": b64,
            "signer_name": "Juan Perez",
            "signer_role": "Tecnico",
        },
        format="json",
    )

    assert resp.status_code == status.HTTP_201_CREATED, resp.data
    sig = Signature.objects.get(id=resp.data["id"])
    assert sig.file_hash == expected_hash
    assert sig.signer_name == "Juan Perez"
    assert sig.signature_type == Signature.SignatureType.TECHNICIAN


@patch("apps.evidence.serializers.default_storage")
def test_duplicate_signature_type_rejected(mock_storage, db, tec, wo_in_progress):
    """No se puede crear segunda firma del mismo tipo en la misma OT."""
    mock_storage.save.return_value = FAKE_SIG_KEY
    mock_storage.url.return_value = FAKE_SIG_URL

    b64 = make_png_b64()
    client = auth_client(tec)
    payload = {
        "work_order": str(wo_in_progress.id),
        "image_data": b64,
        "signer_name": "Juan Perez",
    }

    r1 = client.post(SIGS_URL, payload, format="json")
    assert r1.status_code == status.HTTP_201_CREATED

    r2 = client.post(SIGS_URL, payload, format="json")
    assert r2.status_code == status.HTTP_400_BAD_REQUEST


def test_invalid_base64_rejected(db, tec, wo_in_progress):
    """image_data con base64 invalido devuelve 400."""
    client = auth_client(tec)
    resp = client.post(
        SIGS_URL,
        {
            "work_order": str(wo_in_progress.id),
            "image_data": "esto_no_es_base64!!!",
            "signer_name": "Test",
        },
        format="json",
    )

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
