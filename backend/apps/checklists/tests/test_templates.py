import pytest
from model_bakery import baker
from rest_framework.test import APIClient

from apps.checklists.models import ChecklistField, ChecklistTemplate, ChecklistTemplateVersion
from apps.users.models import User


@pytest.fixture
def admin(db):
    return User.objects.create_user(email="admin@cl.test", password="pass", role="ADMIN", is_active=True)


@pytest.fixture
def tec(db):
    return User.objects.create_user(email="tec@cl.test", password="pass", role="TEC", is_active=True)


@pytest.fixture
def client_admin(admin):
    c = APIClient()
    c.force_authenticate(user=admin)
    return c


@pytest.fixture
def client_tec(tec):
    c = APIClient()
    c.force_authenticate(user=tec)
    return c


@pytest.fixture
def template(db):
    return baker.make(ChecklistTemplate, name="Plantilla Gas", is_active=True)


@pytest.fixture
def version(template, admin):
    v = baker.make(
        ChecklistTemplateVersion,
        template=template,
        version_number=1,
        is_current=True,
        published_by=admin,
    )
    baker.make(ChecklistField, version=v, label="Temperatura (°C)", field_type="NUMBER", sort_order=0)
    baker.make(ChecklistField, version=v, label="Observaciones", field_type="TEXTAREA", sort_order=1)
    return v


@pytest.mark.django_db
def test_list_templates_authenticated(client_tec, template):
    baker.make(ChecklistTemplate, name="Otra Plantilla")
    resp = client_tec.get("/api/checklists/templates/")
    assert resp.status_code == 200
    assert resp.data["count"] >= 2


@pytest.mark.django_db
def test_create_template_as_admin(client_admin):
    resp = client_admin.post(
        "/api/checklists/templates/",
        {"name": "Nueva Plantilla", "description": "Desc de prueba"},
    )
    assert resp.status_code == 201
    assert resp.data["name"] == "Nueva Plantilla"


@pytest.mark.django_db
def test_create_template_as_tec_forbidden(client_tec):
    resp = client_tec.post("/api/checklists/templates/", {"name": "No Permitido"})
    assert resp.status_code == 403


@pytest.mark.django_db
def test_publish_version_creates_fields(client_admin, template):
    payload = {
        "checklist_fields": [
            {"label": "Presión (bar)", "field_type": "NUMBER", "is_required": True, "sort_order": 0},
            {"label": "Firma técnico", "field_type": "SIGNATURE", "is_required": True, "sort_order": 1},
        ]
    }
    resp = client_admin.post(
        f"/api/checklists/templates/{template.id}/publish-version/",
        payload,
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["version_number"] == 1
    assert len(resp.data["checklist_fields"]) == 2


@pytest.mark.django_db
def test_set_current_version(client_admin, template, version, admin):
    v2 = baker.make(
        ChecklistTemplateVersion,
        template=template,
        version_number=2,
        is_current=False,
        published_by=admin,
    )
    resp = client_admin.post(
        f"/api/checklists/templates/{template.id}/set-current/",
        {"version_id": str(v2.id)},
    )
    assert resp.status_code == 200
    v2.refresh_from_db()
    version.refresh_from_db()
    assert v2.is_current is True
    assert version.is_current is False


@pytest.mark.django_db
def test_list_includes_current_version_info(client_admin, template, version):
    resp = client_admin.get("/api/checklists/templates/")
    assert resp.status_code == 200
    t_data = next(
        t for t in resp.data["results"] if str(t["id"]) == str(template.id)
    )
    assert t_data["current_version_number"] == 1
    assert t_data["fields_count"] == 2
