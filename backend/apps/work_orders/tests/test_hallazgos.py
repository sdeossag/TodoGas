"""
Hallazgos desde campo (bloque E, decisiones del 2026-09-23).

El tecnico reporta lo que encontro en un equipo, y si lo arreglo ahi mismo lo
marca resuelto en sitio; lo pendiente va a la bandeja del planificador, que
lo convierte en correctivo o lo descarta. Sale en el acta, entra en el hash,
y el hospital lo ve y recibe un correo si es grave.
"""

import sys
import types
import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from model_bakery import baker
from rest_framework.test import APIClient

from apps.assets.models import Asset, AssetNode, Hospital
from apps.evidence.models import Photo
from apps.maintenance import services
from apps.maintenance.models import Task
from apps.maintenance.testing import make_plan
from apps.users.models import User
from apps.work_orders.integrity import compute_wo_content_hash
from apps.work_orders.models import Finding, WorkOrder
from apps.work_orders.transitions import apply_transition

pytestmark = pytest.mark.django_db
URL = "/api/findings/"


def cliente(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def mundo():
    h = baker.make(Hospital, is_active=True, contact_email="biomedica@clinica.co")
    otro = baker.make(Hospital, is_active=True)
    urg = AssetNode.objects.create(hospital=h, name="Urgencias")
    admin = baker.make(User, role=User.Role.ADMIN, is_active=True)
    sup = baker.make(User, role=User.Role.SUP, is_active=True)
    tec = baker.make(User, role=User.Role.TEC, is_active=True, first_name="Juan", last_name="Zuleta")
    alarma = Asset.objects.create(hospital=h, node=urg, name="Alarma", code="ALR",
                                  status=Asset.Status.ACTIVE)
    ajeno = Asset.objects.create(hospital=h, name="Compresor", code="CMP", status=Asset.Status.ACTIVE)
    plan = make_plan("P", assets=[alarma], next_due_date=timezone.localdate())
    tarea = Task.objects.get(plan_task__plan=plan, status=Task.Status.PENDING)
    ot, _ = services.create_work_order_for_tasks([tarea], admin, assigned_to=tec)
    WorkOrder.objects.filter(pk=ot.pk).update(
        status=WorkOrder.Status.IN_PROGRESS, created_at=timezone.now() - timezone.timedelta(hours=2)
    )
    ot.refresh_from_db()
    return {"h": h, "otro": otro, "urg": urg, "admin": admin, "sup": sup, "tec": tec,
            "alarma": alarma, "ajeno": ajeno, "ot": ot}


def reportar(m, **datos):
    base = {"work_order": str(m["ot"].id), "asset": str(m["alarma"].id),
            "description": "Fuga en la valvula de oxigeno", "severity": "HIGH"}
    return cliente(m["tec"]).post(URL, {**base, **datos}, format="json")


def a_estado(ot, estado):
    WorkOrder.objects.filter(pk=ot.pk).update(status=estado)
    ot.refresh_from_db()


# ── Registrar ────────────────────────────────────────────────────────────────

def test_el_tecnico_reporta_un_hallazgo_pendiente(mundo):
    r = reportar(mundo)
    assert r.status_code == 201, r.data
    f = Finding.objects.get()
    assert f.status == Finding.Status.PENDING
    assert f.reported_by == mundo["tec"]


def test_resuelto_en_sitio_exige_decir_que_se_hizo(mundo):
    assert reportar(mundo, resolved_on_site=True).status_code == 400
    r = reportar(mundo, resolved_on_site=True, resolution_notes="Se cambio el empaque")
    assert r.status_code == 201
    assert Finding.objects.get().status == Finding.Status.RESOLVED


def test_el_reintento_sin_red_no_duplica(mundo):
    """El telefono pone el id: si la respuesta se perdio, reenviar no crea otro."""
    ident = str(uuid.uuid4())
    assert reportar(mundo, id=ident).status_code == 201
    assert reportar(mundo, id=ident).status_code == 200
    assert Finding.objects.count() == 1
    assert str(Finding.objects.get().id) == ident


def test_la_hora_es_la_del_telefono(mundo):
    hace_rato = timezone.now() - timezone.timedelta(minutes=40)
    reportar(mundo, reported_at=hace_rato.isoformat())
    assert Finding.objects.get().reported_at == hace_rato


def test_el_equipo_tiene_que_ser_de_la_ot(mundo):
    r = reportar(mundo, asset=str(mundo["ajeno"].id))
    assert r.status_code == 400
    assert "asset" in r.data


def test_solo_el_tecnico_de_la_ot_reporta(mundo):
    otro_tec = baker.make(User, role=User.Role.TEC, is_active=True)
    cli = baker.make(User, role=User.Role.CLI, is_active=True, hospital=mundo["h"])
    datos = {"work_order": str(mundo["ot"].id), "asset": str(mundo["alarma"].id),
             "description": "X", "severity": "LOW"}
    assert cliente(otro_tec).post(URL, datos, format="json").status_code == 403
    assert cliente(cli).post(URL, datos, format="json").status_code == 403


def test_enviada_a_revision_el_hallazgo_es_evidencia(mundo):
    r = reportar(mundo)
    a_estado(mundo["ot"], WorkOrder.Status.IN_REVIEW)
    c = cliente(mundo["tec"])
    assert c.patch(f"{URL}{r.data['id']}/", {"description": "otra"}, format="json").status_code == 400
    assert c.delete(f"{URL}{r.data['id']}/").status_code == 400
    assert reportar(mundo, description="Otro").status_code == 400


def test_la_foto_del_hallazgo_va_con_su_equipo(mundo, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    f = reportar(mundo).data
    png = SimpleUploadedFile("f.png", b"\x89PNG\r\n\x1a\n" + b"0" * 64, content_type="image/png")
    r = cliente(mundo["tec"]).post("/api/evidence/photos/", {
        "work_order": str(mundo["ot"].id), "finding": f["id"], "file": png,
        "taken_at": timezone.now().isoformat(),
    }, format="multipart")
    assert r.status_code == 201, r.data
    foto = Photo.objects.get()
    assert str(foto.finding_id) == f["id"]
    assert foto.task.asset == mundo["alarma"], "sale en el bloque de su equipo en el acta"


# ── Bandeja del planificador ─────────────────────────────────────────────────

def test_el_planificador_lo_convierte_en_correctivo(mundo):
    f = reportar(mundo, severity="CRITICAL").data
    a_estado(mundo["ot"], WorkOrder.Status.IN_REVIEW)
    pendientes = cliente(mundo["sup"]).get(URL, {"status": "PENDING"}).data
    filas = pendientes["results"] if isinstance(pendientes, dict) else pendientes
    assert [x["id"] for x in filas] == [f["id"]]

    r = cliente(mundo["sup"]).post(f"{URL}{f['id']}/convert/", {}, format="json")
    assert r.status_code == 200, r.data
    hallazgo = Finding.objects.get()
    assert hallazgo.status == Finding.Status.CONVERTED
    assert hallazgo.decided_by == mundo["sup"]
    t = hallazgo.corrective_task
    assert (t.status, t.task_type, t.priority, t.asset) == ("PENDING", "CORRECTIVE", "HIGH", mundo["alarma"])
    assert r.data["corrective_task_info"]["id"] == str(t.id)
    # Sale en Tareas pendientes para agruparla en una OT.
    tareas = cliente(mundo["sup"]).get("/api/tasks/", {"status": "PENDING"}).data
    filas = tareas["results"] if isinstance(tareas, dict) else tareas
    assert str(t.id) in {x["id"] for x in filas}


def test_no_se_decide_dos_veces_ni_antes_de_la_revision(mundo):
    f = reportar(mundo).data
    c = cliente(mundo["sup"])
    assert c.post(f"{URL}{f['id']}/convert/", {}, format="json").status_code == 400
    a_estado(mundo["ot"], WorkOrder.Status.IN_REVIEW)
    assert c.post(f"{URL}{f['id']}/convert/", {}, format="json").status_code == 200
    assert c.post(f"{URL}{f['id']}/dismiss/", {"note": "x"}, format="json").status_code == 400


def test_descartar_exige_motivo(mundo):
    f = reportar(mundo).data
    a_estado(mundo["ot"], WorkOrder.Status.COMPLETED)
    c = cliente(mundo["sup"])
    assert c.post(f"{URL}{f['id']}/dismiss/", {"note": " "}, format="json").status_code == 400
    r = c.post(f"{URL}{f['id']}/dismiss/", {"note": "Ya lo reporto el hospital"}, format="json")
    assert r.status_code == 200
    assert Finding.objects.get().status == Finding.Status.DISMISSED


def test_el_tecnico_no_decide(mundo):
    f = reportar(mundo).data
    a_estado(mundo["ot"], WorkOrder.Status.IN_REVIEW)
    assert cliente(mundo["tec"]).post(f"{URL}{f['id']}/convert/", {}, format="json").status_code == 403


def test_un_supervisor_de_otra_clinica_no_lo_ve(mundo):
    f = reportar(mundo).data
    a_estado(mundo["ot"], WorkOrder.Status.IN_REVIEW)
    sup_b = baker.make(User, role=User.Role.SUP, is_active=True, hospital=mundo["otro"])
    c = cliente(sup_b)
    datos = c.get(URL).data
    filas = datos["results"] if isinstance(datos, dict) else datos
    assert filas == []
    assert c.post(f"{URL}{f['id']}/convert/", {}, format="json").status_code == 404


def test_el_resumen_cuenta_los_pendientes_de_la_bandeja(mundo):
    reportar(mundo, severity="CRITICAL")
    reportar(mundo, severity="LOW")
    reportar(mundo, severity="LOW", resolved_on_site=True, resolution_notes="Ajustado")
    a_estado(mundo["ot"], WorkOrder.Status.IN_REVIEW)
    r = cliente(mundo["sup"]).get(URL + "summary/").data
    assert r == {"pending": 2, "by_severity": {"CRITICAL": 1, "LOW": 1}, "serious": 1}


# ── Hospital ─────────────────────────────────────────────────────────────────

def test_el_hospital_ve_los_hallazgos_de_sus_visitas_finalizadas(mundo):
    reportar(mundo)
    cli = baker.make(User, role=User.Role.CLI, is_active=True, hospital=mundo["h"])
    ver = lambda: cliente(cli).get(URL).data  # noqa: E731
    filas = lambda d: d["results"] if isinstance(d, dict) else d  # noqa: E731
    assert filas(ver()) == [], "en curso no"
    a_estado(mundo["ot"], WorkOrder.Status.COMPLETED)
    assert len(filas(ver())) == 1
    resumen = cliente(cli).get("/api/client-portal/summary/").data
    assert resumen["open_findings_count"] == 1
    assert resumen["recent_findings"][0]["state"] == "OPEN"


def test_al_aprobar_con_uno_grave_se_avisa_al_hospital(mundo):
    reportar(mundo, severity="LOW", out_of_service=True)
    urg = baker.make(User, role=User.Role.CLI, is_active=True, hospital=mundo["h"],
                     scope_node=mundo["urg"], email="urg@clinica.co")
    otro_piso = AssetNode.objects.create(hospital=mundo["h"], name="Cirugia")
    baker.make(User, role=User.Role.CLI, is_active=True, hospital=mundo["h"],
               scope_node=otro_piso, email="cirugia@clinica.co")
    a_estado(mundo["ot"], WorkOrder.Status.IN_REVIEW)
    with patch("apps.reports.tasks.generate_work_order_pdf.delay"):
        apply_transition(mundo["ot"], WorkOrder.Status.COMPLETED, mundo["admin"])
    assert len(mail.outbox) == 1
    correo = mail.outbox[0]
    assert sorted(correo.to) == ["biomedica@clinica.co", urg.email], "no a la de otro piso"
    assert "Fuera de servicio" in correo.body


def test_sin_hallazgos_graves_no_hay_correo(mundo):
    reportar(mundo, severity="HIGH")
    a_estado(mundo["ot"], WorkOrder.Status.IN_REVIEW)
    with patch("apps.reports.tasks.generate_work_order_pdf.delay"):
        apply_transition(mundo["ot"], WorkOrder.Status.COMPLETED, mundo["admin"])
    assert mail.outbox == []


# ── Acta e integridad ────────────────────────────────────────────────────────

def test_el_hash_cubre_lo_capturado_y_no_la_decision(mundo):
    reportar(mundo)
    a_estado(mundo["ot"], WorkOrder.Status.COMPLETED)
    antes = compute_wo_content_hash(mundo["ot"])
    cliente(mundo["sup"]).post(f"{URL}{Finding.objects.get().id}/convert/", {}, format="json")
    assert compute_wo_content_hash(mundo["ot"]) == antes, "decidir no altera el acta"
    Finding.objects.update(description="Otra cosa")
    assert compute_wo_content_hash(mundo["ot"]) != antes


def test_el_acta_lista_los_hallazgos(mundo):
    from apps.reports.generator import generate_service_report_pdf

    reportar(mundo, description="Fuga en la valvula")
    reportar(mundo, description="Tornillo flojo", severity="LOW",
             resolved_on_site=True, resolution_notes="Se ajusto")
    html = {}
    falso = types.ModuleType("weasyprint")

    def HTML(string, base_url=None):
        html["t"] = string
        return MagicMock(write_pdf=lambda: b"%PDF")

    falso.HTML = HTML
    with patch.dict(sys.modules, {"weasyprint": falso}), \
            patch("apps.reports.generator.default_storage") as storage:
        storage.save.return_value = "r.pdf"
        generate_service_report_pdf(mundo["ot"])
    t = html["t"]
    assert "Hallazgos encontrados y reportados" in t
    assert "Fuga en la valvula" in t and "Pendiente de corrección" in t
    assert "Tornillo flojo" in t and "Resuelto en sitio" in t and "Se ajusto" in t
