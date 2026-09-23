"""Fase 3: ejecucion de una OT con varios activos.

El checklist de cada tarea se crea al meterla en la OT (el tecnico puede
trabajar sin red desde el primer campo), la OT se puede ajustar mientras no ha
empezado, las fotos se atribuyen a un activo, la app descarga todo lo que
necesita en un paquete, y el acta sale con un bloque por activo.
"""

import sys
import types
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
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
from apps.evidence.models import Photo
from apps.maintenance import services
from apps.maintenance.models import Task
from apps.maintenance.testing import make_plan, pending_task
from apps.users.models import User
from apps.work_orders.models import WorkOrder

pytestmark = pytest.mark.django_db


def cliente(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def admin():
    return baker.make(User, role=User.Role.ADMIN, is_active=True)


@pytest.fixture
def tec():
    return baker.make(User, role=User.Role.TEC, is_active=True)


@pytest.fixture
def hospital():
    return baker.make(Hospital, is_active=True, name="Clinica Piso 3")


@pytest.fixture
def plantilla():
    t = baker.make(ChecklistTemplate, name="Preventivo tomas")
    v = baker.make(ChecklistTemplateVersion, template=t, version_number=1, is_current=True)
    baker.make(ChecklistField, version=v, label="Presion", field_type="NUMBER",
               is_required=True, sort_order=0)
    baker.make(ChecklistField, version=v, label="Observacion", field_type="TEXT",
               is_required=False, sort_order=1)
    return t


@pytest.fixture
def plan(hospital, plantilla):
    activos = [
        baker.make(Asset, hospital=hospital, status=Asset.Status.ACTIVE, name=n, code=c)
        for n, c in (("Alarma", "P3-1"), ("Caja", "P3-2"), ("Tomas", "P3-3"))
    ]
    return make_plan("Piso 3", assets=activos, checklist_template=plantilla,
                     next_due_date=date.today())


def pendientes(plan):
    return list(Task.objects.filter(plan_task__plan=plan, status=Task.Status.PENDING)
                .order_by("asset__code"))


@pytest.fixture
def ot(plan, admin, tec):
    tareas = pendientes(plan)[:2]
    orden, _ = services.create_work_order_for_tasks(tareas, admin, assigned_to=tec)
    return orden


# ── El checklist nace con la OT ───────────────────────────────────────────────

def test_cada_tarea_trae_su_checklist_vacio(ot, admin):
    for tarea in ot.tasks.all():
        respuesta = tarea.checklist_response
        assert respuesta.version == tarea.checklist_version
        assert respuesta.started_at is None and respuesta.completed_at is None

    detalle = cliente(admin).get(reverse("work-orders-detail", kwargs={"pk": ot.id})).data
    progreso = detalle["tasks"][0]["checklist"]
    assert progreso == {
        "response_id": progreso["response_id"],
        "answered": 0, "total": 2, "required_missing": 1, "completed_at": None,
        "block_changes": [],
    }


def test_la_primera_respuesta_marca_el_inicio(ot, tec):
    ot.status = WorkOrder.Status.IN_PROGRESS
    ot.save()
    respuesta = ot.tasks.first().checklist_response
    campo = respuesta.version.fields.get(label="Presion")

    resp = cliente(tec).post(
        reverse("checklist-responses-submit-field", kwargs={"pk": respuesta.id}),
        {"field": str(campo.id), "value": "55"}, format="json",
    )

    assert resp.status_code == status.HTTP_200_OK, resp.data
    respuesta.refresh_from_db()
    assert respuesta.started_at is not None


def test_pedir_el_checklist_otra_vez_devuelve_el_mismo(ot, tec):
    tarea = ot.tasks.first()
    resp = cliente(tec).post(reverse("checklist-responses-list"), {
        "task": str(tarea.id), "version": str(tarea.checklist_version_id),
    }, format="json")

    assert resp.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED), resp.data
    assert resp.data["id"] == str(tarea.checklist_response.id)
    assert ChecklistResponse.objects.filter(task=tarea).count() == 1


# ── Ajustar la OT antes de empezar ────────────────────────────────────────────

def test_agregar_una_tarea_crea_su_checklist_y_suma_duracion(ot, plan, admin):
    Task.objects.filter(plan_task__plan=plan).update(estimated_duration=timedelta(minutes=30))
    tercera = pendientes(plan)[0]

    resp = cliente(admin).post(
        reverse("work-orders-tasks", kwargs={"pk": ot.id}),
        {"task_ids": [str(tercera.id)]}, format="json",
    )

    assert resp.status_code == status.HTTP_200_OK, resp.data
    assert len(resp.data["tasks"]) == 3
    tercera.refresh_from_db()
    assert tercera.work_order == ot and tercera.checklist_response is not None
    ot.refresh_from_db()
    assert ot.estimated_duration == timedelta(minutes=90)


def test_quitar_una_tarea_la_devuelve_a_pendientes(ot, admin):
    tarea = ot.tasks.last()

    resp = cliente(admin).post(
        reverse("work-orders-remove-task", kwargs={"pk": ot.id}),
        {"task_id": str(tarea.id)}, format="json",
    )

    assert resp.status_code == status.HTTP_200_OK, resp.data
    tarea.refresh_from_db()
    assert tarea.status == Task.Status.PENDING and tarea.work_order is None
    assert not ChecklistResponse.objects.filter(task=tarea).exists()
    assert len(resp.data["tasks"]) == 1


def test_no_se_quita_la_ultima_ni_una_con_respuestas(ot, admin, tec):
    primera, segunda = list(ot.tasks.all())
    campo = segunda.checklist_version.fields.first()
    ChecklistFieldResponse.objects.create(
        response=segunda.checklist_response, field=campo, value="1"
    )
    c = cliente(admin)
    url = reverse("work-orders-remove-task", kwargs={"pk": ot.id})

    con_respuestas = c.post(url, {"task_id": str(segunda.id)}, format="json")
    c.post(url, {"task_id": str(primera.id)}, format="json")
    ultima = c.post(url, {"task_id": str(segunda.id)}, format="json")

    assert con_respuestas.status_code == status.HTTP_400_BAD_REQUEST
    assert "ya tiene respuestas" in con_respuestas.data["detail"]
    assert ultima.status_code == status.HTTP_400_BAD_REQUEST


def test_una_ot_empezada_no_se_modifica(ot, plan, admin):
    ot.status = WorkOrder.Status.IN_PROGRESS
    ot.save()
    resp = cliente(admin).post(
        reverse("work-orders-tasks", kwargs={"pk": ot.id}),
        {"task_ids": [str(pendientes(plan)[0].id)]}, format="json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_el_tecnico_no_ajusta_la_ot(ot, plan, tec):
    resp = cliente(tec).post(
        reverse("work-orders-tasks", kwargs={"pk": ot.id}),
        {"task_ids": [str(pendientes(plan)[0].id)]}, format="json",
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_cambiar_el_checklist_antes_de_responder(ot, admin, plantilla):
    nueva = baker.make(ChecklistTemplateVersion, template=plantilla, version_number=2)
    tarea = ot.tasks.first()

    resp = cliente(admin).post(
        reverse("work-orders-task-checklist", kwargs={"pk": ot.id}),
        {"task": str(tarea.id), "checklist_version": str(nueva.id)}, format="json",
    )

    assert resp.status_code == status.HTTP_200_OK, resp.data
    tarea.refresh_from_db()
    assert tarea.checklist_version == nueva
    assert tarea.checklist_response.version == nueva


# ── Fotos por activo ──────────────────────────────────────────────────────────

def _foto():
    return SimpleUploadedFile("f.jpg", b"\xff\xd8\xff\xe0" + b"0" * 64, content_type="image/jpeg")


@patch("apps.evidence.serializers.default_storage")
def test_la_foto_se_atribuye_a_un_activo(storage, ot, tec):
    storage.save.return_value = "evidence/x.jpg"
    storage.url.return_value = "/media/evidence/x.jpg"
    ot.status = WorkOrder.Status.IN_PROGRESS
    ot.save()
    tarea = ot.tasks.last()

    resp = cliente(tec).post("/api/evidence/photos/", {
        "work_order": str(ot.id), "task": str(tarea.id), "file": _foto(),
        "taken_at": timezone.now().isoformat(),
    }, format="multipart")

    assert resp.status_code == status.HTTP_201_CREATED, resp.data
    assert Photo.objects.get().task == tarea


@patch("apps.evidence.serializers.default_storage")
def test_la_foto_no_acepta_una_tarea_de_otra_ot(storage, ot, plan, tec):
    ot.status = WorkOrder.Status.IN_PROGRESS
    ot.save()
    ajena = pendientes(plan)[0]

    resp = cliente(tec).post("/api/evidence/photos/", {
        "work_order": str(ot.id), "task": str(ajena.id), "file": _foto(),
        "taken_at": timezone.now().isoformat(),
    }, format="multipart")

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "task" in resp.data


# ── Paquete para trabajar sin red ─────────────────────────────────────────────

def test_el_paquete_trae_la_ot_y_cada_checklist(ot, tec):
    resp = cliente(tec).get(reverse("work-orders-offline-bundle", kwargs={"pk": ot.id}))

    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.data["work_order"]["tasks"]) == 2
    assert len(resp.data["checklists"]) == 2
    checklist = resp.data["checklists"][0]
    assert [f["label"] for f in checklist["version_fields"]] == ["Presion", "Observacion"]
    assert str(checklist["task"]) == resp.data["work_order"]["tasks"][0]["id"]


def test_el_paquete_es_solo_del_tecnico_asignado(ot):
    otro = baker.make(User, role=User.Role.TEC, is_active=True)
    resp = cliente(otro).get(reverse("work-orders-offline-bundle", kwargs={"pk": ot.id}))
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# ── Acta con un bloque por activo ─────────────────────────────────────────────

def test_el_acta_tiene_un_bloque_por_activo(ot, tec):
    from apps.reports.generator import generate_service_report_pdf

    for tarea in ot.tasks.all():
        campo = tarea.checklist_version.fields.get(label="Presion")
        ChecklistFieldResponse.objects.create(
            response=tarea.checklist_response, field=campo, value=f"valor-{tarea.asset.code}"
        )
    Photo.objects.create(work_order=ot, task=ot.tasks.last(), file_url="a.jpg",
                         taken_at=timezone.now(), file_hash="a" * 64, uploaded_by=tec)
    # Un campo de foto guarda la URL firmada de S3: el acta no la imprime.
    primera = ot.tasks.first()
    foto = baker.make(ChecklistField, version=primera.checklist_version, label="Foto tablero",
                      field_type="PHOTO", is_required=False, sort_order=2)
    ChecklistFieldResponse.objects.create(
        response=primera.checklist_response, field=foto,
        value="https://bucket.s3.amazonaws.com/evidence/x.jpg?X-Amz-Signature=abc",
    )

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

    texto = html["texto"]
    assert "3.1 Alarma" in texto and "3.2 Caja" in texto
    assert "valor-P3-1" in texto and "valor-P3-2" in texto
    assert "Tomas" not in texto, "la tarea que no esta en la OT no va en el acta"
    assert texto.index("a.jpg") > texto.index("3.2 Caja"), "la foto va con su activo"
    assert "Foto adjunta" in texto and "X-Amz-Signature" not in texto
