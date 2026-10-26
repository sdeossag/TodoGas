"""La direccion de la sububicacion en el acta, y el mapa con su punto."""

from unittest.mock import patch

import pytest
from django.utils import timezone
from model_bakery import baker

from apps.assets.models import Asset, AssetNode, Hospital
from apps.maintenance.testing import make_work_order
from apps.reports.models import ReportSettings
from apps.reports.tests.test_acta_configurable import acta_html, admin  # noqa: F401
from apps.work_orders.models import WorkOrder

pytestmark = pytest.mark.django_db


@pytest.fixture
def ot(admin):  # noqa: F811
    h = baker.make(Hospital, name="Clinica Demo Norte", is_active=True)
    bloque = AssetNode.objects.create(hospital=h, name="Bloque A", address="Calle 10 #20-30, Medellin",
                                      latitude="6.2442000", longitude="-75.5812000")
    piso = AssetNode.objects.create(hospital=h, parent=bloque, name="Piso 1")
    a = baker.make(Asset, hospital=h, node=piso, status=Asset.Status.ACTIVE, code="TOM-1")
    return make_work_order(a, admin, assigned_to=admin, status=WorkOrder.Status.COMPLETED,
                           completed_at=timezone.now())


def test_el_acta_trae_la_direccion_de_la_sububicacion(ot):
    html, _ = acta_html(ot)
    assert "Calle 10 #20-30, Medellin" in html


def test_la_direccion_va_con_el_interruptor_de_ubicacion_del_activo(ot):
    ReportSettings.objects.create(options={"activo_ubicacion": False})
    html, _ = acta_html(ot)
    assert "Calle 10 #20-30, Medellin" not in html


def test_mapa_de_la_sububicacion_cuando_no_hay_gps_del_tecnico(ot):
    with patch("apps.assets.geo.static_map_data_uri", return_value="data:image/png;base64,AAA") as mapa:
        html, _ = acta_html(ot)
    mapa.assert_called()
    assert mapa.call_args.args[:2] == (pytest.approx(6.2442), pytest.approx(-75.5812))
    assert "data:image/png;base64,AAA" in html


def test_sin_interruptor_de_mapa_no_hay_mapa_de_la_sububicacion(ot):
    ReportSettings.objects.create(options={"checklist_mapa": False})
    with patch("apps.assets.geo.static_map_data_uri", return_value="data:image/png;base64,AAA") as mapa:
        html, _ = acta_html(ot)
    mapa.assert_not_called()
    assert "data:image/png;base64,AAA" not in html
