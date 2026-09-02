import pytest
from django.utils import timezone
from model_bakery import baker
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.checklists.models import ChecklistField, ChecklistResponse, ChecklistTemplate, ChecklistTemplateVersion
from apps.users.models import User
from apps.work_orders.models import WorkOrder


@pytest.fixture
def admin(db):
    return User.objects.create_user(email="admin@cr.test", password="pass", role="ADMIN", is_active=True)


@pytest.fixture
def tec(db):
    return User.objects.create_user(email="tec@cr.test", password="pass", role="TEC", is_active=True)


@pytest.fixture
def tec2(db):
    return User.objects.create_user(email="tec2@cr.test", password="pass", role="TEC", is_active=True)


@pytest.fixture
def hospital(db):
    return baker.make(Hospital)


@pytest.fixture
def asset(hospital):
    return baker.make(Asset, hospital=hospital, status="ACTIVE")


@pytest.fixture
def template(db):
    return baker.make(ChecklistTemplate, name="OT Template")


@pytest.fixture
def version(template, admin):
    v = baker.make(
        ChecklistTemplateVersion,
        template=template,
        version_number=1,
        is_current=True,
        published_by=admin,
    )
    baker.make(ChecklistField, version=v, label="Temperatura (°C)", field_type="NUMBER", is_required=True, sort_order=0)
    baker.make(ChecklistField, version=v, label="Observaciones", field_type="TEXTAREA", is_required=False, sort_order=1)
    return v


@pytest.fixture
def work_order(asset, admin, tec, version):
    wo = WorkOrder(
        asset=asset,
        task_type="CORRECTIVE",
        title="OT de Prueba",
        priority="MEDIUM",
        scheduled_date="2026-12-31",
        created_by=admin,
        assigned_to=tec,
        status="IN_PROGRESS",
        checklist_version=version,
    )
    wo.save()
    return wo


@pytest.fixture
def client_tec(tec):
    c = APIClient()
    c.force_authenticate(user=tec)
    return c


@pytest.fixture
def client_admin(admin):
    c = APIClient()
    c.force_authenticate(user=admin)
    return c


@pytest.mark.django_db
def test_tec_can_create_checklist_response(client_tec, work_order, version):
    resp = client_tec.post(
        "/api/checklists/responses/",
        {"work_order": str(work_order.id), "version": str(version.id)},
    )
    assert resp.status_code == 201
    assert str(resp.data["work_order"]) == str(work_order.id)


@pytest.mark.django_db
def test_duplicate_response_rejected(client_tec, work_order, version, tec):
    ChecklistResponse.objects.create(work_order=work_order, version=version, completed_by=tec)
    resp = client_tec.post(
        "/api/checklists/responses/",
        {"work_order": str(work_order.id), "version": str(version.id)},
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_tec_cannot_see_other_tec_response(client_tec, work_order, tec2, version, admin, asset):
    wo2 = WorkOrder(
        asset=asset,
        task_type="CORRECTIVE",
        title="OT Técnico 2",
        priority="MEDIUM",
        scheduled_date="2026-12-31",
        created_by=admin,
        assigned_to=tec2,
        status="IN_PROGRESS",
        checklist_version=version,
    )
    wo2.save()
    ChecklistResponse.objects.create(work_order=wo2, version=version, completed_by=tec2)
    resp = client_tec.get("/api/checklists/responses/")
    assert resp.status_code == 200
    assert resp.data["count"] == 0


@pytest.mark.django_db
def test_submit_field_response(client_tec, work_order, version, tec):
    cr = ChecklistResponse.objects.create(work_order=work_order, version=version, completed_by=tec)
    field = version.fields.order_by("sort_order").first()
    resp = client_tec.post(
        f"/api/checklists/responses/{cr.id}/submit-field/",
        {"field": str(field.id), "value": "36.5"},
    )
    assert resp.status_code == 200
    assert resp.data["value"] == "36.5"
    assert resp.data["out_of_range"] is False


@pytest.mark.django_db
def test_submit_field_wrong_version_rejected(client_tec, work_order, version, tec, admin):
    cr = ChecklistResponse.objects.create(work_order=work_order, version=version, completed_by=tec)
    other_template = baker.make(ChecklistTemplate, name="Otra Plantilla")
    other_version = baker.make(
        ChecklistTemplateVersion,
        template=other_template,
        version_number=1,
        is_current=True,
        published_by=admin,
    )
    wrong_field = baker.make(ChecklistField, version=other_version, label="Campo Erróneo", field_type="TEXT")
    resp = client_tec.post(
        f"/api/checklists/responses/{cr.id}/submit-field/",
        {"field": str(wrong_field.id), "value": "test"},
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_complete_requires_required_fields(client_tec, work_order, version, tec):
    cr = ChecklistResponse.objects.create(work_order=work_order, version=version, completed_by=tec)
    resp = client_tec.post(f"/api/checklists/responses/{cr.id}/complete/")
    assert resp.status_code == 400
    assert "Temperatura" in resp.data["detail"]


@pytest.mark.django_db
def test_complete_marks_completed_at(client_tec, work_order, version, tec):
    cr = ChecklistResponse.objects.create(work_order=work_order, version=version, completed_by=tec)
    required_field = version.fields.filter(is_required=True).first()
    cr.field_responses.create(field=required_field, value="37.0")
    resp = client_tec.post(f"/api/checklists/responses/{cr.id}/complete/")
    assert resp.status_code == 200
    cr.refresh_from_db()
    assert cr.completed_at is not None


@pytest.mark.django_db
def test_cannot_submit_field_after_complete(client_tec, work_order, version, tec):
    cr = ChecklistResponse.objects.create(
        work_order=work_order,
        version=version,
        completed_by=tec,
        completed_at=timezone.now(),
    )
    field = version.fields.first()
    resp = client_tec.post(
        f"/api/checklists/responses/{cr.id}/submit-field/",
        {"field": str(field.id), "value": "100"},
    )
    assert resp.status_code == 400
