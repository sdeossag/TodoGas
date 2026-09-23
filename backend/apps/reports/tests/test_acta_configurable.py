"""
Acta configurable (#107, decision del 2026-09-23): un solo formato con
interruptores por seccion y campo, como las "Opciones de Impresion" de
Fracttal. Lo que prueba el servicio (checklist, hash) no se puede apagar.
"""

import sys
import types
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone
from model_bakery import baker
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.checklists.models import (
    ChecklistField,
    ChecklistFieldResponse,
    ChecklistTemplate,
    ChecklistTemplateVersion,
)
from apps.maintenance import services
from apps.maintenance.models import Task
from apps.maintenance.testing import make_plan
from apps.reports.models import GeneratedReport, ReportSettings
from apps.reports.options import CLAVES, efectivas, numeracion
from apps.users.models import User
from apps.work_orders.models import WorkOrder

pytestmark = pytest.mark.django_db

URL = "/api/report-settings/"


def cliente(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def admin():
    return baker.make(User, role=User.Role.ADMIN, is_active=True)


@pytest.fixture
def sup():
    return baker.make(User, role=User.Role.SUP, is_active=True)


@pytest.fixture
def ot(admin):
    """OT finalizada con fabricante, una respuesta con observacion y notas."""
    t = baker.make(ChecklistTemplate, name="Alarma")
    v = baker.make(ChecklistTemplateVersion, template=t, version_number=1, is_current=True)
    campo = baker.make(ChecklistField, version=v, label="Voltaje", field_type="TEXT",
                       group="", is_required=True, sort_order=0)
    hospital = baker.make(Hospital, is_active=True)
    activo = baker.make(Asset, hospital=hospital, status=Asset.Status.ACTIVE, code="ALR-1",
                        manufacturer="AMICO")
    plan = make_plan("MANT. ALARMA", assets=[activo], checklist_template=t,
                     next_due_date=timezone.localdate())
    tarea = Task.objects.get(plan_task__plan=plan, status=Task.Status.PENDING)
    orden, _ = services.create_work_order_for_tasks([tarea], admin, assigned_to=admin)
    r = orden.tasks.get().checklist_response
    ChecklistFieldResponse.objects.create(response=r, field=campo, value="118 V",
                                          notes="Borne flojo")
    WorkOrder.objects.filter(pk=orden.pk).update(
        status=WorkOrder.Status.COMPLETED, completed_at=timezone.now(), notes="Nota interna",
    )
    orden.refresh_from_db()
    return orden


def acta_html(ot):
    """(html, reporte) de generate_service_report_pdf, sin WeasyPrint real."""
    from apps.reports.generator import generate_service_report_pdf

    html = {}
    falso = types.ModuleType("weasyprint")

    def HTML(string, base_url=None):
        html["texto"] = string
        return MagicMock(write_pdf=lambda: b"%PDF-falso")

    falso.HTML = HTML
    with patch.dict(sys.modules, {"weasyprint": falso}), \
            patch("apps.reports.generator.default_storage") as storage:
        storage.save.return_value = "reports/x.pdf"
        storage.url.side_effect = lambda clave: f"/media/{clave}"
        generate_service_report_pdf(ot)
    return html["texto"], GeneratedReport.objects.latest("generated_at")


# ── Las opciones ──────────────────────────────────────────────────────────────

def test_por_defecto_todo_esta_encendido():
    assert efectivas() == {clave: True for clave in CLAVES}


def test_apagar_una_seccion_no_deja_hueco_en_la_numeracion():
    op = efectivas({"resumen_activos": False, "fotos_visita": False})
    assert numeracion(op) == {"visita": 1, "activos": 2, "hallazgos": 3, "materiales": 4, "firmas": 5}


def test_sin_ninguna_firma_no_hay_seccion_de_firmas():
    op = efectivas({"firma_realizado": False, "firma_validado": False, "firma_aceptado": False})
    assert "firmas" not in numeracion(op)


# ── La API ────────────────────────────────────────────────────────────────────

def test_el_administrador_ve_el_catalogo_y_lo_siempre_incluido(admin):
    r = cliente(admin).get(URL)
    assert r.status_code == 200
    assert {c["key"] for c in r.data["catalog"]} == CLAVES
    assert "Respuestas del checklist" in r.data["always_included"]
    assert all(r.data["options"].values())


def test_solo_el_administrador_configura_el_acta(sup):
    assert cliente(sup).get(URL).status_code == 403
    assert cliente(sup).patch(URL, {"options": {"materiales": False}}, format="json").status_code == 403


def test_guardar_cambia_solo_lo_enviado(admin):
    c = cliente(admin)
    c.patch(URL, {"options": {"materiales": False}}, format="json")
    r = c.patch(URL, {"options": {"fotos_gps": False}}, format="json")
    assert r.status_code == 200
    assert r.data["options"]["materiales"] is False
    assert r.data["options"]["fotos_gps"] is False
    assert r.data["options"]["visita_ejecutor"] is True
    assert ReportSettings.objects.count() == 1


@pytest.mark.parametrize("opciones", [
    {"checklist_respuestas": False},  # lo que prueba el servicio no se apaga
    {"materiales": "no"},
])
def test_no_se_aceptan_opciones_raras(admin, opciones):
    r = cliente(admin).patch(URL, {"options": opciones}, format="json")
    assert r.status_code == 400


# ── El acta ───────────────────────────────────────────────────────────────────

def test_el_acta_sin_configurar_trae_todo(ot):
    texto, reporte = acta_html(ot)
    for rotulo in ("Fabricante", "AMICO", "Observaciones", "Borne flojo", "Nota interna",
                   "Materiales utilizados", "Realizado por", "Validado por", "Aceptado por"):
        assert rotulo in texto
    assert reporte.options_used == efectivas()


def test_lo_apagado_no_sale_en_el_acta_y_queda_registrado(ot, admin):
    cliente(admin).patch(URL, {"options": {
        "activo_fabricante": False, "checklist_observaciones": False,
        "visita_notas": False, "materiales": False, "firma_validado": False,
    }}, format="json")
    texto, reporte = acta_html(ot)
    for rotulo in ("AMICO", "Borne flojo", "Nota interna", "Materiales utilizados", "Validado por"):
        assert rotulo not in texto
    # Lo que prueba el servicio sigue.
    assert "118 V" in texto
    assert "Realizado por" in texto
    assert reporte.options_used["materiales"] is False


def test_la_vista_previa_no_guarda_nada(ot, admin):
    falso = types.ModuleType("weasyprint")
    falso.HTML = lambda string, base_url=None: MagicMock(write_pdf=lambda: b"%PDF-previa")
    with patch.dict(sys.modules, {"weasyprint": falso}):
        r = cliente(admin).post(URL + "preview/", {"options": {"materiales": False}}, format="json")
    assert r.status_code == 200
    assert r["Content-Type"] == "application/pdf"
    assert r.content == b"%PDF-previa"
    assert GeneratedReport.objects.count() == 0
    assert ReportSettings.current().options == {}
