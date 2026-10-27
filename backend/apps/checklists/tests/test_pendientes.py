"""Corregir y dejar pendiente mientras la OT esta en curso (revision del 2026-10-23).

"Entre a un servicio de 10 cubiculos pero me quedo faltando el 7 porque estaba
aislado." El tecnico puede cambiar cualquier respuesta mientras la OT este en
curso (aunque ya haya cerrado el checklist) y marcar como pendiente, con su
motivo, un campo o un bloque repetible completo. Un pendiente cuenta como no
completo: la OT no pasa a revision hasta que se responda.
"""

from datetime import date

import pytest
from django.test import TestCase
from django.urls import reverse
from model_bakery import baker
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.checklists.models import ChecklistField, ChecklistTemplate, ChecklistTemplateVersion
from apps.maintenance import services
from apps.maintenance.models import PlanTask, Task
from apps.maintenance.testing import make_plan
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
def plantilla():
    t = baker.make(ChecklistTemplate, name="Cubiculos")
    v = baker.make(ChecklistTemplateVersion, template=t, version_number=1,
                   is_current=True, repeatable_groups=["Cubículo"])
    baker.make(ChecklistField, version=v, label="Localización", field_type="TEXT",
               group="", is_required=True, sort_order=0)
    baker.make(ChecklistField, version=v, label="Presión", field_type="NUMBER",
               group="Cubículo", is_required=True, sort_order=1)
    baker.make(ChecklistField, version=v, label="Observación", field_type="TEXT",
               group="Cubículo", is_required=False, sort_order=2)
    return t


@pytest.fixture
def ot(plantilla, admin, tec):
    hospital = baker.make(Hospital, is_active=True)
    activo = baker.make(Asset, hospital=hospital, status=Asset.Status.ACTIVE, code="CUB-1")
    plan = make_plan("MANT. 3 CUBICULOS", assets=[activo],
                     checklist_template=plantilla, next_due_date=date.today())
    PlanTask.objects.filter(plan=plan).update(block_counts={"Cubículo": 3})
    tarea = Task.objects.get(plan_task__plan=plan, status=Task.Status.PENDING)
    orden, _ = services.create_work_order_for_tasks([tarea], admin, assigned_to=tec)
    orden.status = WorkOrder.Status.IN_PROGRESS
    orden.save()
    return orden


def resp(ot):
    return ot.tasks.get().checklist_response


def campo(ot, label):
    return resp(ot).version.fields.get(label=label)


def responder(c, ot, label, valor, rep=0):
    return c.post(
        reverse("checklist-responses-submit-field", kwargs={"pk": resp(ot).id}),
        {"field": str(campo(ot, label).id), "value": valor, "repetition": rep}, format="json",
    )


def llenar_todo(c, ot):
    responder(c, ot, "Localización", "Piso 3")
    for n in (1, 2, 3):
        assert responder(c, ot, "Presión", "50", n).status_code == 200


def cerrar(c, ot):
    return c.post(reverse("checklist-responses-complete", kwargs={"pk": resp(ot).id}))


def pendientes(c, ot, lista):
    return c.post(
        reverse("checklist-responses-set-pending", kwargs={"pk": resp(ot).id}),
        {"pendientes": lista}, format="json",
    )


def bloque(n, motivo="aislado por aerosoles"):
    return {"field": None, "group": "Cubículo", "repetition": n, "reason": motivo}


def a_revision(c, ot):
    with TestCase.captureOnCommitCallbacks(execute=True):
        return c.post(
            reverse("work-orders-transition", kwargs={"pk": ot.id}),
            {"new_status": "IN_REVIEW"}, format="json",
        )


# ── Corregir mientras la OT esta en curso ─────────────────────────────────────

def test_se_corrige_una_respuesta_aunque_el_checklist_ya_este_cerrado(ot, tec):
    c = cliente(tec)
    llenar_todo(c, ot)
    assert cerrar(c, ot).status_code == 200
    assert resp(ot).completed_at is not None

    r = responder(c, ot, "Presión", "55", 2)
    assert r.status_code == 200, r.data
    assert r.data["value"] == "55"
    r2 = resp(ot)
    assert r2.completed_at is None, "al corregir se reabre: hay que volver a cerrarlo"
    assert r2.completed_by is None
    assert cerrar(c, ot).status_code == 200


def test_repetir_el_mismo_valor_no_reabre(ot, tec):
    c = cliente(tec)
    llenar_todo(c, ot)
    cerrar(c, ot)
    assert responder(c, ot, "Presión", "50", 2).status_code == 200
    assert resp(ot).completed_at is not None


def test_cambiar_la_cantidad_de_tomas_con_el_checklist_cerrado(ot, tec):
    c = cliente(tec)
    llenar_todo(c, ot)
    cerrar(c, ot)
    r = c.post(reverse("checklist-responses-block-count", kwargs={"pk": resp(ot).id}),
               {"group": "Cubículo", "count": 4}, format="json")
    assert r.status_code == 200, r.data
    assert resp(ot).completed_at is None


@pytest.mark.parametrize("estado", ["IN_REVIEW", "COMPLETED", "CANCELLED"])
def test_fuera_de_en_curso_no_se_edita(ot, tec, estado):
    c = cliente(tec)
    llenar_todo(c, ot)
    cerrar(c, ot)
    WorkOrder.objects.filter(pk=ot.pk).update(status=estado)
    r = responder(c, ot, "Presión", "99", 1)
    assert r.status_code == 400
    assert r.data["code"] == "ot_no_editable"
    r = c.post(reverse("checklist-responses-block-count", kwargs={"pk": resp(ot).id}),
               {"group": "Cubículo", "count": 5}, format="json")
    assert r.status_code == 400
    assert pendientes(c, ot, [bloque(1)]).status_code == 400
    assert resp(ot).field_responses.get(field=campo(ot, "Presión"), repetition=1).value == "50"


def test_la_correccion_de_revision_sigue_funcionando(ot, tec, admin):
    c = cliente(tec)
    llenar_todo(c, ot)
    cerrar(c, ot)
    WorkOrder.objects.filter(pk=ot.pk).update(status="IN_REVIEW")
    r = cliente(admin).post(
        reverse("checklist-responses-correct-field", kwargs={"pk": resp(ot).id}),
        {"field": str(campo(ot, "Presión").id), "value": "60", "repetition": 1}, format="json",
    )
    assert r.status_code == 200, r.data
    assert resp(ot).completed_at is not None, "corregir en revision no reabre"


def test_al_devolverla_de_revision_el_tecnico_vuelve_a_editar(ot, tec, admin):
    c = cliente(tec)
    llenar_todo(c, ot)
    cerrar(c, ot)
    WorkOrder.objects.filter(pk=ot.pk).update(status="IN_REVIEW")
    assert responder(c, ot, "Presión", "70", 1).status_code == 400

    r = cliente(admin).post(
        reverse("work-orders-transition", kwargs={"pk": ot.id}),
        {"new_status": "IN_PROGRESS", "comment": "revisar el 1"}, format="json",
    )
    assert r.status_code == 200, r.data
    assert responder(c, ot, "Presión", "70", 1).status_code == 200
    assert resp(ot).field_responses.get(field=campo(ot, "Presión"), repetition=1).value == "70"


# ── Pendientes con motivo ─────────────────────────────────────────────────────

def test_el_pendiente_exige_motivo(ot, tec):
    c = cliente(tec)
    for motivo in ("", "   "):
        assert pendientes(c, ot, [bloque(2, motivo)]).status_code == 400
    r = pendientes(c, ot, [{"field": None, "group": "Cubículo", "repetition": 2}])
    assert r.status_code == 400
    assert resp(ot).pendientes == []


def test_un_pendiente_de_bloque_se_guarda_y_se_lee(ot, tec):
    c = cliente(tec)
    r = pendientes(c, ot, [bloque(2)])
    assert r.status_code == 200, r.data
    assert r.data["pendientes"][0]["repetition"] == 2
    assert r.data["pendientes"][0]["text"] == "Cubículo 2: pendiente — aislado por aerosoles"
    assert resp(ot).pendientes[0]["marked_by"] == str(tec.id)
    leida = c.get(reverse("checklist-responses-detail", kwargs={"pk": resp(ot).id}))
    assert len(leida.data["pendientes"]) == 1


def test_un_pendiente_de_un_campo_suelto(ot, tec):
    c = cliente(tec)
    r = pendientes(c, ot, [{"field": str(campo(ot, "Localización").id), "repetition": 0,
                            "reason": "sin acceso al cuarto"}])
    assert r.status_code == 200, r.data
    assert r.data["pendientes"][0]["text"] == "Localización: pendiente — sin acceso al cuarto"


def test_pendiente_invalido_se_rechaza(ot, tec):
    c = cliente(tec)
    assert pendientes(c, ot, [bloque(9)]).status_code == 400  # solo hay 3
    assert pendientes(c, ot, [{"field": None, "group": "Otro", "repetition": 1, "reason": "x"}]).status_code == 400
    assert pendientes(c, ot, [{"field": str(campo(ot, "Localización").id), "repetition": 2,
                               "reason": "x"}]).status_code == 400


def test_con_pendientes_no_se_cierra_ni_se_envia_y_el_mensaje_los_nombra(ot, tec):
    c = cliente(tec)
    responder(c, ot, "Localización", "Piso 3")
    for n in (1, 3):
        responder(c, ot, "Presión", "50", n)
    assert pendientes(c, ot, [bloque(2)]).status_code == 200

    r = cerrar(c, ot)
    assert r.status_code == 400
    assert "Cubículo 2: pendiente — aislado por aerosoles" in r.data["detail"]

    r = a_revision(c, ot)
    assert r.status_code == 400
    assert "Cubículo 2: pendiente — aislado por aerosoles" in str(r.data)


def test_marcar_pendiente_en_un_checklist_cerrado_lo_reabre(ot, tec):
    c = cliente(tec)
    llenar_todo(c, ot)
    cerrar(c, ot)
    assert pendientes(c, ot, [bloque(3, "se fue la luz")]).status_code == 200
    assert resp(ot).completed_at is None


def test_responder_el_item_quita_el_pendiente(ot, tec):
    c = cliente(tec)
    responder(c, ot, "Localización", "Piso 3")
    pendientes(c, ot, [bloque(2), {"field": str(campo(ot, "Presión").id), "repetition": 1,
                                   "reason": "tapado"}])
    assert len(resp(ot).pendientes) == 2

    responder(c, ot, "Presión", "48", 1)  # el campo suelto
    assert [p["repetition"] for p in resp(ot).pendientes] == [2]
    responder(c, ot, "Presión", "51", 2)  # algo del bloque pendiente
    assert resp(ot).pendientes == []

    responder(c, ot, "Presión", "50", 3)
    assert cerrar(c, ot).status_code == 200


def test_reenviar_la_lista_reemplaza_y_conserva_quien_y_cuando(ot, tec):
    c = cliente(tec)
    pendientes(c, ot, [bloque(2)])
    marcado = resp(ot).pendientes[0]["marked_at"]
    r = pendientes(c, ot, [bloque(2), bloque(3, "otro motivo")])
    assert r.status_code == 200
    por_rep = {p["repetition"]: p for p in resp(ot).pendientes}
    assert por_rep[2]["marked_at"] == marcado
    assert por_rep[3]["reason"] == "otro motivo"
    pendientes(c, ot, [])
    assert resp(ot).pendientes == []


def test_un_pendiente_sobre_algo_ya_respondido_se_descarta(ot, tec):
    c = cliente(tec)
    responder(c, ot, "Presión", "50", 2)
    r = pendientes(c, ot, [{"field": str(campo(ot, "Presión").id), "repetition": 2, "reason": "x"}])
    assert r.status_code == 200
    assert resp(ot).pendientes == []


def test_el_detalle_de_la_ot_cuenta_y_nombra_los_pendientes(ot, tec):
    c = cliente(tec)
    pendientes(c, ot, [bloque(2)])
    d = c.get(reverse("work-orders-detail", kwargs={"pk": ot.id})).data
    chk = d["tasks"][0]["checklist"]
    assert chk["pending_count"] == 1
    assert chk["pending"] == ["Cubículo 2: pendiente — aislado por aerosoles"]
    assert d["pending_count"] == 1
    lista = c.get(reverse("work-orders-list")).data["results"]
    assert [o["pending_count"] for o in lista if o["id"] == str(ot.id)] == [1]


def test_solo_quien_ejecuta_marca_pendientes(ot):
    otro = baker.make(User, role=User.Role.TEC, is_active=True)
    r = pendientes(cliente(otro), ot, [bloque(1)])
    assert r.status_code in (403, 404)
    cli = baker.make(User, role=User.Role.CLI, is_active=True, hospital=ot.hospital)
    assert pendientes(cliente(cli), ot, [bloque(1)]).status_code == 403
