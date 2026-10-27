"""
Etiqueta Antes / Despues en las fotos (audio3 ~05:10).

La foto ya tiene descripcion; ahora tambien se marca como "Antes" o "Despues"
del trabajo (o sin etiqueta). Vale al capturarla en campo, la corrige el admin
o supervisor en revision, el acta agrupa por etiqueta y, al ser parte de lo
capturado, entra en el hash de integridad (version 6) sin invalidar las actas
firmadas con la 5 o anteriores.
"""

from datetime import timedelta
from unittest import mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string as render_real
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.evidence.tests.firmas import firmar
from apps.audit.models import AuditLog
from apps.evidence.models import Photo
from apps.reports.generator import _render
from apps.reports.models import GeneratedReport
from apps.reports.options import efectivas
from apps.users.models import User
from apps.work_orders import integrity
from apps.work_orders.models import WorkOrder

# Fixtures y ayudantes del flujo de revision (misma OT, mismo hospital).
from .test_admin_ejecuta_y_corrige import (  # noqa: F401
    PNG_1PX, client_for, crear_ot, d, en_revision, make_user, transicion,
)

pytestmark = pytest.mark.django_db


def subir(c, wo_id, caption="", stage=None, taken_at=None):
    datos = {
        "work_order": str(wo_id),
        "file": SimpleUploadedFile("f.png", PNG_1PX, content_type="image/png"),
        "taken_at": (taken_at or timezone.now()).isoformat(),
        "caption": caption,
    }
    if stage is not None:
        datos["stage"] = stage
    return c.post(reverse("evidence-photos-list"), datos, format="multipart")


def url_foto(p):
    return reverse("evidence-photos-detail", kwargs={"pk": p.id})


def html_del_acta(wo):
    """El HTML que recibe WeasyPrint, sin renderizar el PDF."""
    capturado = {}

    def espia(plantilla, contexto, *a, **k):
        capturado["html"] = render_real(plantilla, contexto, *a, **k)
        return "<p></p>"

    with mock.patch("apps.reports.generator.render_to_string", side_effect=espia):
        _render(wo, efectivas({}))
    return capturado["html"]


# ── Modelo y API ─────────────────────────────────────────────────────────────

def test_la_etiqueta_tiene_tres_opciones_y_las_fotos_viejas_quedan_sin_etiqueta():
    campo = Photo._meta.get_field("stage")
    assert dict(campo.choices) == {"BEFORE": "Antes", "AFTER": "Después", "": "Sin etiqueta"}
    assert campo.default == ""


def test_la_api_acepta_y_devuelve_la_etiqueta_al_crear_la_foto(d):
    tec = make_user(User.Role.TEC)
    wo_id = crear_ot(d, tec)
    c = client_for(tec)
    transicion(c, wo_id, WorkOrder.Status.IN_PROGRESS)

    r = subir(c, wo_id, "Valvula", stage="BEFORE")
    assert r.status_code == status.HTTP_201_CREATED, r.data
    assert r.data["stage"] == "BEFORE"
    assert Photo.objects.get(pk=r.data["id"]).stage == "BEFORE"

    r = subir(c, wo_id, "Valvula lista", stage="AFTER")
    assert r.data["stage"] == "AFTER"

    # Sin enviar nada: sin etiqueta, como las de antes.
    r = subir(c, wo_id, "Suelta")
    assert r.status_code == status.HTTP_201_CREATED
    assert r.data["stage"] == ""

    lista = c.get(reverse("evidence-photos-list"), {"work_order": wo_id}).data
    assert sorted(p["stage"] for p in lista) == ["", "AFTER", "BEFORE"]


def test_una_etiqueta_invalida_se_rechaza(d):
    tec = make_user(User.Role.TEC)
    wo_id = crear_ot(d, tec)
    c = client_for(tec)
    transicion(c, wo_id, WorkOrder.Status.IN_PROGRESS)
    r = subir(c, wo_id, "x", stage="DURANTE")
    assert r.status_code == status.HTTP_400_BAD_REQUEST
    assert "stage" in r.data


def test_en_revision_el_admin_cambia_la_etiqueta_y_queda_en_auditoria(en_revision):
    e = en_revision
    p = Photo.objects.get(work_order_id=e["wo_id"])
    assert p.stage == ""

    r = client_for(e["admin"]).patch(url_foto(p), {"stage": "AFTER"}, format="json")
    assert r.status_code == 200, r.data
    assert r.data["stage"] == "AFTER"
    p.refresh_from_db()
    assert p.stage == "AFTER"
    log = AuditLog.objects.get(entity_type="Photo", entity_id=p.id, changes__has_key="stage")
    assert log.changes["stage"] == {"from": "", "to": "AFTER"}
    assert log.changes["correccion"] is True

    # Tambien se puede quitar.
    r = client_for(e["admin"]).patch(url_foto(p), {"stage": ""}, format="json")
    assert r.status_code == 200
    p.refresh_from_db()
    assert p.stage == ""


def test_la_etiqueta_en_revision_sigue_las_reglas_de_la_descripcion(en_revision):
    e = en_revision
    p = Photo.objects.get(work_order_id=e["wo_id"])

    # El tecnico no la corrige en revision.
    r = client_for(e["tec"]).patch(url_foto(p), {"stage": "BEFORE"}, format="json")
    assert r.status_code in (400, 403)
    # Un supervisor de otro hospital no la toca.
    otro = make_user(User.Role.SUP, hospital=e["otro"])
    assert client_for(otro).patch(url_foto(p), {"stage": "BEFORE"}, format="json").status_code in (403, 404)
    # Valor invalido.
    r = client_for(e["admin"]).patch(url_foto(p), {"stage": "DURANTE"}, format="json")
    assert r.status_code == 400
    p.refresh_from_db()
    assert p.stage == ""

    # Cerrada ya no se cambia.
    firmar(e["admin"])
    assert transicion(client_for(e["admin"]), e["wo_id"], WorkOrder.Status.COMPLETED).status_code == 200
    r = client_for(e["admin"]).patch(url_foto(p), {"stage": "BEFORE"}, format="json")
    assert r.status_code == 400
    p.refresh_from_db()
    assert p.stage == ""


# ── Acta ─────────────────────────────────────────────────────────────────────

def test_el_acta_agrupa_las_fotos_de_la_visita_en_antes_despues_y_sin_etiqueta(en_revision):
    e = en_revision
    wo = WorkOrder.objects.get(pk=e["wo_id"])
    base = timezone.now()
    c = client_for(e["admin"])
    # Orden de captura mezclado (despues, suelta, antes) para probar que agrupa.
    assert subir(c, wo.id, "zz-despues", "AFTER", base).status_code == 201
    assert subir(c, wo.id, "zz-suelta", "", base + timedelta(seconds=1)).status_code == 201
    assert subir(c, wo.id, "zz-antes", "BEFORE", base + timedelta(seconds=2)).status_code == 201

    html = html_del_acta(wo)
    antes, despues, suelta = (html.index(f"zz-{n}") for n in ("antes", "despues", "suelta"))
    assert antes < despues < suelta, "primero Antes, luego Despues, al final las sin etiqueta"
    # Cada grupo lleva su encabezado visible para quien lee el acta.
    assert html.rfind("Antes", 0, antes) != -1
    assert antes < html.index("Después", antes) < despues


def test_el_acta_sin_etiquetas_sale_como_siempre(en_revision):
    wo = WorkOrder.objects.get(pk=en_revision["wo_id"])
    html = html_del_acta(wo)
    assert "Evidencia fotográfica" in html
    assert "Después" not in html, "sin etiquetas no se inventan encabezados"


# ── Integridad ───────────────────────────────────────────────────────────────

def test_el_hash_vigente_cubre_la_etiqueta(en_revision):
    e = en_revision
    assert integrity.INTEGRITY_ALGORITHM_VERSION == "8"
    assert "8" in integrity.SUPPORTED_VERSIONS and "5" in integrity.SUPPORTED_VERSIONS

    firmar(e["admin"])
    assert transicion(client_for(e["admin"]), e["wo_id"], WorkOrder.Status.COMPLETED).status_code == 200
    assert GeneratedReport.objects.get(work_order_id=e["wo_id"]).integrity_version == "8"

    wo = WorkOrder.objects.get(pk=e["wo_id"])
    assert integrity.verify_work_order(wo).verified is True
    # Cambiar la etiqueta a escondidas despues de firmada rompe la integridad.
    Photo.objects.filter(work_order=wo).update(stage="BEFORE")
    assert integrity.verify_work_order(wo).verified is False


def test_las_actas_firmadas_con_la_version_5_ignoran_la_etiqueta_y_siguen_verificando(en_revision):
    e = en_revision
    wo = WorkOrder.objects.get(pk=e["wo_id"])
    h5 = integrity.compute_wo_content_hash(wo, "5")
    h6 = integrity.compute_wo_content_hash(wo, "6")
    assert h5 != h6

    Photo.objects.filter(work_order=wo).update(stage="AFTER")
    assert integrity.compute_wo_content_hash(wo, "5") == h5, "la v5 no sabe de etiquetas"
    assert integrity.compute_wo_content_hash(wo, "6") != h6

    # Un acta v5 ya guardada sigue dando VERIFIED aunque las fotos tengan etiqueta.
    GeneratedReport.objects.create(
        work_order=wo, report_type=GeneratedReport.ReportType.WORK_ORDER, title="Acta",
        generated_by=e["admin"], integrity_version="5", content_hash=h5,
        file_hash="x" * 64, file_url="reports/x.pdf",
    )
    assert integrity.verify_work_order(wo).verified is True
