"""
El acta dice cuando se hizo el trabajo y quien lo hizo (decision del 2026-09-23).

En Fracttal el cliente pidio quitar "fecha de finalizacion" y "tecnico
responsable" porque mentian: eran la hora de sincronizar y el asignado del
momento. Aqui no se esconden, se registran bien: la hora es la del telefono
(tambien sin red), el ejecutor es quien cerro el checklist y la validacion es
quien aprobo la OT.
"""

import base64
import sys
import types
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.checklists.models import ChecklistField, ChecklistTemplate, ChecklistTemplateVersion
from apps.evidence.models import Signature
from apps.maintenance import services
from apps.maintenance.models import Task
from apps.maintenance.testing import make_plan
from apps.users.models import User
from apps.work_orders.device_time import device_time
from apps.work_orders.models import WorkOrder
from apps.work_orders.transitions import apply_transition

pytestmark = pytest.mark.django_db

# PNG de 1x1: basta para que la firma pase la validacion de base64.
PNG = base64.b64encode(
    bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
        "1f15c4890000000d49444154789c6360000002000100e221bc330000000049454e44ae426082"
    )
).decode()


def cliente(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def admin():
    return baker.make(User, role=User.Role.ADMIN, is_active=True,
                      first_name="Ana", last_name="Supervisora")


@pytest.fixture
def tec():
    return baker.make(User, role=User.Role.TEC, is_active=True,
                      first_name="Juan", last_name="Zuleta")


@pytest.fixture
def otro_tec():
    return baker.make(User, role=User.Role.TEC, is_active=True,
                      first_name="Victor", last_name="Vargas")


@pytest.fixture
def ot(admin, tec):
    """OT en curso creada hace 3 horas, con un checklist de un campo."""
    t = baker.make(ChecklistTemplate, name="Alarma")
    v = baker.make(ChecklistTemplateVersion, template=t, version_number=1, is_current=True)
    baker.make(ChecklistField, version=v, label="Voltaje", field_type="TEXT",
               group="", is_required=True, sort_order=0)
    hospital = baker.make(Hospital, is_active=True)
    activo = baker.make(Asset, hospital=hospital, status=Asset.Status.ACTIVE, code="ALR-1")
    plan = make_plan("MANT. ALARMA", assets=[activo], checklist_template=t,
                     next_due_date=timezone.localdate())
    tarea = Task.objects.get(plan_task__plan=plan, status=Task.Status.PENDING)
    orden, _ = services.create_work_order_for_tasks([tarea], admin, assigned_to=tec)
    WorkOrder.objects.filter(pk=orden.pk).update(
        status=WorkOrder.Status.IN_PROGRESS,
        created_at=timezone.now() - timedelta(hours=3),
    )
    orden.refresh_from_db()
    return orden


def respuesta_de(ot):
    return ot.tasks.get().checklist_response


def responder(c, ot, value, answered_at=None):
    r = respuesta_de(ot)
    datos = {"field": str(r.version.fields.get().id), "value": value}
    if answered_at is not None:
        datos["answered_at"] = answered_at.isoformat()
    return c.post(reverse("checklist-responses-submit-field", kwargs={"pk": r.id}),
                  datos, format="json")


def cerrar(c, ot, completed_at=None):
    r = respuesta_de(ot)
    datos = {"completed_at": completed_at.isoformat()} if completed_at else {}
    return c.post(reverse("checklist-responses-complete", kwargs={"pk": r.id}),
                  datos, format="json")


def acta_html(ot):
    """El HTML que recibe WeasyPrint, sin generar el PDF."""
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
    return html["texto"]


# ── La hora del telefono ──────────────────────────────────────────────────────

def test_la_hora_del_telefono_se_acepta_si_es_creible(ot):
    hace_dos_horas = timezone.now() - timedelta(hours=2)
    assert device_time(hace_dos_horas, ot) == hace_dos_horas


@pytest.mark.parametrize("desfase", [timedelta(hours=1), -timedelta(days=2)])
def test_un_reloj_imposible_cae_a_la_hora_del_servidor(ot, desfase):
    """En el futuro, o antes de que existiera la OT: el reloj del telefono esta mal."""
    antes = timezone.now()
    assert device_time(timezone.now() + desfase, ot) >= antes


def test_sin_hora_del_telefono_manda_la_del_servidor(ot):
    antes = timezone.now()
    assert device_time(None, ot) >= antes


def test_la_respuesta_sin_red_guarda_la_hora_en_que_se_respondio(ot, tec):
    en_campo = timezone.now() - timedelta(hours=2)
    assert responder(cliente(tec), ot, "118 V", en_campo).status_code in (200, 201)
    assert respuesta_de(ot).field_responses.get().answered_at == en_campo


def test_el_cierre_sin_red_guarda_la_hora_en_que_se_cerro(ot, tec):
    c = cliente(tec)
    responder(c, ot, "118 V", timezone.now() - timedelta(hours=2))
    en_campo = timezone.now() - timedelta(minutes=110)
    assert cerrar(c, ot, en_campo).status_code == 200
    assert respuesta_de(ot).completed_at == en_campo


@patch("apps.evidence.serializers.default_storage")
def test_la_firma_sin_red_guarda_la_hora_en_que_se_firmo(storage, ot, tec):
    storage.save.return_value = "evidence/signatures/x.png"
    storage.url.return_value = "/media/x.png"
    en_campo = timezone.now() - timedelta(minutes=100)
    r = cliente(tec).post("/api/evidence/signatures/", {
        "work_order": str(ot.id), "image_data": PNG, "signer_name": "Juan Zuleta",
        "signed_at": en_campo.isoformat(),
    }, format="json")
    assert r.status_code == 201, r.data
    assert Signature.objects.get(pk=r.data["id"]).signed_at == en_campo


# ── El acta ───────────────────────────────────────────────────────────────────

def test_el_acta_dice_cuando_se_hizo_el_trabajo_no_cuando_se_aprobo(ot, tec, admin):
    c = cliente(tec)
    responder(c, ot, "118 V", timezone.now() - timedelta(hours=2))
    cerrar(c, ot, timezone.now() - timedelta(minutes=90))
    WorkOrder.objects.filter(pk=ot.pk).update(status=WorkOrder.Status.IN_REVIEW)
    ot.refresh_from_db()
    with patch("apps.reports.tasks.generate_work_order_pdf.delay"):
        apply_transition(ot, WorkOrder.Status.COMPLETED, admin)

    texto = acta_html(ot)
    local = timezone.localtime
    assert "Trabajo en campo" in texto
    assert local(timezone.now() - timedelta(hours=2)).strftime("%H:%M") in texto
    assert "30 min" in texto, "la duracion va de la primera respuesta al cierre"
    assert "Fecha de intervención" not in texto
    assert "Duración real" not in texto


def test_el_ejecutor_es_quien_cerro_no_el_asignado_despues(ot, tec, otro_tec, admin):
    """Reasignada en revision, el acta de Fracttal ponia de responsable a quien no fue."""
    c = cliente(tec)
    responder(c, ot, "118 V")
    cerrar(c, ot)
    WorkOrder.objects.filter(pk=ot.pk).update(assigned_to=otro_tec)
    ot.refresh_from_db()

    texto = acta_html(ot)
    assert "Ejecutado por" in texto
    assert "Juan Zuleta" in texto
    assert "Victor Vargas" not in texto


def test_validado_por_es_quien_aprobo_la_ot(ot, tec, admin):
    c = cliente(tec)
    responder(c, ot, "118 V")
    cerrar(c, ot)
    WorkOrder.objects.filter(pk=ot.pk).update(status=WorkOrder.Status.IN_REVIEW)
    ot.refresh_from_db()

    assert "Pendiente de aprobación" in acta_html(ot)

    with patch("apps.reports.tasks.generate_work_order_pdf.delay"):
        apply_transition(ot, WorkOrder.Status.COMPLETED, admin)
    texto = acta_html(ot)
    for rotulo in ("Realizado por", "Validado por", "Aceptado por"):
        assert rotulo in texto
    assert "Ana Supervisora" in texto
    assert "Pendiente de aprobación" not in texto


def test_el_acta_se_genera_con_la_aprobacion_ya_registrada(ot, admin):
    """En desarrollo el acta se genera en el acto: el historial tiene que ir antes."""
    WorkOrder.objects.filter(pk=ot.pk).update(status=WorkOrder.Status.IN_REVIEW)
    ot.refresh_from_db()
    visto = {}

    def al_generar(wo_id):
        visto["aprobacion"] = WorkOrder.objects.get(pk=wo_id).status_history.filter(
            to_status=WorkOrder.Status.COMPLETED
        ).exists()

    with patch("apps.reports.tasks.generate_work_order_pdf.delay", side_effect=al_generar):
        apply_transition(ot, WorkOrder.Status.COMPLETED, admin)
    assert visto["aprobacion"] is True
