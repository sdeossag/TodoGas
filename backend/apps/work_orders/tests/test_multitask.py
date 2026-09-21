"""OT con varias tareas: transiciones e integridad (fase 1 del modelo de tareas).

Una OT agrupa tareas de varios activos, cada una con su checklist. Aqui se
comprueba que el ciclo completo respeta eso: no se envia a revision con un
checklist a medias, cerrar la OT deja un acta cuyo hash verifica, cancelarla
reemite sus tareas, y la verificacion usa la version del algoritmo con que se
firmo cada acta.
"""

from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.checklists.models import (
    ChecklistField,
    ChecklistFieldResponse,
    ChecklistResponse,
    ChecklistTemplate,
    ChecklistTemplateVersion,
)
from apps.evidence.models import Photo, Signature
from apps.maintenance import services
from apps.maintenance.models import Task
from apps.maintenance.testing import make_plan, pending_task
from apps.reports.models import GeneratedReport
from apps.users.models import User
from apps.work_orders.integrity import compute_wo_content_hash
from apps.work_orders.models import WorkOrder
from apps.work_orders.transitions import apply_transition


def client_for(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def admin(db):
    return baker.make(User, role=User.Role.ADMIN, is_active=True, email="admin@mt.test")


@pytest.fixture
def tec(db):
    return baker.make(User, role=User.Role.TEC, is_active=True, email="tec@mt.test")


@pytest.fixture
def hospital(db):
    return baker.make(Hospital, is_active=True, name="Clinica Piso 3")


@pytest.fixture
def version(db, admin):
    plantilla = baker.make(ChecklistTemplate, name="Preventivo")
    v = baker.make(ChecklistTemplateVersion, template=plantilla, version_number=1, is_current=True)
    baker.make(ChecklistField, version=v, label="Presion (PSI)", field_type="NUMBER",
               is_required=True, sort_order=0)
    return v


@pytest.fixture
def ot_de_piso(hospital, admin, tec, version):
    """Una OT del Piso 3 con tres tareas: alarma, caja de control y tomas."""
    activos = [
        baker.make(Asset, hospital=hospital, status=Asset.Status.ACTIVE, name=nombre)
        for nombre in ("Alarma 3 gases", "Caja de control", "Salidas 24 tomas")
    ]
    plan = make_plan(
        "Plan piso", assets=activos, checklist_template=version.template,
        next_due_date=date.today() - timedelta(days=1),
    )
    tareas = [pending_task(plan, a) for a in activos]
    ot, _ = services.create_work_order_for_tasks(tareas, admin, assigned_to=tec)
    ot.status = WorkOrder.Status.IN_PROGRESS
    ot.started_at = timezone.now()
    ot.save()
    return ot


def responder(tarea, tec, completo=True):
    respuesta = ChecklistResponse.objects.create(
        task=tarea, version=tarea.checklist_version, completed_by=tec,
        started_at=timezone.now(),
        completed_at=timezone.now() if completo else None,
    )
    ChecklistFieldResponse.objects.create(
        response=respuesta, field=tarea.checklist_version.fields.get(), value="55",
    )
    return respuesta


def evidencia(ot, tec):
    Photo.objects.create(
        work_order=ot, file_url="f.jpg", taken_at=timezone.now(),
        file_hash="a" * 64, uploaded_by=tec,
    )
    Signature.objects.create(
        work_order=ot, signature_type=Signature.SignatureType.TECHNICIAN,
        file_url="s.png", signer_name="Tecnico", file_hash="b" * 64,
    )


# ── Revision: todos los checklists ───────────────────────────────────────────

def test_no_pasa_a_revision_con_un_checklist_a_medias(ot_de_piso, tec):
    tareas = list(ot_de_piso.tasks.all())
    responder(tareas[0], tec)
    responder(tareas[1], tec)
    responder(tareas[2], tec, completo=False)
    evidencia(ot_de_piso, tec)

    resp = client_for(tec).post(
        reverse("work-orders-transition", kwargs={"pk": ot_de_piso.id}),
        {"new_status": "IN_REVIEW"}, format="json",
    )

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Salidas 24 tomas" in str(resp.data), "el mensaje dice a que activo le falta"


def test_pasa_a_revision_con_todos_completos(ot_de_piso, tec):
    for tarea in ot_de_piso.tasks.all():
        responder(tarea, tec)
    evidencia(ot_de_piso, tec)

    resp = client_for(tec).post(
        reverse("work-orders-transition", kwargs={"pk": ot_de_piso.id}),
        {"new_status": "IN_REVIEW"}, format="json",
    )

    assert resp.status_code == status.HTTP_200_OK


# ── Cerrar: el acta verifica ─────────────────────────────────────────────────

def test_cerrar_la_ot_deja_un_acta_que_verifica(ot_de_piso, tec, admin):
    """
    El hash se calcula en el momento en que se genera el acta. Si las tareas se
    cerraran despues, el hash las veria "programadas" y la verificacion (ya
    "finalizadas") daria alteracion para siempre.
    """
    for tarea in ot_de_piso.tasks.all():
        responder(tarea, tec)
    evidencia(ot_de_piso, tec)
    apply_transition(ot_de_piso, WorkOrder.Status.IN_REVIEW, tec)

    sellado = {}

    def generar_acta(work_order_id):
        wo = WorkOrder.objects.get(pk=work_order_id)
        sellado["hash"] = compute_wo_content_hash(wo)
        GeneratedReport.objects.create(
            work_order=wo, report_type=GeneratedReport.ReportType.WORK_ORDER,
            title="Acta", file_url="acta.pdf", file_hash="c" * 64,
            content_hash=sellado["hash"], integrity_version="2",
        )

    with patch("apps.reports.tasks.generate_work_order_pdf.delay", side_effect=generar_acta):
        apply_transition(ot_de_piso, WorkOrder.Status.COMPLETED, admin)

    assert set(ot_de_piso.tasks.values_list("status", flat=True)) == {Task.Status.DONE}
    resp = client_for(admin).get(
        reverse("work-order-integrity", kwargs={"pk": str(ot_de_piso.id)})
    )
    assert resp.data["verified"] is True
    assert resp.data["algorithm_version"] == "2"


def test_cerrar_crea_la_siguiente_de_cada_activo(ot_de_piso, tec, admin):
    for tarea in ot_de_piso.tasks.all():
        responder(tarea, tec)
    evidencia(ot_de_piso, tec)
    apply_transition(ot_de_piso, WorkOrder.Status.IN_REVIEW, tec)

    with patch("apps.reports.tasks.generate_work_order_pdf.delay"):
        apply_transition(ot_de_piso, WorkOrder.Status.COMPLETED, admin)

    pendientes = Task.objects.filter(status=Task.Status.PENDING)
    assert pendientes.count() == 3
    assert {t.asset_id for t in pendientes} == {t.asset_id for t in ot_de_piso.tasks.all()}


# ── Cancelar: las tareas vuelven a pendientes (D6) ───────────────────────────

def test_cancelar_por_api_reemite_las_tareas(ot_de_piso, admin):
    resp = client_for(admin).post(
        reverse("work-orders-cancel", kwargs={"pk": ot_de_piso.id}),
        {"comment": "ERROR DE ASIGNACION"}, format="json",
    )

    assert resp.status_code == status.HTTP_200_OK
    assert ot_de_piso.tasks.filter(status=Task.Status.CANCELLED).count() == 3
    reemitidas = Task.objects.filter(status=Task.Status.PENDING, work_order__isnull=True)
    assert reemitidas.count() == 3


# ── Integridad v2: cualquier tarea ───────────────────────────────────────────

def test_v2_detecta_la_alteracion_de_cualquier_tarea(ot_de_piso, tec):
    tareas = list(ot_de_piso.tasks.all())
    for tarea in tareas:
        responder(tarea, tec)
    antes = compute_wo_content_hash(ot_de_piso)

    campo = ChecklistFieldResponse.objects.get(response__task=tareas[2])
    campo.value = "10"
    campo.save()

    assert compute_wo_content_hash(ot_de_piso) != antes


def test_v2_incluye_hospital_y_tareas(ot_de_piso):
    from apps.work_orders.integrity import build_integrity_payload

    payload = build_integrity_payload(ot_de_piso)

    assert payload["algorithm_version"] == "2"
    assert payload["work_order"]["hospital"] == str(ot_de_piso.hospital_id)
    assert len(payload["tasks"]) == 3
    assert "asset" not in payload["work_order"]


# ── Verificacion por la version con que se firmo ─────────────────────────────

def test_un_acta_v1_se_verifica_con_v1(hospital, admin, tec, version):
    """Antes una version distinta respondia "regenera el reporte", y regenerar
    lavaba cualquier alteracion."""
    from apps.maintenance.testing import make_work_order

    activo = baker.make(Asset, hospital=hospital, status=Asset.Status.ACTIVE)
    ot = make_work_order(
        activo, admin, status=WorkOrder.Status.COMPLETED, assigned_to=tec,
        checklist_version=version, completed_at=timezone.now(),
    )
    GeneratedReport.objects.create(
        work_order=ot, report_type=GeneratedReport.ReportType.WORK_ORDER,
        title="Acta vieja", file_url="vieja.pdf", file_hash="d" * 64,
        content_hash=compute_wo_content_hash(ot, "1"), integrity_version="1",
    )

    resp = client_for(admin).get(reverse("work-order-integrity", kwargs={"pk": str(ot.id)}))

    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["verified"] is True
    assert resp.data["algorithm_version"] == "1"


def test_version_desconocida_no_se_da_por_verificada(hospital, admin):
    from apps.maintenance.testing import make_work_order

    activo = baker.make(Asset, hospital=hospital, status=Asset.Status.ACTIVE)
    ot = make_work_order(activo, admin, status=WorkOrder.Status.COMPLETED)
    GeneratedReport.objects.create(
        work_order=ot, report_type=GeneratedReport.ReportType.WORK_ORDER,
        title="Acta", file_url="x.pdf", file_hash="e" * 64,
        content_hash="0" * 64, integrity_version="9",
    )

    resp = client_for(admin).get(reverse("work-order-integrity", kwargs={"pk": str(ot.id)}))

    assert resp.status_code == status.HTTP_409_CONFLICT
    assert resp.data["verified"] is None


# ── Compatibilidad de la API ─────────────────────────────────────────────────

def test_el_detalle_expone_las_tareas_y_el_primer_activo(ot_de_piso, admin):
    resp = client_for(admin).get(reverse("work-orders-detail", kwargs={"pk": ot_de_piso.id}))

    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.data["tasks"]) == 3
    assert resp.data["asset"]["name"] == "Alarma 3 gases"
    assert resp.data["hospital"]["name"] == "Clinica Piso 3"


def test_filtrar_por_activo_no_repite_la_ot(ot_de_piso, admin):
    activo = ot_de_piso.tasks.first().asset
    resp = client_for(admin).get(reverse("work-orders-list"), {"search": "a"})

    ids = [r["id"] for r in resp.data["results"]]
    assert ids.count(str(ot_de_piso.id)) == 1

    resp = client_for(admin).get(reverse("work-orders-list"), {"asset_id": activo.id})
    assert [r["id"] for r in resp.data["results"]] == [str(ot_de_piso.id)]
