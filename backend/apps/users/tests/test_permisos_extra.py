"""
Permisos extra por usuario (primer audio del cliente, 10:18: "que un tecnico
pueda tener mas permisos").

El rol sigue siendo la base; el administrador marca casillas que SOLO suman y
que no amplian el alcance por hospital. Una cuenta de hospital nunca recibe.
"""

import uuid
from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient

from apps.evidence.tests.firmas import firmar
from apps.assets.models import Asset, Hospital
from apps.audit.models import AuditLog
from apps.checklists.models import ChecklistField, ChecklistTemplate, ChecklistTemplateVersion
from apps.users import permisos
from apps.users.models import User
from apps.users.permisos import PermisoExtra
from apps.work_orders.models import WorkOrder

# Helpers de una prueba hermana: ejecutar una OT de punta a punta.
from apps.work_orders.tests.test_admin_ejecuta_y_corrige import (  # noqa: F401
    crear_ot,
    ejecutar,
    transicion,
)

pytestmark = pytest.mark.django_db


def client_for(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def make_user(role, **kwargs):
    return User.objects.create_user(
        email=f"{uuid.uuid4()}@todogas.test", password="x",
        first_name="Zz", last_name=role.title(), role=role, **kwargs,
    )


def dar(user, *codigos, por=None):
    """Otorga y devuelve el usuario recargado (sin cache de permisos)."""
    for c in codigos:
        permisos.otorgar(user, c, por=por or make_user(User.Role.ADMIN))
    return User.objects.get(pk=user.pk)


@pytest.fixture
def d():
    admin = make_user(User.Role.ADMIN)
    h = Hospital.objects.create(name="Clinica", code=uuid.uuid4().hex[:8])
    otro = Hospital.objects.create(name="Otra", code=uuid.uuid4().hex[:8])
    activo = Asset.objects.create(hospital=h, name="Alarma", code=uuid.uuid4().hex[:8])
    activo_otro = Asset.objects.create(hospital=otro, name="Alarma 2", code=uuid.uuid4().hex[:8])
    t = ChecklistTemplate.objects.create(name=f"Alarma {uuid.uuid4().hex[:6]}")
    v = ChecklistTemplateVersion.objects.create(template=t, version_number=1, published_by=admin, is_current=True)
    campo = ChecklistField.objects.create(
        version=v, label="Presión (PSI)", field_type=ChecklistField.FieldType.NUMBER,
        is_required=True, sort_order=1,
    )
    return {"admin": admin, "h": h, "otro": otro, "activo": activo, "activo_otro": activo_otro,
            "version": v, "campo": campo}


# ── Catalogo y defaults por rol ──────────────────────────────────────────────

CODIGOS = {
    "ot.crear_manual", "ot.crear_desde_pendientes", "ot.asignar", "ot.revisar", "ot.cancelar",
    "tareas.planificar", "protocolos.gestionar", "checklists.gestionar", "activos.gestionar",
    "contratos.gestionar", "hallazgos.decidir", "inventario.articulos", "inventario.movimientos",
    "reportes.ver",
}

# Lo que el supervisor puede hacer HOY en el servidor. Si esta lista cambia hay
# una regresion (o una decision nueva que debe quedar por escrito).
SUP_HOY = {
    "ot.crear_desde_pendientes", "ot.asignar", "ot.revisar", "tareas.planificar",
    "checklists.gestionar", "activos.gestionar", "hallazgos.decidir",
    "inventario.movimientos", "reportes.ver",
}


def test_catalogo_fijo_con_nombre_y_descripcion():
    assert {p.codigo for p in permisos.CATALOGO} == CODIGOS
    for p in permisos.CATALOGO:
        assert p.nombre and p.descripcion and p.area


def test_admin_tiene_todos_cli_ninguno():
    assert permisos.permisos_del_rol(User.Role.ADMIN) == CODIGOS
    assert permisos.permisos_del_rol(User.Role.CLI) == set()


def test_supervisor_conserva_lo_que_puede_hoy():
    assert permisos.permisos_del_rol(User.Role.SUP) == SUP_HOY


def test_tecnico_no_trae_permisos_de_gestion():
    assert permisos.permisos_del_rol(User.Role.TEC) == set()


def test_puede_suma_rol_y_extra():
    tec = make_user(User.Role.TEC)
    assert not permisos.puede(tec, "ot.revisar")
    tec = dar(tec, "ot.revisar")
    assert permisos.puede(tec, "ot.revisar")
    assert not permisos.puede(tec, "ot.cancelar")
    assert permisos.puede(make_user(User.Role.SUP), "ot.revisar")


def test_cli_nunca_puede_ni_con_una_fila_en_la_base():
    cli = make_user(User.Role.CLI, hospital=Hospital.objects.create(name="H", code="h1"))
    with pytest.raises(ValueError):
        permisos.otorgar(cli, "ot.revisar", por=make_user(User.Role.ADMIN))
    # Aunque alguien la insertara a mano, la funcion central la ignora.
    PermisoExtra.objects.create(user=cli, codigo="ot.revisar")
    assert permisos.permisos_efectivos(User.objects.get(pk=cli.pk)) == set()


def test_codigo_desconocido_se_rechaza():
    with pytest.raises(ValueError):
        permisos.otorgar(make_user(User.Role.TEC), "inventada", por=make_user(User.Role.ADMIN))


# ── Tecnico con "aprobar" ────────────────────────────────────────────────────

def _ot_en_revision(d, tecnico):
    wo_id = crear_ot(d, tecnico)
    ejecutar(client_for(tecnico), wo_id, d["campo"])
    return wo_id


def test_tecnico_con_revisar_aprueba_la_ot_de_otro(d):
    ejecuta = make_user(User.Role.TEC)
    wo_id = _ot_en_revision(d, ejecuta)
    revisor = dar(make_user(User.Role.TEC), "ot.revisar")
    firmar(revisor)
    r = transicion(client_for(revisor), wo_id, WorkOrder.Status.COMPLETED)
    assert r.status_code == 200, r.data
    assert WorkOrder.objects.get(pk=wo_id).status == WorkOrder.Status.COMPLETED


def test_tecnico_sin_revisar_no_aprueba_ni_ve_la_ot_de_otro(d):
    ejecuta = make_user(User.Role.TEC)
    wo_id = _ot_en_revision(d, ejecuta)
    otro_tec = make_user(User.Role.TEC)
    r = transicion(client_for(otro_tec), wo_id, WorkOrder.Status.COMPLETED)
    assert r.status_code == 404  # como hoy: no la ve
    # Y quien la ejecuto tampoco se la aprueba sin el permiso.
    r = transicion(client_for(ejecuta), wo_id, WorkOrder.Status.COMPLETED)
    assert r.status_code == 400
    assert WorkOrder.objects.get(pk=wo_id).status == WorkOrder.Status.IN_REVIEW


def test_revisar_extra_no_amplia_el_alcance_por_hospital(d):
    ejecuta = make_user(User.Role.TEC)
    wo_id = _ot_en_revision(d, ejecuta)  # OT del hospital `h`
    limitado_a_otro = dar(make_user(User.Role.TEC, hospital=d["otro"]), "ot.revisar")
    r = transicion(client_for(limitado_a_otro), wo_id, WorkOrder.Status.COMPLETED)
    assert r.status_code == 404
    assert WorkOrder.objects.get(pk=wo_id).status == WorkOrder.Status.IN_REVIEW
    # Su lista tampoco la trae.
    lista = client_for(limitado_a_otro).get("/api/work-orders/")
    assert str(wo_id) not in {x["id"] for x in lista.data["results"]}
    # El del hospital correcto si.
    del_hospital = dar(make_user(User.Role.TEC, hospital=d["h"]), "ot.revisar")
    firmar(del_hospital)
    r = transicion(client_for(del_hospital), wo_id, WorkOrder.Status.COMPLETED)
    assert r.status_code == 200, r.data


def test_tecnico_con_revisar_devuelve_la_ot_a_proceso(d):
    wo_id = _ot_en_revision(d, make_user(User.Role.TEC))
    revisor = dar(make_user(User.Role.TEC), "ot.revisar")
    r = transicion(client_for(revisor), wo_id, WorkOrder.Status.IN_PROGRESS)
    assert r.status_code == 200, r.data


# ── Tecnico con "crear OT" y otros permisos ──────────────────────────────────

def _payload_ot_manual(d):
    return {
        "tasks": [{"asset": str(d["activo"].id), "checklist_version": str(d["version"].id)}],
        "task_type": WorkOrder.TaskType.CORRECTIVE,
        "title": "Reporte",
        "priority": WorkOrder.Priority.MEDIUM,
        "scheduled_date": str(date.today() + timedelta(days=1)),
    }


def test_tecnico_con_crear_manual_crea_y_sin_el_no(d):
    tec = make_user(User.Role.TEC)
    r = client_for(tec).post("/api/work-orders/", _payload_ot_manual(d), format="json")
    assert r.status_code == 403
    tec = dar(tec, "ot.crear_manual")
    r = client_for(tec).post("/api/work-orders/", _payload_ot_manual(d), format="json")
    assert r.status_code == 201, r.data


def test_tecnico_con_crear_desde_pendientes_no_puede_crear_manual(d):
    tec = dar(make_user(User.Role.TEC), "ot.crear_desde_pendientes")
    r = client_for(tec).post("/api/work-orders/", _payload_ot_manual(d), format="json")
    assert r.status_code == 403


def test_supervisor_sigue_sin_crear_ot_manual(d):
    r = client_for(make_user(User.Role.SUP)).post("/api/work-orders/", _payload_ot_manual(d), format="json")
    assert r.status_code == 403


def test_tecnico_con_asignar_reasigna(d):
    ejecuta = make_user(User.Role.TEC)
    wo_id = crear_ot(d, ejecuta)
    otro = make_user(User.Role.TEC)
    c = client_for(make_user(User.Role.TEC))
    assert c.post(f"/api/work-orders/{wo_id}/assign/", {"assigned_to": str(otro.id)}, format="json").status_code in (403, 404)
    asignador = dar(make_user(User.Role.TEC), "ot.asignar")
    r = client_for(asignador).post(f"/api/work-orders/{wo_id}/assign/", {"assigned_to": str(otro.id)}, format="json")
    assert r.status_code == 200, r.data
    assert WorkOrder.objects.get(pk=wo_id).assigned_to_id == otro.id


def test_tecnico_con_cancelar_cancela_y_sin_el_no(d):
    wo_id = crear_ot(d, make_user(User.Role.TEC))
    sin = client_for(make_user(User.Role.TEC)).post(f"/api/work-orders/{wo_id}/cancel/", {"comment": "x"}, format="json")
    assert sin.status_code in (403, 404)
    con = dar(make_user(User.Role.TEC), "ot.cancelar")
    r = client_for(con).post(f"/api/work-orders/{wo_id}/cancel/", {"comment": "ya no"}, format="json")
    assert r.status_code == 200, r.data


def test_supervisor_no_cancela_como_hoy(d):
    wo_id = crear_ot(d, make_user(User.Role.TEC))
    r = client_for(make_user(User.Role.SUP)).post(f"/api/work-orders/{wo_id}/cancel/", {"comment": "x"}, format="json")
    assert r.status_code == 403


def test_tecnico_con_gestionar_checklists_crea_plantillas():
    tec = make_user(User.Role.TEC)
    assert client_for(tec).post("/api/checklists/templates/", {"name": "N1"}).status_code == 403
    tec = dar(tec, "checklists.gestionar")
    assert client_for(tec).post("/api/checklists/templates/", {"name": "N1"}).status_code == 201


def test_tecnico_con_movimientos_registra_entradas():
    from apps.inventory.models import InventoryItem

    item = InventoryItem.objects.create(name="Valvula", code="V1", current_stock=1, min_stock=0)
    body = {"item": str(item.id), "movement_type": "IN", "quantity": 5}
    tec = make_user(User.Role.TEC)
    assert client_for(tec).post("/api/inventory/movements/", body).status_code == 403
    tec = dar(tec, "inventario.movimientos")
    r = client_for(tec).post("/api/inventory/movements/", body)
    assert r.status_code == 201, r.data


def test_articulos_de_inventario_siguen_siendo_del_admin_y_se_pueden_dar():
    sup = make_user(User.Role.SUP)
    assert client_for(sup).post("/api/inventory/items/", {"name": "X", "code": "X1"}).status_code == 403
    sup = dar(sup, "inventario.articulos")
    assert client_for(sup).post("/api/inventory/items/", {"name": "X", "code": "X1"}).status_code == 201


def test_tecnico_con_reportes_ve_el_tablero_y_las_actas_de_su_alcance(d):
    tec = make_user(User.Role.TEC, hospital=d["h"])
    assert client_for(tec).get("/api/dashboard/").status_code == 403
    assert client_for(tec).get("/api/reports/").data["results"] == []
    tec = dar(tec, "reportes.ver")
    assert client_for(tec).get("/api/dashboard/").status_code == 200
    assert client_for(tec).get("/api/reports/").status_code == 200


def test_tecnico_con_protocolos_ve_y_crea_protocolos():
    tec = make_user(User.Role.TEC)
    assert client_for(tec).get("/api/maintenance/plans/").status_code == 403
    tec = dar(tec, "protocolos.gestionar")
    assert client_for(tec).get("/api/maintenance/plans/").status_code == 200


def test_tecnico_con_activos_edita_y_da_de_baja(d):
    tec = make_user(User.Role.TEC)
    url = f"/api/assets/{d['activo'].id}/"
    assert client_for(tec).patch(url, {"name": "Nuevo"}, format="json").status_code == 403
    tec = dar(tec, "activos.gestionar")
    assert client_for(tec).patch(url, {"name": "Nuevo"}, format="json").status_code == 200
    assert client_for(tec).post(f"{url}decommission/").status_code == 200


def test_tecnico_con_planificar_ve_pendientes():
    tec = make_user(User.Role.TEC)
    assert client_for(tec).get("/api/tasks/").status_code == 403
    assert client_for(dar(tec, "tareas.planificar")).get("/api/tasks/").status_code == 200


def test_tecnico_con_contratos_los_crea_y_sin_el_no(d):
    tec = make_user(User.Role.TEC)
    assert client_for(tec).post("/api/contracts/", {}, format="json").status_code == 403
    r = client_for(dar(tec, "contratos.gestionar")).post("/api/contracts/", {}, format="json")
    assert r.status_code == 400  # pasa el permiso; falta el contenido


def test_tecnico_con_hallazgos_ve_la_bandeja():
    tec = make_user(User.Role.TEC)
    assert client_for(tec).get("/api/findings/summary/").status_code == 403
    assert client_for(dar(tec, "hallazgos.decidir")).get("/api/findings/summary/").status_code == 200


# ── Supervisor: lo del servidor se mantiene (incoherencias con la UI) ────────

def test_supervisor_sigue_reasignando_al_editar_la_ot(d):
    wo_id = crear_ot(d, make_user(User.Role.TEC))
    otro = make_user(User.Role.TEC)
    r = client_for(make_user(User.Role.SUP)).patch(
        f"/api/work-orders/{wo_id}/", {"assigned_to": str(otro.id)}, format="json")
    assert r.status_code == 200, r.data


def test_editar_la_ot_cambiando_asignado_exige_asignar(d):
    wo_id = crear_ot(d, make_user(User.Role.TEC))
    otro = make_user(User.Role.TEC)
    # Un tecnico con "crear OT manual" edita la OT pero no reasigna por esa via.
    c = client_for(dar(make_user(User.Role.TEC), "ot.crear_manual"))
    r = c.patch(f"/api/work-orders/{wo_id}/", {"assigned_to": str(otro.id)}, format="json")
    assert r.status_code == 403
    assert WorkOrder.objects.get(pk=wo_id).assigned_to_id != otro.id


def test_supervisor_sigue_dando_de_baja_al_editar_el_activo(d):
    r = client_for(make_user(User.Role.SUP)).patch(
        f"/api/assets/{d['activo'].id}/", {"status": "DECOMMISSIONED"}, format="json")
    assert r.status_code == 200, r.data


# ── API de usuarios ──────────────────────────────────────────────────────────

def _nuevo(role="TEC", **extra):
    return {
        "email": f"{uuid.uuid4().hex[:8]}@todogas.test", "first_name": "A", "last_name": "B",
        "role": role, "password": "TestPass1!", **extra,
    }


def test_me_devuelve_los_permisos_efectivos():
    tec = dar(make_user(User.Role.TEC), "ot.revisar", "ot.cancelar")
    r = client_for(tec).get("/api/auth/me/")
    assert set(r.data["permisos"]) == {"ot.revisar", "ot.cancelar"}
    assert set(r.data["permisos_extra"]) == {"ot.revisar", "ot.cancelar"}
    sup = client_for(make_user(User.Role.SUP)).get("/api/auth/me/")
    assert set(sup.data["permisos"]) == SUP_HOY
    assert sup.data["permisos_extra"] == []
    adm = client_for(make_user(User.Role.ADMIN)).get("/api/auth/me/")
    assert set(adm.data["permisos"]) == CODIGOS
    cli = make_user(User.Role.CLI, hospital=Hospital.objects.create(name="H", code="h2"))
    assert client_for(cli).get("/api/auth/me/").data["permisos"] == []


def test_login_devuelve_los_permisos(api_client):
    make_user(User.Role.TEC)
    u = User.objects.create_user(email="x@todogas.test", password="TestPass1!", first_name="a",
                                 last_name="b", role=User.Role.TEC)
    dar(u, "ot.revisar")
    r = api_client.post("/api/auth/login/", {"email": "x@todogas.test", "password": "TestPass1!"}, format="json")
    assert r.status_code == 200
    assert r.data["user"]["permisos"] == ["ot.revisar"]


def test_admin_crea_usuario_con_permisos_extra():
    admin = make_user(User.Role.ADMIN)
    r = client_for(admin).post("/api/users/", _nuevo(permisos_extra=["ot.revisar"]), format="json")
    assert r.status_code == 201, r.data
    u = User.objects.get(email=r.data["email"]) if "email" in r.data else None
    assert u is not None
    assert set(permisos.permisos_efectivos(u)) == {"ot.revisar"}


def test_admin_edita_permisos_extra_y_quita():
    admin, tec = make_user(User.Role.ADMIN), make_user(User.Role.TEC)
    c = client_for(admin)
    r = c.patch(f"/api/users/{tec.id}/", {"permisos_extra": ["ot.revisar", "ot.cancelar"]}, format="json")
    assert r.status_code == 200, r.data
    assert set(r.data["permisos_extra"]) == {"ot.revisar", "ot.cancelar"}
    r = c.patch(f"/api/users/{tec.id}/", {"permisos_extra": ["ot.cancelar"]}, format="json")
    assert r.data["permisos_extra"] == ["ot.cancelar"]
    assert PermisoExtra.objects.filter(user=tec).count() == 1
    # Un PATCH que no menciona permisos no los toca.
    c.patch(f"/api/users/{tec.id}/", {"phone": "123"}, format="json")
    assert PermisoExtra.objects.filter(user=tec).count() == 1


def test_endpoint_de_permisos_del_usuario():
    admin, tec = make_user(User.Role.ADMIN), make_user(User.Role.TEC)
    c = client_for(admin)
    r = c.put(f"/api/users/{tec.id}/permissions/", {"permisos_extra": ["ot.revisar"]}, format="json")
    assert r.status_code == 200, r.data
    r = c.get(f"/api/users/{tec.id}/permissions/")
    assert r.data["permisos_extra"] == ["ot.revisar"]
    assert "ot.revisar" in r.data["permisos"]


def test_lo_que_ya_trae_el_rol_no_se_guarda_como_extra():
    admin, sup = make_user(User.Role.ADMIN), make_user(User.Role.SUP)
    r = client_for(admin).patch(
        f"/api/users/{sup.id}/", {"permisos_extra": ["ot.revisar", "ot.cancelar"]}, format="json")
    assert r.status_code == 200, r.data
    assert r.data["permisos_extra"] == ["ot.cancelar"]


def test_codigo_desconocido_da_400_en_la_api():
    admin, tec = make_user(User.Role.ADMIN), make_user(User.Role.TEC)
    r = client_for(admin).patch(f"/api/users/{tec.id}/", {"permisos_extra": ["inventada"]}, format="json")
    assert r.status_code == 400


def test_cli_no_puede_recibir_permisos_extra_en_el_servidor(d):
    admin = make_user(User.Role.ADMIN)
    c = client_for(admin)
    r = c.post("/api/users/", _nuevo("CLI", hospital=str(d["h"].id), permisos_extra=["ot.revisar"]), format="json")
    assert r.status_code == 400
    assert "permisos_extra" in r.data
    cli = make_user(User.Role.CLI, hospital=d["h"])
    r = c.patch(f"/api/users/{cli.id}/", {"permisos_extra": ["ot.revisar"]}, format="json")
    assert r.status_code == 400
    r = c.put(f"/api/users/{cli.id}/permissions/", {"permisos_extra": ["ot.revisar"]}, format="json")
    assert r.status_code == 400
    assert not PermisoExtra.objects.filter(user=cli).exists()
    # Vaciar la lista de una cuenta de hospital no es un error.
    assert c.patch(f"/api/users/{cli.id}/", {"permisos_extra": []}, format="json").status_code == 200


@pytest.mark.parametrize("rol", ["SUP", "TEC", "CLI"])
def test_solo_el_admin_edita_permisos(rol, d):
    quien = make_user(rol, hospital=d["h"]) if rol == "CLI" else make_user(rol)
    tec = make_user(User.Role.TEC)
    c = client_for(quien)
    assert c.patch(f"/api/users/{tec.id}/", {"permisos_extra": ["ot.revisar"]}, format="json").status_code == 403
    assert c.put(f"/api/users/{tec.id}/permissions/", {"permisos_extra": ["ot.revisar"]}, format="json").status_code == 403
    # Ni a si mismo.
    assert c.patch(f"/api/users/{quien.id}/", {"permisos_extra": ["ot.revisar"]}, format="json").status_code == 403
    assert not PermisoExtra.objects.exists()


def test_el_catalogo_lo_lee_solo_el_admin():
    r = client_for(make_user(User.Role.ADMIN)).get("/api/users/permissions-catalog/")
    assert r.status_code == 200
    assert {p["codigo"] for p in r.data} == CODIGOS
    fila = next(p for p in r.data if p["codigo"] == "ot.revisar")
    assert fila["nombre"] and fila["descripcion"] and fila["area"]
    assert set(fila["roles"]) == {"ADMIN", "SUP"}
    assert client_for(make_user(User.Role.SUP)).get("/api/users/permissions-catalog/").status_code == 403


# ── Auditoria ────────────────────────────────────────────────────────────────

def test_otorgar_y_quitar_quedan_en_la_auditoria():
    admin, tec = make_user(User.Role.ADMIN), make_user(User.Role.TEC)
    c = client_for(admin)
    c.patch(f"/api/users/{tec.id}/", {"permisos_extra": ["ot.revisar"]}, format="json")
    c.patch(f"/api/users/{tec.id}/", {"permisos_extra": ["ot.cancelar"]}, format="json")
    filas = [
        f for f in AuditLog.objects.filter(entity_type="User", entity_id=tec.id, user=admin)
        if "permisos_extra" in f.changes
    ]
    assert len(filas) == 2
    primera, segunda = sorted(filas, key=lambda f: f.timestamp)
    assert primera.changes["permisos_extra"] == {"otorgados": ["ot.revisar"], "quitados": []}
    assert segunda.changes["permisos_extra"] == {"otorgados": ["ot.cancelar"], "quitados": ["ot.revisar"]}
    assert primera.action == AuditLog.Action.UPDATE


def test_sin_cambios_no_audita_de_mas():
    admin, tec = make_user(User.Role.ADMIN), make_user(User.Role.TEC)
    c = client_for(admin)
    c.patch(f"/api/users/{tec.id}/", {"permisos_extra": ["ot.revisar"]}, format="json")
    antes = AuditLog.objects.filter(entity_id=tec.id, changes__has_key="permisos_extra").count()
    c.patch(f"/api/users/{tec.id}/", {"permisos_extra": ["ot.revisar"]}, format="json")
    assert AuditLog.objects.filter(entity_id=tec.id, changes__has_key="permisos_extra").count() == antes


def test_registra_quien_otorgo_y_cuando():
    admin, tec = make_user(User.Role.ADMIN), make_user(User.Role.TEC)
    client_for(admin).patch(f"/api/users/{tec.id}/", {"permisos_extra": ["ot.revisar"]}, format="json")
    fila = PermisoExtra.objects.get(user=tec)
    assert fila.otorgado_por_id == admin.id and fila.otorgado_en is not None
    assert isinstance(fila.pk, uuid.UUID)


def test_quien_asigna_ve_la_lista_de_usuarios_para_elegir_ejecutor():
    tec = make_user(User.Role.TEC)
    assert client_for(tec).get("/api/users/").status_code == 403
    assert client_for(dar(tec, "ot.asignar")).get("/api/users/").status_code == 200
    # Como hoy: admin y supervisor, pero no pueden editar.
    assert client_for(make_user(User.Role.SUP)).get("/api/users/").status_code == 200
