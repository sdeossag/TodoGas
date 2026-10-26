"""
Protocolo asignado a una ubicacion (revision del 2026-10-23, grab. 4 12:52):
instalaciones entrega obras por ubicacion, no por equipo.

La ubicacion recibe un activo que la representa; desde ahi tareas, OT y acta
funcionan igual que con un equipo, pero no aparece entre los equipos.
"""

import uuid

import pytest
from rest_framework.test import APIClient

from apps.assets.models import Asset, AssetNode, Hospital
from apps.maintenance import services
from apps.maintenance.models import MaintenancePlan, PlanTask, Task
from apps.users.models import User

pytestmark = pytest.mark.django_db


def _user(role, **extra):
    return User.objects.create_user(
        email=f"{uuid.uuid4()}@t.co", password="x", first_name="A", last_name="B", role=role, **extra,
    )


@pytest.fixture
def d():
    admin = _user(User.Role.ADMIN)
    h = Hospital.objects.create(name="Clinica Norte", code=uuid.uuid4().hex[:8])
    bloque = AssetNode.objects.create(hospital=h, name="Bloque A")
    piso = AssetNode.objects.create(hospital=h, parent=bloque, name="Piso 3")
    equipo = Asset.objects.create(hospital=h, node=piso, name="Alarma", code=uuid.uuid4().hex[:8])
    plan = MaintenancePlan.objects.create(name=f"ENTREGA OBRA {uuid.uuid4().hex[:4]}")
    PlanTask.objects.create(plan=plan, name="Entrega", frequency_value=6, frequency_unit="MONTHS")
    c = APIClient()
    c.force_authenticate(user=admin)
    return {"admin": admin, "h": h, "bloque": bloque, "piso": piso, "equipo": equipo, "plan": plan, "c": c}


def _asignar(d, *nodos, client=None):
    return (client or d["c"]).post(
        f"/api/maintenance/plans/{d['plan'].id}/assign-locations/",
        {"node_ids": [str(n.id) for n in nodos]}, format="json",
    )


def test_asignar_protocolo_a_una_ubicacion_crea_su_pendiente(d):
    r = _asignar(d, d["piso"])
    assert r.status_code == 200, r.data
    assert r.data["assigned"] == 1

    activo = Asset.objects.get(represents_node=d["piso"])
    assert activo.is_location and activo.name == "Piso 3"
    assert activo.node_id == d["piso"].id and activo.hospital_id == d["h"].id
    assert activo.plan_id == d["plan"].id
    assert Task.objects.filter(asset=activo, status=Task.Status.PENDING).count() == 1


def test_reasignar_no_duplica_el_activo_de_ubicacion(d):
    _asignar(d, d["piso"])
    r = _asignar(d, d["piso"])
    assert r.data["assigned"] == 0
    assert Asset.objects.filter(represents_node=d["piso"]).count() == 1


def test_la_ubicacion_no_sale_entre_los_equipos(d):
    _asignar(d, d["piso"])
    r = d["c"].get("/api/assets/", {"hospital_id": str(d["h"].id)})
    filas = r.data["results"] if isinstance(r.data, dict) else r.data
    assert [a["code"] for a in filas] == [d["equipo"].code]

    r = d["c"].get("/api/assets/", {"kind": "location"})
    filas = r.data["results"] if isinstance(r.data, dict) else r.data
    assert [a["name"] for a in filas] == ["Piso 3"]
    assert filas[0]["is_location"] is True

    # Los conteos del arbol y del hospital tampoco la cuentan.
    r = d["c"].get("/api/asset-nodes/", {"hospital_id": str(d["h"].id)})
    filas = r.data["results"] if isinstance(r.data, dict) else r.data
    piso = next(n for n in filas if n["id"] == str(d["piso"].id))
    assert piso["asset_count"] == 1


def test_el_protocolo_muestra_la_ubicacion_marcada(d):
    _asignar(d, d["piso"])
    services.set_asset_plan(d["equipo"], d["plan"])
    r = d["c"].get(f"/api/maintenance/plans/{d['plan'].id}/")
    marcas = {a["name"]: a["is_location"] for a in r.data["assets"]}
    assert marcas == {"Piso 3": True, "Alarma": False}


def test_la_ot_de_la_ubicacion_se_arma_y_cierra_como_la_de_un_equipo(d):
    _asignar(d, d["piso"])
    activo = Asset.objects.get(represents_node=d["piso"])
    tarea = Task.objects.get(asset=activo, status=Task.Status.PENDING)
    wo, _ = services.create_work_order_for_tasks([tarea], d["admin"])

    r = d["c"].get(f"/api/work-orders/{wo.id}/")
    assert r.status_code == 200, r.data
    assert r.data["tasks"][0]["asset"]["is_location"] is True

    services.complete_work_order_tasks(wo)
    assert Task.objects.filter(asset=activo, status=Task.Status.PENDING).count() == 1, (
        "al cerrar se programa la siguiente, igual que en un equipo"
    )


def test_quitar_el_protocolo_de_la_ubicacion(d):
    _asignar(d, d["piso"])
    activo = Asset.objects.get(represents_node=d["piso"])
    r = d["c"].post(
        f"/api/maintenance/plans/{d['plan'].id}/remove-assets/",
        {"asset_ids": [str(activo.id)]}, format="json",
    )
    assert r.data["removed"] == 1
    assert not Task.objects.filter(asset=activo, status=Task.Status.PENDING).exists()


def test_protocolo_de_otro_hospital_se_rechaza(d):
    otro = Hospital.objects.create(name="Otro", code=uuid.uuid4().hex[:8])
    d["plan"].restrict_to_hospital = otro
    d["plan"].save()
    r = _asignar(d, d["piso"])
    assert r.status_code == 400
    assert "node_ids" in r.data
    assert not Asset.objects.filter(represents_node=d["piso"]).exists()


def test_supervisor_limitado_no_asigna_fuera_de_su_alcance(d):
    otro = Hospital.objects.create(name="Otro", code=uuid.uuid4().hex[:8])
    ajeno = AssetNode.objects.create(hospital=otro, name="Torre B")
    sup = _user(User.Role.SUP, hospital=d["h"])
    c = APIClient()
    c.force_authenticate(user=sup)
    r = _asignar(d, ajeno, client=c)
    assert r.status_code in (400, 403)
    assert not Asset.objects.filter(represents_node=ajeno).exists()


def test_renombrar_la_ubicacion_renombra_su_activo(d):
    _asignar(d, d["piso"])
    d["piso"].name = "Piso 3 - UCI"
    d["piso"].save()
    assert Asset.objects.get(represents_node=d["piso"]).name == "Piso 3 - UCI"


def test_no_se_borra_una_ubicacion_con_protocolo(d):
    sotano = AssetNode.objects.create(hospital=d["h"], name="Sotano")
    _asignar(d, sotano)
    r = d["c"].delete(f"/api/asset-nodes/{sotano.id}/")
    assert r.status_code == 400


def test_el_acta_de_la_ubicacion_se_genera(d):
    from apps.reports.generator import preview_service_report_pdf
    from apps.reports.options import efectivas

    _asignar(d, d["piso"])
    activo = Asset.objects.get(represents_node=d["piso"])
    tarea = Task.objects.get(asset=activo, status=Task.Status.PENDING)
    wo, _ = services.create_work_order_for_tasks([tarea], d["admin"])
    pdf = preview_service_report_pdf(wo, efectivas({}))
    assert pdf[:4] == b"%PDF"
