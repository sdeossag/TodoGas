"""
Los 400 de "checklist ya completado" llevan un codigo estable.

El frontend comparaba el texto en español con una regex; si alguien corrige una
tilde, se rompe. Ahora la respuesta trae ademas `"code": "checklist_completed"`
y el mensaje legible sigue en `detail`.
"""

import pytest
from django.utils import timezone
from model_bakery import baker
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.checklists.models import (
    ChecklistField,
    ChecklistResponse,
    ChecklistTemplate,
    ChecklistTemplateVersion,
)
from apps.maintenance.testing import make_work_order
from apps.users.models import User

pytestmark = pytest.mark.django_db
MENSAJE = "El checklist ya está completado."


@pytest.fixture
def cerrado():
    admin = baker.make(User, role=User.Role.ADMIN, is_active=True)
    tec = baker.make(User, role=User.Role.TEC, is_active=True)
    hospital = baker.make(Hospital)
    asset = baker.make(Asset, hospital=hospital, status="ACTIVE")
    plantilla = baker.make(ChecklistTemplate, name="T")
    version = baker.make(ChecklistTemplateVersion, template=plantilla, version_number=1,
                         is_current=True, published_by=admin)
    campo = baker.make(ChecklistField, version=version, label="X", field_type="TEXT",
                       is_required=False, group="", sort_order=0)
    ot = make_work_order(asset, admin, assigned_to=tec, status="IN_PROGRESS",
                         checklist_version=version, scheduled_date="2026-12-31")
    respuesta = ChecklistResponse.objects.create(
        task=ot.tasks.first(), version=version, completed_by=tec,
        completed_at=timezone.now(),
    )
    c = APIClient()
    c.force_authenticate(user=tec)
    return {"c": c, "r": respuesta, "campo": campo}


def verificar(r):
    assert r.status_code == 400, r.data
    assert r.data["code"] == "checklist_completed"
    assert r.data["detail"] == MENSAJE


def test_submit_field_sobre_un_checklist_completado_ya_se_corrige(cerrado):
    """Revision del 2026-10-23: con la OT en curso se corrige aunque este cerrado."""
    r = cerrado["c"].post(
        f"/api/checklists/responses/{cerrado['r'].id}/submit-field/",
        {"field": str(cerrado["campo"].id), "value": "hola"}, format="json")
    assert r.status_code == 200, r.data
    cerrado["r"].refresh_from_db()
    assert cerrado["r"].completed_at is None


def test_complete_sobre_un_checklist_completado_trae_el_codigo(cerrado):
    r = cerrado["c"].post(
        f"/api/checklists/responses/{cerrado['r'].id}/complete/", {}, format="json")
    verificar(r)


def test_otros_400_del_checklist_no_llevan_ese_codigo(cerrado):
    """El codigo es especifico: un checklist abierto con un dato malo no lo trae."""
    abierto = cerrado["r"]
    ChecklistResponse.objects.filter(pk=abierto.pk).update(completed_at=None)
    r = cerrado["c"].post(
        f"/api/checklists/responses/{abierto.id}/block-count/",
        {"group": "no-existe", "count": 2}, format="json")
    assert r.status_code == 400
    assert r.data.get("code") != "checklist_completed"
