import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from model_bakery import baker

from apps.assets.models import AssetNode, Hospital

pytestmark = pytest.mark.django_db


def test_se_niega_fuera_de_una_base_demo():
    if "demo" in str(connection.settings_dict["NAME"]).lower():
        pytest.skip("esta prueba corre contra una base que no es demo")
    with pytest.raises(CommandError, match="demo"):
        call_command("completar_ubicaciones_demo")


def _base():
    h = baker.make(Hospital, name="Clinica Demo Norte", code="DEMO-NORTE", is_active=True,
                   address="Cra 15 # 100-12", latitude="4.6780000", longitude="-74.0480000")
    bloque = AssetNode.objects.create(hospital=h, name="Bloque A", code="N-BA",
                                      address=h.address, latitude=h.latitude, longitude=h.longitude)
    p1 = AssetNode.objects.create(hospital=h, parent=bloque, name="Piso 1 - Urgencias", code="N-P1")
    p3 = AssetNode.objects.create(hospital=h, parent=bloque, name="Piso 3", code="N-P3")
    return h, bloque, p1, p3


def test_rellena_los_nodos_vacios_sin_pisar_lo_que_ya_hay_y_es_idempotente():
    h, bloque, p1, p3 = _base()
    AssetNode.objects.filter(pk=p3.pk).update(address="Mi calle", latitude="1.0000000", longitude="2.0000000")
    call_command("completar_ubicaciones_demo", marcador="")  # "" siempre esta en el nombre
    p1.refresh_from_db()
    p3.refresh_from_db()
    bloque.refresh_from_db()
    assert p1.address and p1.latitude is not None
    assert p3.address == "Mi calle"
    # El seed viejo copiaba al bloque la direccion y el punto del hospital: eso
    # no es una ubicacion propia, y se reemplaza por la del bloque.
    assert bloque.address != h.address and "Bloque A" in bloque.address
    assert bloque.latitude != h.latitude
    primero = (p1.address, p1.latitude, p1.longitude)
    call_command("completar_ubicaciones_demo", marcador="")
    p1.refresh_from_db()
    assert (p1.address, p1.latitude, p1.longitude) == primero


def test_no_toca_hospitales_de_fuera_de_la_demo():
    h = baker.make(Hospital, name="Real", code="REAL-1", is_active=True)
    n = AssetNode.objects.create(hospital=h, name="Bloque A", code="N-BA")
    call_command("completar_ubicaciones_demo", marcador="")
    n.refresh_from_db()
    assert n.address == "" and n.latitude is None
