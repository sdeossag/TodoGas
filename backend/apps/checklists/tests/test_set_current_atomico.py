"""
Cambiar la version vigente de una plantilla es todo o nada.

Regresion: set-current desmarcaba la version actual con un update y despues
marcaba la nueva con un save, sin transaccion. Si el save fallaba, la plantilla
quedaba sin version vigente y no se podia crear ninguna OT con ella.
"""

from unittest import mock

import pytest
from model_bakery import baker
from rest_framework.test import APIClient

from apps.checklists.models import ChecklistTemplate, ChecklistTemplateVersion
from apps.users.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def mundo():
    admin = baker.make(User, role=User.Role.ADMIN, is_active=True)
    plantilla = baker.make(ChecklistTemplate, name="Plantilla")
    v1 = baker.make(ChecklistTemplateVersion, template=plantilla, version_number=1,
                    is_current=True, published_by=admin)
    v2 = baker.make(ChecklistTemplateVersion, template=plantilla, version_number=2,
                    is_current=False, published_by=admin)
    # raise_request_exception=False: la excepcion se vuelve un 500, como en produccion.
    c = APIClient(raise_request_exception=False)
    c.force_authenticate(user=admin)
    return {"c": c, "t": plantilla, "v1": v1, "v2": v2}


def vigentes(plantilla):
    return list(ChecklistTemplateVersion.objects.filter(template=plantilla, is_current=True))


def test_si_falla_al_marcar_la_nueva_la_anterior_sigue_vigente(mundo):
    with mock.patch.object(ChecklistTemplateVersion, "save", side_effect=RuntimeError("boom")):
        r = mundo["c"].post(f"/api/checklists/templates/{mundo['t'].id}/set-current/",
                            {"version_id": str(mundo["v2"].id)}, format="json")

    assert r.status_code == 500
    assert vigentes(mundo["t"]) == [mundo["v1"]], \
        "la plantilla quedo sin version vigente (o con la equivocada)"


def test_cambiar_la_vigente_deja_exactamente_una(mundo):
    r = mundo["c"].post(f"/api/checklists/templates/{mundo['t'].id}/set-current/",
                        {"version_id": str(mundo["v2"].id)}, format="json")
    assert r.status_code == 200
    assert vigentes(mundo["t"]) == [mundo["v2"]]


def test_marcar_como_vigente_la_que_ya_lo_es_no_la_desmarca(mundo):
    r = mundo["c"].post(f"/api/checklists/templates/{mundo['t'].id}/set-current/",
                        {"version_id": str(mundo["v1"].id)}, format="json")
    assert r.status_code == 200
    assert vigentes(mundo["t"]) == [mundo["v1"]]
