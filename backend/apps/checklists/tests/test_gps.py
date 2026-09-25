"""
Localizacion GPS con Google Maps (decision del 2026-09-24), como el campo
*LOCALIZACION de Fracttal: al sincronizar, el servidor convierte las
coordenadas en direccion y el acta imprime la direccion con un mapa pequeno.
Sin clave o sin Google, todo sigue con las coordenadas.
"""

from types import SimpleNamespace
from unittest import mock

import pytest
from model_bakery import baker
from rest_framework.test import APIClient

from apps.assets import geo
from apps.assets.models import Asset, Hospital
from apps.checklists.models import (
    ChecklistField,
    ChecklistFieldResponse,
    ChecklistTemplate,
    ChecklistTemplateVersion,
)
from apps.maintenance import services
from apps.maintenance.models import MaintenancePlan, PlanTask, Task
from apps.reports.generator import _mapa, _valor
from apps.users.models import User
from apps.work_orders.models import WorkOrder

pytestmark = pytest.mark.django_db
DIRECCION = "Cra. 4h Bis #341, Ibagué, Tolima, Colombia"


@pytest.fixture
def d():
    admin = baker.make(User, role=User.Role.ADMIN, is_active=True)
    tec = baker.make(User, role=User.Role.TEC, is_active=True)
    h = baker.make(Hospital, is_active=True)
    activo = Asset.objects.create(hospital=h, name="Toma", code="TOMA-GPS")
    t = ChecklistTemplate.objects.create(name="Salidas")
    v = ChecklistTemplateVersion.objects.create(template=t, version_number=1, published_by=admin, is_current=True)
    campo = ChecklistField.objects.create(version=v, label="Localización", field_type="GPS", sort_order=1)
    plan = MaintenancePlan.objects.create(name="SALIDAS 3 TOMAS")
    PlanTask.objects.create(plan=plan, name="Salidas", checklist_template=t, frequency_value=6, frequency_unit="MONTHS")
    services.set_asset_plan(activo, plan)
    tarea = Task.objects.get(plan_task__plan=plan, asset=activo)
    ot, _ = services.create_work_order_for_tasks([tarea], admin)
    ot.assigned_to = tec
    ot.status = WorkOrder.Status.IN_PROGRESS
    ot.save()
    c = APIClient()
    c.force_authenticate(user=tec)
    return {"c": c, "campo": campo, "url": f"/api/checklists/responses/{tarea.checklist_response.id}/submit-field/"}


def test_parse_latlng():
    assert geo.parse_latlng("4.437887,-75.220034") == (4.437887, -75.220034)
    assert geo.parse_latlng(" 4.4 , -75.2 ") == (4.4, -75.2)
    for malo in ("", "hola", "4.4", "91,0", "0,181"):
        assert geo.parse_latlng(malo) is None


def test_al_sincronizar_se_calcula_la_direccion(d, django_capture_on_commit_callbacks):
    with mock.patch("apps.assets.geo.reverse_geocode", return_value=DIRECCION) as pedir:
        with django_capture_on_commit_callbacks(execute=True):
            r = d["c"].post(d["url"], {"field": str(d["campo"].id), "value": "4.437887,-75.220034"}, format="json")
        assert r.status_code == 200, r.data
        pedir.assert_called_once_with(4.437887, -75.220034)
        fr = ChecklistFieldResponse.objects.get()
        assert fr.geo_address == DIRECCION

        with django_capture_on_commit_callbacks(execute=True):
            d["c"].post(d["url"], {"field": str(d["campo"].id), "value": "4.437887,-75.220034"}, format="json")
        assert pedir.call_count == 1, "la misma posicion no se vuelve a pedir"

    with mock.patch("apps.assets.geo.reverse_geocode", return_value="Otra dirección") as pedir:
        with django_capture_on_commit_callbacks(execute=True):
            d["c"].post(d["url"], {"field": str(d["campo"].id), "value": "4.5,-75.3"}, format="json")
        assert ChecklistFieldResponse.objects.get().geo_address == "Otra dirección"


def test_la_respuesta_trae_la_direccion(d, django_capture_on_commit_callbacks):
    with mock.patch("apps.assets.geo.reverse_geocode", return_value=DIRECCION):
        with django_capture_on_commit_callbacks(execute=True):
            d["c"].post(d["url"], {"field": str(d["campo"].id), "value": "4.4,-75.2"}, format="json")
    r = d["c"].post(d["url"], {"field": str(d["campo"].id), "value": "4.4,-75.2"}, format="json")
    assert r.data["geo_address"] == DIRECCION


def test_sin_clave_no_se_llama_a_google(settings):
    settings.GOOGLE_MAPS_API_KEY = ""
    with mock.patch("urllib.request.urlopen") as abrir:
        assert geo.reverse_geocode(4.4, -75.2) == ""
        assert geo.static_map_data_uri(4.4, -75.2) == ""
    abrir.assert_not_called()


def test_google_caido_no_rompe_nada(settings):
    settings.GOOGLE_MAPS_API_KEY = "clave-de-prueba"
    import urllib.error

    with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("sin red")):
        assert geo.reverse_geocode(4.4, -75.2) == ""
        assert geo.static_map_data_uri(4.4, -75.2) == ""


def test_una_imagen_de_error_no_va_al_acta(settings):
    settings.GOOGLE_MAPS_API_KEY = "clave-de-prueba"
    with mock.patch("apps.assets.geo._get", return_value=b"<html>error</html>"):
        assert geo.static_map_data_uri(4.4, -75.2) == ""
    with mock.patch("apps.assets.geo._get", return_value=b"\x89PNG\r\n\x1a\nxx"):
        assert geo.static_map_data_uri(4.4, -75.2).startswith("data:image/png;base64,")


def test_el_acta_imprime_la_direccion_y_respeta_el_interruptor():
    campo = ChecklistField(field_type="GPS", label="Localización")
    fr = SimpleNamespace(field=campo, value="4.4,-75.2", geo_address=DIRECCION)
    assert _valor(fr) == f"{DIRECCION} (4.4,-75.2)"
    assert _valor(fr, corto=True) == DIRECCION
    sin = SimpleNamespace(field=campo, value="4.4,-75.2", geo_address="")
    assert _valor(sin) == "4.4,-75.2", "sin direccion, las coordenadas"

    with mock.patch("apps.assets.geo.static_map_data_uri", return_value="data:image/png;base64,AAA") as mapa:
        assert _mapa(fr, {"checklist_mapa": True}) == "data:image/png;base64,AAA"
        assert _mapa(fr, {"checklist_mapa": False}) == ""
        mapa.assert_called_once_with(4.4, -75.2)
