"""
El administrador o supervisor ejecuta una OT y la corrige en revision
(decision del 2026-10-01; audio1 07:50 y 13:15, audio3 13:16).

- Admin y supervisor pueden quedar asignados y hacer lo del tecnico; quien la
  ejecuto puede aprobarla el mismo.
- En revision, admin o supervisor corrigen respuestas (queda "Corregido por",
  la hora del tecnico y el valor anterior en auditoria) y fotos: agregan,
  cambian la descripcion u ocultan del acta, sin borrar.
"""

import base64
import uuid
from datetime import date, timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.assets.models import Asset, AssetNode, Hospital
from apps.audit.models import AuditLog
from apps.checklists.models import (
    ChecklistField,
    ChecklistFieldResponse,
    ChecklistTemplate,
    ChecklistTemplateVersion,
)
from apps.evidence.models import Photo, Signature
from unittest import mock

from apps.reports.generator import _render, field_facts
from apps.reports.options import efectivas
from apps.reports.models import GeneratedReport
from apps.users.models import User
from apps.work_orders import integrity
from apps.work_orders.models import WorkOrder

pytestmark = pytest.mark.django_db

PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmM"
    "IQAAAABJRU5ErkJggg=="
)


def client_for(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def make_user(role, **kwargs):
    return User.objects.create_user(
        email=f"{uuid.uuid4()}@todogas.test", password="x",
        first_name="Zz", last_name=role.title(), role=role, **kwargs,
    )


@pytest.fixture
def d():
    admin = make_user(User.Role.ADMIN)
    h = Hospital.objects.create(name="Clinica", code=uuid.uuid4().hex[:8])
    otro = Hospital.objects.create(name="Otra", code=uuid.uuid4().hex[:8])
    activo = Asset.objects.create(hospital=h, name="Alarma", code=uuid.uuid4().hex[:8])
    t = ChecklistTemplate.objects.create(name=f"Alarma {uuid.uuid4().hex[:6]}")
    v = ChecklistTemplateVersion.objects.create(template=t, version_number=1, published_by=admin, is_current=True)
    campo = ChecklistField.objects.create(
        version=v, label="Presión (PSI)", field_type=ChecklistField.FieldType.NUMBER,
        is_required=True, sort_order=1,
    )
    return {"admin": admin, "h": h, "otro": otro, "activo": activo, "version": v, "campo": campo}


def crear_ot(d, asignado):
    resp = client_for(d["admin"]).post(reverse("work-orders-list"), {
        "tasks": [{"asset": str(d["activo"].id), "checklist_version": str(d["version"].id)}],
        "task_type": WorkOrder.TaskType.CORRECTIVE,
        "title": "Reporte de instalación",
        "priority": WorkOrder.Priority.MEDIUM,
        "scheduled_date": str(date.today() + timedelta(days=1)),
        "assigned_to": str(asignado.id) if asignado else None,
    }, format="json")
    assert resp.status_code == status.HTTP_201_CREATED, resp.data
    return resp.data["id"]


def transicion(c, wo_id, estado):
    return c.post(reverse("work-orders-transition", kwargs={"pk": wo_id}), {"new_status": estado}, format="json")


def foto(c, wo_id, caption="Antes"):
    return c.post(reverse("evidence-photos-list"), {
        "work_order": str(wo_id),
        "file": SimpleUploadedFile("f.png", PNG_1PX, content_type="image/png"),
        "taken_at": timezone.now().isoformat(),
        "caption": caption,
    }, format="multipart")


def ejecutar(c, wo_id, campo, valor="50"):
    """Lo que hace quien la tiene asignada: iniciar, checklist, foto, firma, revision."""
    assert transicion(c, wo_id, WorkOrder.Status.IN_PROGRESS).status_code == 200
    cr = c.get(reverse("work-orders-detail", kwargs={"pk": wo_id})).data["tasks"][0]["checklist_response_id"]
    r = c.post(reverse("checklist-responses-submit-field", kwargs={"pk": cr}),
               {"field": str(campo.id), "value": valor}, format="json")
    assert r.status_code == 200, r.data
    assert c.post(reverse("checklist-responses-complete", kwargs={"pk": cr})).status_code == 200
    assert foto(c, wo_id).status_code == 201
    r = c.post(reverse("evidence-signatures-list"), {
        "work_order": str(wo_id), "image_data": base64.b64encode(PNG_1PX).decode(),
        "signer_name": "Quien ejecuta", "signature_type": Signature.SignatureType.TECHNICIAN,
    }, format="json")
    assert r.status_code == 201, r.data
    r = transicion(c, wo_id, WorkOrder.Status.IN_REVIEW)
    assert r.status_code == 200, r.data
    return cr


def _contexto_del_acta(wo):
    """Lo que recibe la plantilla del acta, sin pasar por WeasyPrint."""
    with mock.patch("apps.reports.generator.render_to_string", return_value="<p></p>") as r:
        _render(wo, efectivas({}))
    return r.call_args.args[1]


# ── Ejecutar ─────────────────────────────────────────────────────────────────

def test_el_admin_se_la_asigna_la_ejecuta_y_la_aprueba(d):
    admin = d["admin"]
    c = client_for(admin)
    wo_id = crear_ot(d, admin)
    ejecutar(c, wo_id, d["campo"])

    r = transicion(c, wo_id, WorkOrder.Status.COMPLETED)
    assert r.status_code == 200, r.data
    reporte = GeneratedReport.objects.get(work_order_id=wo_id)
    assert reporte.integrity_version == "5"
    hechos = field_facts(WorkOrder.objects.get(pk=wo_id))
    assert hechos["executors"] == ["Zz Admin"], "el acta dice quien la ejecuto"


def test_el_supervisor_ejecuta_una_ot_fuera_de_su_alcance_si_se_la_asignan(d):
    sup = make_user(User.Role.SUP, hospital=d["otro"])
    wo_id = crear_ot(d, sup)
    c = client_for(sup)
    assert wo_id in [w["id"] for w in c.get(reverse("work-orders-list")).data["results"]]
    ejecutar(c, wo_id, d["campo"])


def test_solo_el_asignado_la_inicia(d):
    tec = make_user(User.Role.TEC)
    wo_id = crear_ot(d, tec)
    r = transicion(client_for(d["admin"]), wo_id, WorkOrder.Status.IN_PROGRESS)
    assert r.status_code == 400
    assert "Asígnatela" in str(r.data)


def test_una_cuenta_de_hospital_no_ejecuta(d):
    cli = make_user(User.Role.CLI, hospital=d["h"])
    wo_id = crear_ot(d, None)
    r = client_for(d["admin"]).post(reverse("work-orders-assign", kwargs={"pk": wo_id}),
                                    {"assigned_to": str(cli.id)}, format="json")
    assert r.status_code == 400


# ── Corregir respuestas ──────────────────────────────────────────────────────

@pytest.fixture
def en_revision(d):
    tec = make_user(User.Role.TEC)
    wo_id = crear_ot(d, tec)
    cr = ejecutar(client_for(tec), wo_id, d["campo"], valor="50")
    return {**d, "tec": tec, "wo_id": wo_id, "cr": cr}


def corregir(user, e, valor, **extra):
    return client_for(user).post(
        reverse("checklist-responses-correct-field", kwargs={"pk": e["cr"]}),
        {"field": str(e["campo"].id), "value": valor, **extra}, format="json",
    )


def test_el_admin_corrige_una_respuesta_en_revision(en_revision):
    e = en_revision
    fr = ChecklistFieldResponse.objects.get(response_id=e["cr"])
    hora_del_tecnico = fr.answered_at

    r = corregir(e["admin"], e, "55")
    assert r.status_code == 200, r.data
    assert r.data["value"] == "55"
    assert r.data["corrected_by_name"] == "Zz Admin"

    fr.refresh_from_db()
    assert fr.value == "55"
    assert fr.corrected_by == e["admin"] and fr.corrected_at is not None
    assert fr.answered_at == hora_del_tecnico, "la hora sigue siendo la del tecnico"
    log = AuditLog.objects.get(entity_type="ChecklistFieldResponse", entity_id=fr.id, changes__correccion=True)
    assert log.changes["value"] == {"from": "50", "to": "55"}
    assert log.changes["correccion"] is True

    # El acta sale con el valor final y la aprobacion sigue funcionando.
    assert transicion(client_for(e["admin"]), e["wo_id"], WorkOrder.Status.COMPLETED).status_code == 200
    wo = WorkOrder.objects.get(pk=e["wo_id"])
    assert integrity.verify_work_order(wo).verified is True


def test_el_supervisor_corrige_y_el_mismo_valor_no_marca_correccion(en_revision):
    e = en_revision
    sup = make_user(User.Role.SUP, hospital=e["h"])
    r = corregir(sup, e, "50")
    assert r.status_code == 200
    assert ChecklistFieldResponse.objects.get(response_id=e["cr"]).corrected_by is None
    assert corregir(sup, e, "48").status_code == 200
    assert ChecklistFieldResponse.objects.get(response_id=e["cr"]).corrected_by == sup


def test_corregir_respeta_las_reglas_del_campo(en_revision):
    r = corregir(en_revision["admin"], en_revision, "")
    assert r.status_code == 400, "un obligatorio no se puede vaciar al corregir"


def test_no_se_corrige_fuera_de_revision_ni_lo_hace_el_tecnico(en_revision):
    e = en_revision
    assert corregir(e["tec"], e, "60").status_code == 403
    # Devuelta al tecnico: ahi la corrige el, no el admin.
    assert transicion(client_for(e["admin"]), e["wo_id"], WorkOrder.Status.IN_PROGRESS).status_code == 200
    assert corregir(e["admin"], e, "60").status_code == 400


def test_un_supervisor_de_otro_hospital_no_corrige(en_revision):
    e = en_revision
    sup = make_user(User.Role.SUP, hospital=e["otro"])
    assert corregir(sup, e, "60").status_code == 404


# ── Corregir fotos ───────────────────────────────────────────────────────────

def test_en_revision_el_admin_agrega_fotos_y_el_tecnico_no(en_revision):
    e = en_revision
    assert foto(client_for(e["admin"]), e["wo_id"], "Faltaba esta").status_code == 201
    assert foto(client_for(e["tec"]), e["wo_id"]).status_code == 400
    assert AuditLog.objects.filter(entity_type="Photo", changes__correccion=True,
                                   changes__caption="Faltaba esta").exists()


def test_una_foto_mala_se_oculta_del_acta_sin_borrarse(en_revision):
    e = en_revision
    c = client_for(e["admin"])
    foto(c, e["wo_id"], "La buena")
    mala = Photo.objects.get(work_order_id=e["wo_id"], caption="Antes")

    r = c.patch(reverse("evidence-photos-detail", kwargs={"pk": mala.id}),
                {"hidden": True, "caption": "Borrosa"}, format="json")
    assert r.status_code == 200, r.data
    assert r.data["hidden"] is True and r.data["hidden_by_name"] == "Zz Admin"
    mala.refresh_from_db()
    assert mala.hidden and mala.caption == "Borrosa"
    log = AuditLog.objects.get(entity_type="Photo", entity_id=mala.id, changes__has_key="hidden")
    assert log.changes["caption"] == {"from": "Antes", "to": "Borrosa"}

    # El tecnico no la corrige en revision.
    r = client_for(e["tec"]).patch(reverse("evidence-photos-detail", kwargs={"pk": mala.id}),
                                   {"hidden": False}, format="json")
    assert r.status_code in (400, 403)

    assert transicion(c, e["wo_id"], WorkOrder.Status.COMPLETED).status_code == 200
    wo = WorkOrder.objects.get(pk=e["wo_id"])
    assert [p.caption for p in _contexto_del_acta(wo)["photos"]] == ["La buena"]
    assert Photo.objects.filter(pk=mala.pk).exists(), "ocultar no borra"

    # El hospital ve lo mismo que el acta.
    cli = make_user(User.Role.CLI, hospital=e["h"])
    lista = client_for(cli).get(reverse("evidence-photos-list"), {"work_order": e["wo_id"]}).data
    assert [p["caption"] for p in lista] == ["La buena"]

    # Cerrada ya no se cambia, y mostrarla a escondidas rompe la integridad.
    r = c.patch(reverse("evidence-photos-detail", kwargs={"pk": mala.id}), {"hidden": False}, format="json")
    assert r.status_code == 400
    assert integrity.verify_work_order(wo).verified is True
    Photo.objects.filter(pk=mala.pk).update(hidden=False)
    assert integrity.verify_work_order(wo).verified is False


def test_la_foto_obligatoria_tiene_que_salir_en_el_acta(d):
    tec = make_user(User.Role.TEC)
    wo_id = crear_ot(d, tec)
    c = client_for(tec)
    transicion(c, wo_id, WorkOrder.Status.IN_PROGRESS)
    foto(c, wo_id)
    p = Photo.objects.get(work_order_id=wo_id)
    assert c.patch(reverse("evidence-photos-detail", kwargs={"pk": p.id}), {"hidden": True}, format="json").status_code == 200
    r = transicion(c, wo_id, WorkOrder.Status.IN_REVIEW)
    assert r.status_code == 400
    assert "foto" in str(r.data)


def test_las_actas_firmadas_con_la_version_4_siguen_verificando(en_revision):
    e = en_revision
    wo = WorkOrder.objects.get(pk=e["wo_id"])
    h4 = integrity.compute_wo_content_hash(wo, "4")
    Photo.objects.filter(work_order=wo).update(hidden=False)
    assert integrity.compute_wo_content_hash(wo, "4") == h4
    assert integrity.compute_wo_content_hash(wo, "5") != h4
