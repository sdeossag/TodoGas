"""
Si/No/N/A (decision del 2026-09-24): el N/A es una opcion del campo Si/No.
El tecnico responde "na" solo si el campo lo permite, cuenta como respondido
y el acta imprime "N/A".
"""

import pytest
from model_bakery import baker
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.checklists.models import ChecklistField, ChecklistTemplate, ChecklistTemplateVersion
from apps.maintenance import services
from apps.maintenance.models import MaintenancePlan, PlanTask, Task
from apps.reports.generator import _sections
from apps.users.models import User
from apps.work_orders.models import WorkOrder

pytestmark = pytest.mark.django_db


@pytest.fixture
def d():
    admin = baker.make(User, role=User.Role.ADMIN, is_active=True)
    tec = baker.make(User, role=User.Role.TEC, is_active=True)
    h = baker.make(Hospital, is_active=True)
    activo = Asset.objects.create(hospital=h, name="Alarma", code="ALR-NA")
    t = ChecklistTemplate.objects.create(name="Alarma 3 gases")
    v = ChecklistTemplateVersion.objects.create(template=t, version_number=1, published_by=admin, is_current=True)
    con_na = ChecklistField.objects.create(
        version=v, label="¿Monitorea aire medicinal?", field_type="BOOLEAN",
        options_json={"allow_na": True}, is_required=True, sort_order=1,
    )
    sin_na = ChecklistField.objects.create(
        version=v, label="¿Tiene fuga?", field_type="BOOLEAN", options_json=[], sort_order=2,
    )
    plan = MaintenancePlan.objects.create(name="PREV ALARMA")
    PlanTask.objects.create(plan=plan, name="Preventivo", checklist_template=t,
                            frequency_value=6, frequency_unit="MONTHS")
    services.set_asset_plan(activo, plan)
    tarea = Task.objects.get(plan_task__plan=plan, asset=activo)
    ot, _ = services.create_work_order_for_tasks([tarea], admin)
    ot.assigned_to = tec
    ot.status = WorkOrder.Status.IN_PROGRESS
    ot.save()
    c = APIClient()
    c.force_authenticate(user=tec)
    return {
        "c": c, "respuesta": tarea.checklist_response, "con_na": con_na, "sin_na": sin_na,
        "url": f"/api/checklists/responses/{tarea.checklist_response.id}/submit-field/",
    }


def test_el_tecnico_responde_na_donde_se_permite(d):
    r = d["c"].post(d["url"], {"field": str(d["con_na"].id), "value": "na"}, format="json")
    assert r.status_code == 200, r.data
    r = d["c"].post(d["url"], {"field": str(d["sin_na"].id), "value": "na"}, format="json")
    assert r.status_code == 400 and "no admite N/A" in r.data["value"]


def test_el_acta_imprime_na(d):
    d["c"].post(d["url"], {"field": str(d["con_na"].id), "value": "na"}, format="json")
    d["c"].post(d["url"], {"field": str(d["sin_na"].id), "value": "false"}, format="json")
    [seccion] = _sections(d["respuesta"])
    assert [f["value"] for f in seccion["rows"]] == ["N/A", "No"]
