"""
Alcance por hospital y parte del arbol (#117, decision del 2026-09-23).

Como "Limitar acceso a esta localizacion" de Fracttal: la biomedica de una
clinica ve lo suyo, y lo mismo un supervisor limitado a una sede. Todas las
vistas pasan por apps.users.scope.
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from model_bakery import baker
from rest_framework.test import APIClient

from apps.assets.models import Asset, AssetNode, Hospital
from apps.checklists.models import ChecklistField, ChecklistTemplate, ChecklistTemplateVersion
from apps.maintenance import services
from apps.maintenance.models import RescheduleCause, Task
from apps.maintenance.testing import make_plan
from apps.users.models import User
from apps.work_orders.models import WorkOrder

pytestmark = pytest.mark.django_db
HOY = timezone.localdate()


def cliente(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def ids(respuesta):
    datos = respuesta.data
    filas = datos["results"] if isinstance(datos, dict) and "results" in datos else datos
    return {str(f["id"]) for f in filas}


@pytest.fixture
def mundo():
    """
    Clinica A con dos pisos (Urgencias bajo Piso 1, y Piso 2) y clinica B,
    un activo en cada sitio, y una OT finalizada y una en curso por activo.
    """
    a = baker.make(Hospital, is_active=True, name="Clinica A")
    b = baker.make(Hospital, is_active=True, name="Clinica B")
    piso1 = AssetNode.objects.create(hospital=a, name="Piso 1")
    urg = AssetNode.objects.create(hospital=a, name="Urgencias", parent=piso1)
    piso2 = AssetNode.objects.create(hospital=a, name="Piso 2")
    admin = baker.make(User, role=User.Role.ADMIN, is_active=True)
    t = baker.make(ChecklistTemplate, name="T")
    v = baker.make(ChecklistTemplateVersion, template=t, version_number=1, is_current=True)
    baker.make(ChecklistField, version=v, label="X", field_type="TEXT", group="", sort_order=0)

    activos = {
        "urg": Asset.objects.create(hospital=a, node=urg, name="Toma urg", code="A-URG",
                                    status=Asset.Status.ACTIVE),
        "piso2": Asset.objects.create(hospital=a, node=piso2, name="Toma p2", code="A-P2",
                                      status=Asset.Status.ACTIVE),
        "b": Asset.objects.create(hospital=b, name="Toma B", code="B-1",
                                  status=Asset.Status.ACTIVE),
    }
    plan = make_plan("P", assets=list(activos.values()), checklist_template=t,
                     next_due_date=HOY)
    ots = {}
    for clave, activo in activos.items():
        tarea = Task.objects.get(plan_task__plan=plan, asset=activo, status=Task.Status.PENDING)
        ot, _ = services.create_work_order_for_tasks([tarea], admin)
        WorkOrder.objects.filter(pk=ot.pk).update(status=WorkOrder.Status.COMPLETED,
                                                  completed_at=timezone.now())
        ots[clave] = ot
    return {"a": a, "b": b, "piso1": piso1, "urg": urg, "piso2": piso2, "admin": admin,
            "activos": activos, "ots": ots, "plan": plan, "version": v}


def pendiente(mundo, clave):
    """Una tarea pendiente del activo `clave` (su propio plan)."""
    plan = make_plan(f"P-{clave}-{Task.objects.count()}", assets=[mundo["activos"][clave]],
                     checklist_template=mundo["version"].template, next_due_date=HOY)
    return Task.objects.get(plan_task__plan=plan, status=Task.Status.PENDING)


def pendiente_b(mundo):
    return pendiente(mundo, "b")


def biomedica(mundo, nodo=None):
    return baker.make(User, role=User.Role.CLI, is_active=True, hospital=mundo["a"],
                      scope_node=nodo)


# ── El hueco del checklist ───────────────────────────────────────────────────

def test_el_cliente_no_ve_ni_escribe_checklists_de_otro_hospital(mundo):
    """Regresion: submit-field le respondia 200 a un cliente sobre otro hospital."""
    ot, _ = services.create_work_order_for_tasks([pendiente_b(mundo)], mundo["admin"])
    WorkOrder.objects.filter(pk=ot.pk).update(status=WorkOrder.Status.IN_PROGRESS)
    r = ot.tasks.get().checklist_response
    c = cliente(biomedica(mundo))

    assert str(r.id) not in ids(c.get("/api/checklists/responses/"))
    assert c.get(f"/api/checklists/responses/{r.id}/").status_code == 404
    campo = mundo["version"].fields.get()
    escribir = c.post(f"/api/checklists/responses/{r.id}/submit-field/",
                      {"field": str(campo.id), "value": "hack"}, format="json")
    assert escribir.status_code == 403
    assert not r.field_responses.exists()


def test_el_cliente_ve_el_checklist_de_sus_ots_finalizadas(mundo):
    c = cliente(biomedica(mundo))
    visibles = ids(c.get("/api/checklists/responses/"))
    propio = mundo["ots"]["urg"].tasks.get().checklist_response
    ajeno = mundo["ots"]["b"].tasks.get().checklist_response
    assert str(propio.id) in visibles
    assert str(ajeno.id) not in visibles


def test_el_cliente_no_ve_el_catalogo_de_plantillas(mundo):
    assert cliente(biomedica(mundo)).get("/api/checklists/templates/").status_code == 403


# ── Cuenta de hospital ───────────────────────────────────────────────────────

def test_la_biomedica_ve_su_hospital_completo(mundo):
    c = cliente(biomedica(mundo))
    activos = ids(c.get("/api/assets/"))
    assert activos == {str(mundo["activos"]["urg"].id), str(mundo["activos"]["piso2"].id)}
    ots = ids(c.get("/api/work-orders/"))
    assert str(mundo["ots"]["b"].id) not in ots
    assert str(mundo["ots"]["piso2"].id) in ots


def test_limitada_a_un_piso_ve_ese_piso_y_lo_que_cuelga(mundo):
    """Limitada a Piso 1 ve Urgencias, que esta debajo; no ve Piso 2."""
    c = cliente(biomedica(mundo, nodo=mundo["piso1"]))
    assert ids(c.get("/api/assets/")) == {str(mundo["activos"]["urg"].id)}
    ots = ids(c.get("/api/work-orders/"))
    assert ots == {str(mundo["ots"]["urg"].id)}
    assert c.get(f"/api/work-orders/{mundo['ots']['piso2'].id}/").status_code == 404
    resumen = c.get("/api/client-portal/summary/").data
    assert resumen["total_assets"] == 1


def test_una_cuenta_de_hospital_sin_hospital_no_ve_nada(mundo):
    """Mal creada, lo seguro es que no vea: no que vea todo."""
    c = cliente(baker.make(User, role=User.Role.CLI, is_active=True, hospital=None))
    assert ids(c.get("/api/assets/")) == set()
    assert ids(c.get("/api/work-orders/")) == set()


def test_el_cliente_no_ve_lo_que_esta_en_curso(mundo):
    WorkOrder.objects.filter(pk=mundo["ots"]["urg"].pk).update(status=WorkOrder.Status.IN_PROGRESS)
    assert str(mundo["ots"]["urg"].id) not in ids(cliente(biomedica(mundo)).get("/api/work-orders/"))


# ── Usuarios internos ────────────────────────────────────────────────────────

@pytest.fixture
def sup_a(mundo):
    return baker.make(User, role=User.Role.SUP, is_active=True, hospital=mundo["a"])


def test_el_supervisor_limitado_trabaja_solo_su_clinica(mundo, sup_a):
    c = cliente(sup_a)
    assert str(mundo["activos"]["b"].id) not in ids(c.get("/api/assets/"))
    assert str(mundo["ots"]["b"].id) not in ids(c.get("/api/work-orders/"))
    assert ids(c.get("/api/hospitals/")) == {str(mundo["a"].id)}
    propia, ajena = pendiente(mundo, "urg"), pendiente_b(mundo)
    tareas = ids(c.get("/api/tasks/", {"status": "PENDING"}))
    assert str(propia.id) in tareas
    assert str(ajena.id) not in tareas


def test_no_arma_una_ot_con_tareas_de_otra_clinica(mundo, sup_a):
    tarea_b = pendiente_b(mundo)
    r = cliente(sup_a).post("/api/work-orders/", {"task_ids": [str(tarea_b.id)]}, format="json")
    assert r.status_code == 400
    assert "task_ids" in r.data


def test_no_reprograma_tareas_de_otra_clinica(mundo, sup_a):
    tarea_b = pendiente_b(mundo)
    causa = RescheduleCause.objects.get(name="APLAZADO")
    r = cliente(sup_a).post("/api/tasks/reschedule/", {
        "task_ids": [str(tarea_b.id)], "scheduled_date": str(HOY + timedelta(days=5)),
        "cause_id": str(causa.id),
    }, format="json")
    assert r.status_code == 400


def test_no_crea_activos_en_otra_clinica(mundo, sup_a):
    r = cliente(sup_a).post("/api/assets/", {
        "hospital": str(mundo["b"].id), "name": "X", "code": "X-1",
    }, format="json")
    assert r.status_code == 400
    assert "hospital" in r.data


def test_limitado_a_un_piso_no_crea_en_la_raiz_del_hospital(mundo):
    sup = baker.make(User, role=User.Role.SUP, is_active=True, hospital=mundo["a"],
                     scope_node=mundo["piso1"])
    c = cliente(sup)
    raiz = c.post("/api/assets/", {"hospital": str(mundo["a"].id), "name": "X", "code": "X-2"},
                  format="json")
    assert raiz.status_code == 400
    dentro = c.post("/api/assets/", {"hospital": str(mundo["a"].id), "node": str(mundo["urg"].id),
                                     "name": "X", "code": "X-3"}, format="json")
    assert dentro.status_code == 201, dentro.data


def test_el_tablero_de_un_supervisor_limitado_es_el_de_su_clinica(mundo, sup_a):
    from apps.work_orders.views_dashboard import _hospital_del_tablero

    pedido = type("R", (), {"user": sup_a, "query_params": {"hospital_id": str(mundo["b"].id)}})
    assert _hospital_del_tablero(pedido) == str(mundo["a"].id)


def test_al_tecnico_limitado_no_se_le_esconde_lo_asignado(mundo):
    tec = baker.make(User, role=User.Role.TEC, is_active=True, hospital=mundo["a"])
    WorkOrder.objects.filter(pk=mundo["ots"]["b"].pk).update(assigned_to=tec)
    assert str(mundo["ots"]["b"].id) in ids(cliente(tec).get("/api/work-orders/"))


def test_el_administrador_nunca_queda_limitado(mundo):
    admin = baker.make(User, role=User.Role.ADMIN, is_active=True, hospital=mundo["a"])
    assert str(mundo["activos"]["b"].id) in ids(cliente(admin).get("/api/assets/"))


# ── Crear y editar usuarios ──────────────────────────────────────────────────

def nuevo(mundo, **datos):
    base = {"email": "x@h.co", "first_name": "A", "last_name": "B", "password": "Clave-Segura-2026!"}
    return cliente(mundo["admin"]).post("/api/users/", {**base, **datos}, format="json")


def test_una_cuenta_de_hospital_necesita_hospital(mundo):
    r = nuevo(mundo, role="CLI")
    assert r.status_code == 400
    assert "hospital" in r.data


def test_la_ubicacion_tiene_que_ser_del_mismo_hospital(mundo):
    otro = AssetNode.objects.create(hospital=mundo["b"], name="Piso B")
    r = nuevo(mundo, role="CLI", hospital=str(mundo["a"].id), scope_node=str(otro.id))
    assert r.status_code == 400
    assert "scope_node" in r.data


def test_se_crea_la_biomedica_de_urgencias(mundo):
    r = nuevo(mundo, role="CLI", hospital=str(mundo["a"].id), scope_node=str(mundo["urg"].id))
    assert r.status_code == 201, r.data
    u = User.objects.get(email="x@h.co")
    assert u.scope_node == mundo["urg"]


def test_cambiar_de_hospital_suelta_la_ubicacion_vieja(mundo):
    u = biomedica(mundo, nodo=mundo["piso1"])
    r = cliente(mundo["admin"]).patch(f"/api/users/{u.id}/", {"hospital": str(mundo["b"].id)},
                                      format="json")
    assert r.status_code == 200, r.data
    u.refresh_from_db()
    assert u.hospital == mundo["b"] and u.scope_node is None
