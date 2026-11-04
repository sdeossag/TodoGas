"""
Aprobó / Alerta / Falló: tipo de respuesta como el de Fracttal. Se guarda en la
columna de texto de siempre con APROBO, ALERTA, FALLO (y NA si el campo permite
N/A). Alerta y Falló cuentan como respondidos y quitan un pendiente igual que
cualquier otra respuesta; no bloquean nada por sí solos.
"""

import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.checklists.models import ChecklistField, ChecklistTemplate, ChecklistTemplateVersion
from apps.checklists.validators import validate_field_value
from apps.maintenance import services
from apps.maintenance.models import MaintenancePlan, PlanTask, Task
from apps.users.models import User
from apps.work_orders.models import WorkOrder


def campo_paf(options_json):
    return ChecklistField(field_type="PASS_ALERT_FAIL", options_json=options_json, label="Estado")


def test_acepta_solo_los_tres_valores():
    campo = campo_paf([])
    for valor in ("APROBO", "ALERTA", "FALLO"):
        validate_field_value(campo, valor)
    for malo in ("aprobo", "true", "SI", "", "Falló", "NA"):
        with pytest.raises(ValueError):
            validate_field_value(campo, malo)


def test_na_solo_si_el_campo_lo_permite():
    con_na = campo_paf({"allow_na": True})
    assert con_na.allows_na
    validate_field_value(con_na, "NA")
    for opciones in ([], {}, {"allow_na": False}):
        campo = campo_paf(opciones)
        assert not campo.allows_na
        with pytest.raises(ValueError, match="no admite N/A"):
            validate_field_value(campo, "NA")


@pytest.mark.django_db
class TestPorLaApi:
    @pytest.fixture
    def d(self):
        admin = baker.make(User, role=User.Role.ADMIN, is_active=True)
        tec = baker.make(User, role=User.Role.TEC, is_active=True)
        h = baker.make(Hospital, is_active=True)
        activo = Asset.objects.create(hospital=h, name="Toma", code="TMA-PAF")
        t = ChecklistTemplate.objects.create(name="Revisión de tomas")
        v = ChecklistTemplateVersion.objects.create(
            template=t, version_number=1, published_by=admin, is_current=True
        )
        con_na = ChecklistField.objects.create(
            version=v, label="Estado general", field_type="PASS_ALERT_FAIL",
            options_json={"allow_na": True}, is_required=True, sort_order=1,
        )
        sin_na = ChecklistField.objects.create(
            version=v, label="Acople", field_type="PASS_ALERT_FAIL", options_json=[], sort_order=2,
        )
        plan = MaintenancePlan.objects.create(name="PREV TOMAS")
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
        r = tarea.checklist_response
        return {
            "c": c, "admin": admin, "ot": ot, "respuesta": r, "con_na": con_na, "sin_na": sin_na,
            "url": f"/api/checklists/responses/{r.id}/submit-field/",
        }

    def test_guarda_el_valor_tal_cual(self, d):
        for valor in ("APROBO", "ALERTA", "FALLO"):
            r = d["c"].post(d["url"], {"field": str(d["sin_na"].id), "value": valor}, format="json")
            assert r.status_code == 200, r.data
            assert r.data["value"] == valor and r.data["field_type"] == "PASS_ALERT_FAIL"
        r = d["c"].post(d["url"], {"field": str(d["sin_na"].id), "value": "true"}, format="json")
        assert r.status_code == 400

    def test_na_segun_el_campo(self, d):
        r = d["c"].post(d["url"], {"field": str(d["con_na"].id), "value": "NA"}, format="json")
        assert r.status_code == 200, r.data
        r = d["c"].post(d["url"], {"field": str(d["sin_na"].id), "value": "NA"}, format="json")
        assert r.status_code == 400 and "no admite N/A" in r.data["value"]

    def test_fallo_y_alerta_quitan_un_pendiente_y_cuentan_como_respondidos(self, d):
        url = reverse("checklist-responses-set-pending", kwargs={"pk": d["respuesta"].id})
        for valor, campo in (("FALLO", d["sin_na"]), ("ALERTA", d["con_na"])):
            d["c"].post(url, {"pendientes": [
                {"field": str(campo.id), "repetition": 0, "reason": "sin acceso"}
            ]}, format="json")
            d["respuesta"].refresh_from_db()
            assert len(d["respuesta"].pendientes) == 1
            r = d["c"].post(d["url"], {"field": str(campo.id), "value": valor}, format="json")
            assert r.status_code == 200, r.data
            d["respuesta"].refresh_from_db()
            assert d["respuesta"].pendientes == []
        assert d["respuesta"].field_responses.count() == 2

    def test_el_supervisor_corrige_en_revision(self, d):
        d["c"].post(d["url"], {"field": str(d["sin_na"].id), "value": "APROBO"}, format="json")
        d["ot"].status = WorkOrder.Status.IN_REVIEW
        d["ot"].save()
        admin = APIClient()
        admin.force_authenticate(user=d["admin"])
        url = f"/api/checklists/responses/{d['respuesta'].id}/correct-field/"
        r = admin.post(url, {"field": str(d["sin_na"].id), "value": "FALLO"}, format="json")
        assert r.status_code == 200, r.data
        assert r.data["value"] == "FALLO" and r.data["corrected_by_name"]
        r = admin.post(url, {"field": str(d["sin_na"].id), "value": "NA"}, format="json")
        assert r.status_code == 400
