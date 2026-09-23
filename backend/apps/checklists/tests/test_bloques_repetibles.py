"""Bloques repetibles del checklist (diseño aprobado el 2026-09-22).

El bloque "Toma" de preguntas se define una vez y el plan dice cuántas veces
va, como en Fracttal ("MANT. SALIDAS 20 TOMAS"), pero sin escribirlo a mano N
veces. El técnico ajusta la cantidad en campo y el administrador ve el aviso.
"""

import sys
import types
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.checklists.models import (
    ChecklistField,
    ChecklistFieldResponse,
    ChecklistTemplate,
    ChecklistTemplateVersion,
)
from apps.maintenance import services
from apps.maintenance.models import PlanTask, Task
from apps.maintenance.testing import make_plan
from apps.users.models import User
from apps.work_orders.integrity import compute_wo_content_hash
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
def plantilla():
    """Localización una vez, y el bloque Toma: cubículo y fuga (obligatoria)."""
    t = baker.make(ChecklistTemplate, name="Salidas de gas")
    v = baker.make(ChecklistTemplateVersion, template=t, version_number=1,
                   is_current=True, repeatable_groups=["Toma"])
    baker.make(ChecklistField, version=v, label="Localización", field_type="TEXT",
               group="", is_required=True, sort_order=0)
    baker.make(ChecklistField, version=v, label="Cubículo", field_type="TEXT",
               group="Toma", is_required=False, sort_order=1)
    baker.make(ChecklistField, version=v, label="¿Tiene fuga?", field_type="BOOLEAN",
               group="Toma", is_required=True, sort_order=2)
    return t


@pytest.fixture
def ot(plantilla, admin, tec):
    """OT de un activo con el plan de 3 tomas, en curso."""
    hospital = baker.make(Hospital, is_active=True)
    activo = baker.make(Asset, hospital=hospital, status=Asset.Status.ACTIVE, code="SAL-3")
    plan = make_plan("MANT. SALIDAS 3 TOMAS", assets=[activo],
                     checklist_template=plantilla, next_due_date=date.today())
    PlanTask.objects.filter(plan=plan).update(block_counts={"Toma": 3})
    tarea = Task.objects.get(plan_task__plan=plan, status=Task.Status.PENDING)
    orden, _ = services.create_work_order_for_tasks([tarea], admin, assigned_to=tec)
    orden.status = WorkOrder.Status.IN_PROGRESS
    orden.save()
    return orden


def respuesta_de(ot):
    return ot.tasks.get().checklist_response


def campo(ot, label):
    return respuesta_de(ot).version.fields.get(label=label)


def responder(c, respuesta, field, value, repetition=0):
    return c.post(
        reverse("checklist-responses-submit-field", kwargs={"pk": respuesta.id}),
        {"field": str(field.id), "value": value, "repetition": repetition}, format="json",
    )


def llenar_todo(c, ot, tomas=3):
    r = respuesta_de(ot)
    responder(c, r, campo(ot, "Localización"), "Piso 3")
    for n in range(1, tomas + 1):
        responder(c, r, campo(ot, "Cubículo"), f"Cub {n}", n)
        responder(c, r, campo(ot, "¿Tiene fuga?"), "false", n)


# ── Editor: el bloque se define una vez ───────────────────────────────────────

def test_publicar_una_version_con_un_grupo_repetible(admin):
    t = baker.make(ChecklistTemplate, name="Tomas")
    resp = cliente(admin).post(
        reverse("checklist-templates-publish-version", kwargs={"pk": t.id}),
        {
            "checklist_fields": [
                {"label": "Cubículo", "field_type": "TEXT", "group": "Toma", "sort_order": 0},
                {"label": "Fuga", "field_type": "BOOLEAN", "group": "Toma", "sort_order": 1},
            ],
            "repeatable_groups": ["Toma"],
        },
        format="json",
    )

    assert resp.status_code == status.HTTP_201_CREATED, resp.data
    assert resp.data["repeatable_groups"] == ["Toma"]
    lista = cliente(admin).get(reverse("checklist-templates-list")).data
    fila = next(p for p in (lista.get("results", lista)) if p["id"] == str(t.id))
    assert fila["current_repeatable_groups"] == ["Toma"]


def test_no_se_repite_un_grupo_sin_campos(admin):
    t = baker.make(ChecklistTemplate, name="Tomas")
    resp = cliente(admin).post(
        reverse("checklist-templates-publish-version", kwargs={"pk": t.id}),
        {
            "checklist_fields": [{"label": "Fuga", "field_type": "BOOLEAN", "group": "Toma"}],
            "repeatable_groups": ["Salida"],
        },
        format="json",
    )

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Salida" in str(resp.data["repeatable_groups"])


# ── La cantidad viene del plan ────────────────────────────────────────────────

def test_el_checklist_nace_con_la_cantidad_del_plan(ot):
    r = respuesta_de(ot)

    assert r.block_counts == {"Toma": 3}
    assert r.planned_block_counts == {"Toma": 3}


def test_cambiar_el_plan_despues_no_toca_la_ot_armada(ot):
    PlanTask.objects.update(block_counts={"Toma": 20})

    assert respuesta_de(ot).block_counts == {"Toma": 3}


def test_un_correctivo_sin_plan_arranca_con_una(plantilla, admin):
    activo = baker.make(Asset, hospital=baker.make(Hospital, is_active=True),
                        status=Asset.Status.ACTIVE)
    version = plantilla.versions.get()

    orden = services.create_manual_work_order(
        [(activo, version)], admin, task_type="CORRECTIVE", title="Fuga",
        scheduled_date=date.today(),
    )

    assert orden.tasks.get().checklist_response.block_counts == {"Toma": 1}


def test_el_plan_valida_las_cantidades(admin, plantilla):
    plan = make_plan("Salidas", checklist_template=plantilla)
    tarea = plan.tasks.get()
    url = reverse("plan-tasks-detail", kwargs={"pk": tarea.id})

    malo = cliente(admin).patch(url, {"block_counts": {"Toma": 0}}, format="json")
    bueno = cliente(admin).patch(url, {"block_counts": {"Toma": "20"}}, format="json")

    assert malo.status_code == status.HTTP_400_BAD_REQUEST
    assert bueno.status_code == status.HTTP_200_OK, bueno.data
    assert bueno.data["block_counts"] == {"Toma": 20}


# ── Responder por toma ────────────────────────────────────────────────────────

def test_el_mismo_campo_se_responde_una_vez_por_toma(ot, tec):
    c, r = cliente(tec), respuesta_de(ot)

    for n in (1, 2, 3):
        resp = responder(c, r, campo(ot, "Cubículo"), f"Cub {n}", n)
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["repetition"] == n

    valores = dict(
        ChecklistFieldResponse.objects.filter(response=r).values_list("repetition", "value")
    )
    assert valores == {1: "Cub 1", 2: "Cub 2", 3: "Cub 3"}


def test_una_toma_fuera_de_la_cantidad_se_rechaza(ot, tec):
    c, r = cliente(tec), respuesta_de(ot)

    cuarta = responder(c, r, campo(ot, "Cubículo"), "Cub 4", 4)
    sin_toma = responder(c, r, campo(ot, "Cubículo"), "Cub", 0)
    fijo_con_toma = responder(c, r, campo(ot, "Localización"), "Piso 3", 1)

    assert cuarta.status_code == status.HTTP_400_BAD_REQUEST
    assert "1 a 3" in str(cuarta.data["repetition"])
    assert sin_toma.status_code == status.HTTP_400_BAD_REQUEST
    assert fijo_con_toma.status_code == status.HTTP_400_BAD_REQUEST


def test_el_avance_cuenta_cada_toma(ot, admin, tec):
    c, r = cliente(tec), respuesta_de(ot)
    responder(c, r, campo(ot, "Localización"), "Piso 3")
    responder(c, r, campo(ot, "¿Tiene fuga?"), "false", 1)

    avance = cliente(admin).get(
        reverse("work-orders-detail", kwargs={"pk": ot.id})
    ).data["tasks"][0]["checklist"]

    # 1 fijo + 3 tomas x 2 preguntas; faltan 2 fugas obligatorias.
    assert (avance["answered"], avance["total"], avance["required_missing"]) == (2, 7, 2)


def test_el_obligatorio_lo_es_en_cada_toma(ot, tec):
    """En Fracttal solo la primera toma tenía obligatorios."""
    c, r = cliente(tec), respuesta_de(ot)
    responder(c, r, campo(ot, "Localización"), "Piso 3")
    responder(c, r, campo(ot, "¿Tiene fuga?"), "false", 1)
    responder(c, r, campo(ot, "¿Tiene fuga?"), "false", 3)

    incompleto = c.post(reverse("checklist-responses-complete", kwargs={"pk": r.id}))
    responder(c, r, campo(ot, "¿Tiene fuga?"), "true", 2)
    completo = c.post(reverse("checklist-responses-complete", kwargs={"pk": r.id}))

    assert incompleto.status_code == status.HTTP_400_BAD_REQUEST
    assert "Toma 2: ¿Tiene fuga?" in incompleto.data["detail"]
    assert completo.status_code == status.HTTP_200_OK, completo.data


# ── En campo hay otra cantidad: se ajusta y se avisa ─────────────────────────

def test_el_tecnico_encuentra_una_toma_mas_y_se_avisa(ot, admin, tec):
    c, r = cliente(tec), respuesta_de(ot)

    resp = c.post(reverse("checklist-responses-block-count", kwargs={"pk": r.id}),
                  {"group": "Toma", "count": 4}, format="json")
    cuarta = responder(c, r, campo(ot, "Cubículo"), "Cub 4", 4)

    assert resp.status_code == status.HTTP_200_OK, resp.data
    assert resp.data["block_counts"] == {"Toma": 4}
    assert resp.data["planned_block_counts"] == {"Toma": 3}
    assert cuarta.status_code == status.HTTP_200_OK
    avance = cliente(admin).get(
        reverse("work-orders-detail", kwargs={"pk": ot.id})
    ).data["tasks"][0]["checklist"]
    assert avance["block_changes"] == [{"group": "Toma", "planned": 3, "count": 4}]


def test_no_se_quita_una_toma_con_respuestas(ot, tec):
    c, r = cliente(tec), respuesta_de(ot)
    responder(c, r, campo(ot, "Cubículo"), "Cub 3", 3)
    url = reverse("checklist-responses-block-count", kwargs={"pk": r.id})

    quitar_la_tercera = c.post(url, {"group": "Toma", "count": 2}, format="json")
    grupo_que_no_se_repite = c.post(url, {"group": "", "count": 2}, format="json")
    cero = c.post(url, {"group": "Toma", "count": 0}, format="json")

    assert quitar_la_tercera.status_code == status.HTTP_400_BAD_REQUEST
    assert "3 tiene respuestas" in str(quitar_la_tercera.data["count"])
    assert grupo_que_no_se_repite.status_code == status.HTTP_400_BAD_REQUEST
    assert cero.status_code == status.HTTP_400_BAD_REQUEST


# ── Integridad y acta ────────────────────────────────────────────────────────

def test_intercambiar_valores_entre_tomas_cambia_el_hash(ot, tec):
    """
    La v3 identifica cada respuesta por campo y toma. La v2 las ordena solo por
    campo, y entre tomas de un mismo campo queda el orden que devuelva la base.
    """
    llenar_todo(cliente(tec), ot)
    antes_v3 = compute_wo_content_hash(ot, "3")

    r = respuesta_de(ot)
    uno = ChecklistFieldResponse.objects.get(response=r, field__label="Cubículo", repetition=1)
    dos = ChecklistFieldResponse.objects.get(response=r, field__label="Cubículo", repetition=2)
    uno.value, dos.value = dos.value, uno.value
    uno.save()
    dos.save()

    assert compute_wo_content_hash(ot, "3") != antes_v3


def test_el_acta_imprime_el_bloque_como_tabla(ot, tec):
    from apps.reports.generator import generate_service_report_pdf

    llenar_todo(cliente(tec), ot)
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
    assert "Toma &times; 3" in texto
    assert '<table class="repeated">' in texto
    # Una fila por toma, en orden.
    assert texto.index("Cub 1") < texto.index("Cub 2") < texto.index("Cub 3")
    assert texto.count("<th>Cubículo</th>") == 1, "la pregunta es columna, no fila repetida"
