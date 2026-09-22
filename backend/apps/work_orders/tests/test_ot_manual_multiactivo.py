"""Fase 4: alta manual de una OT con varios activos, y fin de la compatibilidad.

El alta de un correctivo deja de ser "un activo con un checklist" y pasa a ser
una visita a un hospital con una tarea por activo, cada una con su checklist.
La API ya no devuelve el activo, la version ni el plan de la primera tarea.
"""

from datetime import date

import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from apps.assets.models import Asset, AssetNode, Hospital
from apps.checklists.models import (
    ChecklistField,
    ChecklistFieldResponse,
    ChecklistTemplate,
    ChecklistTemplateVersion,
)
from apps.maintenance.models import Task
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
def piso(hospital):
    return baker.make(AssetNode, hospital=hospital, name="Piso 3", parent=None)


@pytest.fixture
def activos(hospital, piso):
    return [
        baker.make(Asset, hospital=hospital, node=piso, status=Asset.Status.ACTIVE,
                   name=nombre, code=codigo)
        for nombre, codigo in (("Alarma", "P3-1"), ("Caja", "P3-2"))
    ]


@pytest.fixture
def version():
    plantilla = baker.make(ChecklistTemplate, name="Correctivo")
    v = baker.make(ChecklistTemplateVersion, template=plantilla, version_number=1,
                   is_current=True)
    baker.make(ChecklistField, version=v, label="Presion", field_type="NUMBER",
               is_required=True, sort_order=0)
    return v


def alta(activos, **extra):
    datos = {
        "tasks": [{"asset": str(a.id)} for a in activos],
        "task_type": WorkOrder.TaskType.CORRECTIVE,
        "title": "Fuga en el piso 3",
        "scheduled_date": str(date.today()),
    }
    datos.update(extra)
    return datos


# ── Alta manual con varios activos (#101) ─────────────────────────────────────

def test_una_ot_manual_cubre_varios_activos_de_una_ubicacion(activos, piso, admin, tec, version):
    datos = alta(activos, location=str(piso.id), assigned_to=str(tec.id))
    # El checklist es de cada activo: aqui solo el segundo lo lleva.
    datos["tasks"][1]["checklist_version"] = str(version.id)

    resp = cliente(admin).post(reverse("work-orders-list"), datos, format="json")

    assert resp.status_code == status.HTTP_201_CREATED, resp.data
    ot = WorkOrder.objects.get(pk=resp.data["id"])
    assert ot.location == piso and ot.hospital == activos[0].hospital
    tareas = list(ot.tasks.order_by("sort_order"))
    assert [t.asset for t in tareas] == activos
    assert [t.status for t in tareas] == [Task.Status.SCHEDULED] * 2
    assert tareas[0].checklist_version is None
    # El checklist nace con la OT (fase 3), tambien en el alta manual.
    assert tareas[1].checklist_version == version
    assert tareas[1].checklist_response.version == version
    assert [a["code"] for a in resp.data["assets"]] == ["P3-1", "P3-2"]
    assert resp.data["assets_count"] == 2


def test_el_alta_de_un_solo_activo_sigue_funcionando(activos, admin):
    resp = cliente(admin).post(
        reverse("work-orders-list"), alta(activos[:1]), format="json"
    )

    assert resp.status_code == status.HTTP_201_CREATED, resp.data
    assert resp.data["assets_count"] == 1
    assert WorkOrder.objects.get(pk=resp.data["id"]).tasks.count() == 1


def test_una_ot_es_de_un_hospital(activos, admin):
    """Decision D4: una OT es una visita, y una visita es a un hospital."""
    otro = baker.make(Asset, hospital=baker.make(Hospital, is_active=True),
                      status=Asset.Status.ACTIVE)

    resp = cliente(admin).post(
        reverse("work-orders-list"), alta([activos[0], otro]), format="json"
    )

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "mismo hospital" in str(resp.data["tasks"])


def test_no_se_repite_un_activo(activos, admin):
    resp = cliente(admin).post(
        reverse("work-orders-list"), alta([activos[0], activos[0]]), format="json"
    )

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "P3-1" in str(resp.data["tasks"])


def test_la_ubicacion_es_del_mismo_hospital(activos, admin):
    ajena = baker.make(AssetNode, hospital=baker.make(Hospital, is_active=True),
                       name="Otro piso", parent=None)

    resp = cliente(admin).post(
        reverse("work-orders-list"), alta(activos, location=str(ajena.id)), format="json"
    )

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "otro hospital" in str(resp.data["location"])


def test_un_activo_fuera_de_servicio_se_rechaza(activos, admin):
    activos[1].status = Asset.Status.OUT_OF_SERVICE
    activos[1].save()

    resp = cliente(admin).post(reverse("work-orders-list"), alta(activos), format="json")

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "P3-2" in str(resp.data["tasks"])


def test_la_ot_necesita_al_menos_un_activo(admin):
    resp = cliente(admin).post(reverse("work-orders-list"), alta([]), format="json")

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "tasks" in resp.data


# ── Se acabo la compatibilidad de la primera tarea ───────────────────────────

def test_la_lista_trae_los_activos_y_no_el_primero(activos, admin):
    cliente(admin).post(reverse("work-orders-list"), alta(activos), format="json")

    fila = cliente(admin).get(reverse("work-orders-list")).data["results"][0]

    assert [a["code"] for a in fila["assets"]] == ["P3-1", "P3-2"]
    assert fila["assets_count"] == 2
    assert "asset" not in fila


def test_una_tarea_anulada_no_cuenta_como_activo(activos, admin):
    ot_id = cliente(admin).post(
        reverse("work-orders-list"), alta(activos), format="json"
    ).data["id"]
    ot = WorkOrder.objects.get(pk=ot_id)
    ot.tasks.filter(asset=activos[1]).update(status=Task.Status.CANCELLED)

    detalle = cliente(admin).get(reverse("work-orders-detail", kwargs={"pk": ot_id})).data

    assert [a["code"] for a in detalle["assets"]] == ["P3-1"]
    assert detalle["assets_count"] == 1


# ── El checklist se cambia en la tarea, no en la OT ──────────────────────────

def test_cambiar_el_checklist_de_una_tarea(activos, admin, version):
    ot_id = cliente(admin).post(
        reverse("work-orders-list"), alta(activos), format="json"
    ).data["id"]
    tarea = WorkOrder.objects.get(pk=ot_id).tasks.first()

    resp = cliente(admin).post(
        reverse("work-orders-task-checklist", kwargs={"pk": ot_id}),
        {"task": str(tarea.id), "checklist_version": str(version.id)}, format="json",
    )

    assert resp.status_code == status.HTTP_200_OK, resp.data
    tarea.refresh_from_db()
    assert tarea.checklist_version == version
    assert tarea.checklist_response.version == version


def test_no_se_cambia_el_checklist_ya_respondido(activos, admin, version):
    ot_id = cliente(admin).post(
        reverse("work-orders-list"), alta(activos), format="json"
    ).data["id"]
    tarea = WorkOrder.objects.get(pk=ot_id).tasks.first()
    c = cliente(admin)
    url = reverse("work-orders-task-checklist", kwargs={"pk": ot_id})
    c.post(url, {"task": str(tarea.id), "checklist_version": str(version.id)}, format="json")
    tarea.refresh_from_db()
    ChecklistFieldResponse.objects.create(
        response=tarea.checklist_response, field=version.fields.first(), value="3"
    )

    otra = baker.make(ChecklistTemplateVersion, template=version.template, version_number=2)
    resp = c.post(url, {"task": str(tarea.id), "checklist_version": str(otra.id)}, format="json")

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "ya se empezó" in str(resp.data["checklist_version"])


def test_la_tarea_tiene_que_ser_de_la_ot(activos, admin, version):
    primera = cliente(admin).post(
        reverse("work-orders-list"), alta(activos[:1]), format="json"
    ).data["id"]
    segunda = cliente(admin).post(
        reverse("work-orders-list"), alta(activos[1:]), format="json"
    ).data["id"]
    ajena = WorkOrder.objects.get(pk=segunda).tasks.first()

    resp = cliente(admin).post(
        reverse("work-orders-task-checklist", kwargs={"pk": primera}),
        {"task": str(ajena.id), "checklist_version": str(version.id)}, format="json",
    )

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "no es de esta OT" in str(resp.data["task"])


def test_el_tecnico_no_cambia_el_checklist(activos, admin, tec, version):
    ot_id = cliente(admin).post(
        reverse("work-orders-list"), alta(activos, assigned_to=str(tec.id)), format="json"
    ).data["id"]
    tarea = WorkOrder.objects.get(pk=ot_id).tasks.first()

    resp = cliente(tec).post(
        reverse("work-orders-task-checklist", kwargs={"pk": ot_id}),
        {"task": str(tarea.id), "checklist_version": str(version.id)}, format="json",
    )

    assert resp.status_code == status.HTTP_403_FORBIDDEN
