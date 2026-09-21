"""El comando verify_integrity recorre todas las OT cerradas y falla si alguna
acta no verifica. Es el control que se corre despues de migrar."""

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone
from model_bakery import baker

from apps.assets.models import Asset, Hospital
from apps.maintenance.testing import make_work_order
from apps.reports.models import GeneratedReport
from apps.users.models import User
from apps.work_orders.integrity import compute_wo_content_hash
from apps.work_orders.models import WorkOrder

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin():
    return baker.make(User, role=User.Role.ADMIN, is_active=True)


@pytest.fixture
def hospital():
    return baker.make(Hospital, is_active=True, code="H-VER")


def cerrada(hospital, admin, **extra):
    activo = baker.make(Asset, hospital=hospital, status=Asset.Status.ACTIVE)
    return make_work_order(
        activo, admin, status=WorkOrder.Status.COMPLETED,
        completed_at=timezone.now(), **extra,
    )


def acta(ot, version="2", content_hash=None):
    return GeneratedReport.objects.create(
        work_order=ot, report_type=GeneratedReport.ReportType.WORK_ORDER,
        title="Acta", file_url="acta.pdf", file_hash="f" * 64,
        content_hash=(
            compute_wo_content_hash(ot, version) if content_hash is None else content_hash
        ),
        integrity_version=version,
    )


def correr(*args):
    salida = StringIO()
    call_command("verify_integrity", *args, stdout=salida)
    return salida.getvalue()


def test_todas_verifican(hospital, admin):
    acta(cerrada(hospital, admin), "1")
    acta(cerrada(hospital, admin), "2")
    cerrada(hospital, admin)  # sin acta: se informa, no es falla

    salida = correr()

    assert "OT cerradas revisadas: 3" in salida
    assert "Verifican: 2  (v1: 1, v2: 1)" in salida
    assert "Sin acta generada: 1" in salida
    assert "Todas las actas con hash verifican." in salida


def test_falla_si_un_acta_fue_alterada(hospital, admin):
    buena = cerrada(hospital, admin)
    acta(buena)
    alterada = cerrada(hospital, admin)
    acta(alterada)
    WorkOrder.objects.filter(pk=alterada.pk).update(notes="cambiado despues de firmar")
    salida = StringIO()

    with pytest.raises(CommandError, match="1 acta"):
        call_command("verify_integrity", stdout=salida)

    assert alterada.wo_code in salida.getvalue()
    assert buena.wo_code not in salida.getvalue()


def test_version_desconocida_es_falla(hospital, admin):
    ot = cerrada(hospital, admin)
    acta(ot, version="9", content_hash="0" * 64)

    with pytest.raises(CommandError):
        correr()


def test_acta_sin_hash_se_informa_sin_fallar(hospital, admin):
    acta(cerrada(hospital, admin), version="", content_hash="")

    salida = correr()

    assert "Sin hash (acta anterior al hash de contenido): 1" in salida


def test_filtra_por_hospital(hospital, admin):
    acta(cerrada(hospital, admin))
    otro = baker.make(Hospital, is_active=True, code="H-OTRO")
    alterada = cerrada(otro, admin)
    acta(alterada, content_hash="0" * 64)

    salida = correr("--hospital", "H-VER", "--detalle")

    assert "OT cerradas revisadas: 1" in salida
    assert alterada.wo_code not in salida
