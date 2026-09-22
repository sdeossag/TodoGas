"""Una tarea del plan no debe quedar atada a una plantilla sin version publicada.

Regresion: el formulario de planes ofrecia todas las plantillas y el serializer
las aceptaba. El motor ata la OT a la version (is_current), asi que con una
plantilla sin publicar dejaba checklist_version en None y generaba ordenes
preventivas sin nada que diligenciar, en silencio.
"""

from datetime import date, timedelta

import pytest
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.checklists.models import ChecklistTemplate, ChecklistTemplateVersion
from apps.maintenance.engine import generate_work_orders_for_plan
from apps.maintenance.models import MaintenancePlan
from apps.users.models import User
from apps.work_orders.models import WorkOrder
from apps.maintenance.testing import make_plan as _make_plan


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def admin_user(db):
    return baker.make(User, role=User.Role.ADMIN, is_active=True)


@pytest.fixture
def hospital(db):
    return baker.make(Hospital, is_active=True)


@pytest.fixture
def asset(db, hospital):
    return baker.make(Asset, hospital=hospital, status=Asset.Status.ACTIVE)


@pytest.fixture
def unpublished_template(db):
    """Plantilla creada pero nunca publicada: sin ninguna version."""
    return baker.make(ChecklistTemplate, name='Sin publicar', is_active=True)


@pytest.fixture
def published_template(db, admin_user):
    template = baker.make(ChecklistTemplate, name='Publicada', is_active=True)
    baker.make(
        ChecklistTemplateVersion,
        template=template,
        version_number=1,
        is_current=True,
        published_by=admin_user,
    )
    return template


@pytest.fixture
def plan(db):
    return MaintenancePlan.objects.create(name='Plan de prueba')


def task_payload(plan, **extra):
    payload = {
        'plan': str(plan.id),
        'name': 'Preventivo semestral',
        'task_type': MaintenancePlan.TaskType.PREVENTIVE,
        'frequency_value': 6,
        'frequency_unit': MaintenancePlan.FrequencyUnit.MONTHS,
    }
    payload.update(extra)
    return payload


# ── Validacion en el serializer (tarea del plan) ─────────────────────────────

def test_create_task_rejects_template_without_published_version(
    plan, admin_user, unpublished_template
):
    client = auth_client(admin_user)
    resp = client.post(
        '/api/maintenance/plan-tasks/',
        task_payload(plan, checklist_template=str(unpublished_template.id)),
        format='json',
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert 'checklist_template' in resp.json()


def test_create_task_accepts_template_with_published_version(
    plan, admin_user, published_template
):
    client = auth_client(admin_user)
    resp = client.post(
        '/api/maintenance/plan-tasks/',
        task_payload(plan, checklist_template=str(published_template.id)),
        format='json',
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert plan.tasks.get().checklist_template_id == published_template.id


def test_create_task_still_accepts_no_checklist(plan, admin_user):
    """«Sin checklist» sigue siendo una opcion valida: la validacion no la rompe."""
    client = auth_client(admin_user)
    resp = client.post('/api/maintenance/plan-tasks/', task_payload(plan), format='json')
    assert resp.status_code == status.HTTP_201_CREATED


def test_update_task_rejects_template_without_published_version(
    plan, admin_user, published_template, unpublished_template
):
    client = auth_client(admin_user)
    created = client.post(
        '/api/maintenance/plan-tasks/',
        task_payload(plan, checklist_template=str(published_template.id)),
        format='json',
    )
    task_id = created.json()['id']

    resp = client.patch(
        f'/api/maintenance/plan-tasks/{task_id}/',
        {'checklist_template': str(unpublished_template.id)},
        format='json',
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ── Comportamiento del motor ─────────────────────────────────────────────────

def make_plan(asset, template=None):
    """Crea el plan por el ORM, saltandose el serializer.

    Reproduce los planes que ya existian antes de la validacion y el caso de
    despublicar una version despues de crear el plan. La pendiente ya vence,
    para que la corrida programada la convierta en OT.
    """
    return _make_plan(
        f"Plan {template.name if template else 'sin checklist'}",
        assets=[asset],
        checklist_template=template,
        next_due_date=date.today() - timedelta(days=1),
    )


def test_generate_attaches_current_version(asset, admin_user, published_template):
    plan = make_plan(asset, published_template)
    result = generate_work_orders_for_plan(plan, triggered_by=admin_user)

    assert result['created'] == 1
    wo = WorkOrder.objects.get(tasks__plan_task__plan=plan)
    assert wo.tasks.first().checklist_version_id is not None


def test_generate_warns_when_template_has_no_published_version(
    asset, admin_user, unpublished_template
):
    plan = make_plan(asset, unpublished_template)
    result = generate_work_orders_for_plan(plan, triggered_by=admin_user)

    # La OT se crea igual: no generarla cancelaria el preventivo en silencio.
    assert result['created'] == 1
    wo = WorkOrder.objects.get(tasks__plan_task__plan=plan)
    assert wo.tasks.first().checklist_version_id is None
    # Pero el fallo tiene que ser visible en la respuesta del disparo.
    assert any('no tiene version publicada' in w for w in result['warnings'])


def test_generate_without_template_does_not_warn(asset, admin_user):
    plan = make_plan(asset, template=None)
    result = generate_work_orders_for_plan(plan, triggered_by=admin_user)

    assert result['created'] == 1
    assert not any('version publicada' in w for w in result['warnings'])
