"""
La aprobacion firma sola con la firma guardada de quien aprueba, y esa firma
sale en el acta, en "Validado por" (pedido del cliente, 2026-10).
"""

import base64
from unittest import mock

import pytest
from django.core.files.storage import default_storage
from django.urls import reverse
from rest_framework.exceptions import ValidationError

from apps.audit.models import AuditLog
from apps.evidence.models import Signature, UserSignature
from apps.evidence.tests.firmas import firmar, png_bytes
from apps.reports.models import GeneratedReport
from apps.users.models import User
from apps.work_orders import integrity
from apps.work_orders.models import WorkOrder
from apps.work_orders.tests.test_admin_ejecuta_y_corrige import (  # noqa: F401  (fixtures y ayudas)
    client_for,
    crear_ot,
    d,
    ejecutar,
    en_revision,
    make_user,
    transicion,
)

pytestmark = pytest.mark.django_db

FIRMA_REQUERIDA = {
    "code": "firma_requerida",
    "detail": "Registra tu firma en Mi perfil para aprobar esta orden.",
}


def sin_trigger_de_firmas():
    """
    Las firmas son inmutables en la base (trigger). Para simular datos viejos o
    alterados a escondidas, la prueba lo apaga dentro de su transaccion, que se
    deshace al terminar.
    """
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute("SET CONSTRAINTS ALL IMMEDIATE")
        cur.execute("ALTER TABLE evidence_signature DISABLE TRIGGER USER")


def aprobar(user, wo_id):
    return transicion(client_for(user), wo_id, WorkOrder.Status.COMPLETED)


def de_validacion(wo_id):
    return Signature.objects.filter(work_order_id=wo_id, signature_type=Signature.SignatureType.VALIDATION)


# ── Aprobar ──────────────────────────────────────────────────────────────────

def test_sin_firma_guardada_no_se_aprueba(en_revision):
    e = en_revision
    r = aprobar(e["admin"], e["wo_id"])
    assert r.status_code == 400
    assert r.json() == FIRMA_REQUERIDA
    assert WorkOrder.objects.get(pk=e["wo_id"]).status == WorkOrder.Status.IN_REVIEW
    assert not de_validacion(e["wo_id"]).exists()
    assert not GeneratedReport.objects.filter(work_order_id=e["wo_id"]).exists()


def test_si_el_archivo_de_la_firma_guardada_no_existe_tampoco_se_aprueba(en_revision):
    e = en_revision
    saved = firmar(e["admin"])
    default_storage.delete(saved.file_url)
    r = aprobar(e["admin"], e["wo_id"])
    assert r.status_code == 400 and r.json() == FIRMA_REQUERIDA
    assert WorkOrder.objects.get(pk=e["wo_id"]).status == WorkOrder.Status.IN_REVIEW


def test_con_firma_guardada_se_aprueba_y_la_ot_lleva_su_copia(en_revision):
    e = en_revision
    saved = firmar(e["admin"])
    r = aprobar(e["admin"], e["wo_id"])
    assert r.status_code == 200, r.data
    assert r.data["status"] == WorkOrder.Status.COMPLETED

    sig = de_validacion(e["wo_id"]).get()
    assert sig.file_hash == saved.file_hash
    assert sig.file_url != saved.file_url, "la OT lleva un archivo propio"
    assert default_storage.exists(sig.file_url)
    with default_storage.open(sig.file_url) as f:
        assert f.read() == png_bytes((10, 20, 30))
    assert sig.signer_name == "Zz Admin"
    assert sig.signer_role == e["admin"].get_role_display()

    # Aparece en el listado de firmas.
    c = client_for(e["admin"])
    lista = c.get(reverse("evidence-signatures-list"), {"work_order": str(e["wo_id"])}).data
    assert {s["signature_type"] for s in lista} == {"TECHNICIAN", "VALIDATION"}

    log = AuditLog.objects.get(
        entity_type="WorkOrder", entity_id=e["wo_id"], changes__new_status="COMPLETED"
    )
    assert log.changes["firma_guardada"] is True


def test_el_supervisor_tambien_firma_al_aprobar(en_revision):
    e = en_revision
    sup = make_user(User.Role.SUP)
    firmar(sup)
    assert aprobar(sup, e["wo_id"]).status_code == 200
    assert de_validacion(e["wo_id"]).get().signer_name == "Zz Sup"


def test_el_admin_que_ejecuto_la_ot_la_aprueba_con_su_firma(d):
    admin = d["admin"]
    wo_id = crear_ot(d, admin)
    ejecutar(client_for(admin), wo_id, d["campo"])
    assert aprobar(admin, wo_id).json() == FIRMA_REQUERIDA
    firmar(admin)
    assert aprobar(admin, wo_id).status_code == 200
    assert de_validacion(wo_id).count() == 1
    assert Signature.objects.filter(work_order_id=wo_id, signature_type="TECHNICIAN").count() == 1


def test_cambiar_la_firma_guardada_despues_no_altera_la_ot_ni_su_acta(en_revision):
    e = en_revision
    firmar(e["admin"], color=(10, 20, 30))
    assert aprobar(e["admin"], e["wo_id"]).status_code == 200
    wo = WorkOrder.objects.get(pk=e["wo_id"])
    sig = de_validacion(e["wo_id"]).get()
    hash_antes = integrity.compute_wo_content_hash(wo)
    assert integrity.verify_work_order(wo).verified is True

    firmar(e["admin"], color=(200, 0, 0))
    UserSignature.objects.get(user=e["admin"]).delete()

    sig.refresh_from_db()
    with default_storage.open(sig.file_url) as f:
        assert f.read() == png_bytes((10, 20, 30))
    assert integrity.compute_wo_content_hash(wo) == hash_antes
    assert integrity.verify_work_order(wo).verified is True


def test_si_falla_la_creacion_de_la_firma_no_queda_aprobada_ni_con_archivo_huerfano(en_revision, tmp_path):
    e = en_revision
    firmar(e["admin"])
    antes = {p for p in (tmp_path / "media").rglob("*") if p.is_file()}
    with mock.patch.object(Signature.objects, "create", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            aprobar(e["admin"], e["wo_id"])
    assert WorkOrder.objects.get(pk=e["wo_id"]).status == WorkOrder.Status.IN_REVIEW
    assert {p for p in (tmp_path / "media").rglob("*") if p.is_file()} == antes
    assert not de_validacion(e["wo_id"]).exists()


# ── Envio a revision y API publica ────────────────────────────────────────────

def test_la_firma_de_validacion_no_cuenta_como_firma_del_tecnico_al_enviar_a_revision(d):
    from apps.work_orders.transitions import validate_transition

    tec = make_user(User.Role.TEC)
    wo_id = crear_ot(d, tec)
    assert transicion(client_for(tec), wo_id, WorkOrder.Status.IN_PROGRESS).status_code == 200
    wo = WorkOrder.objects.get(pk=wo_id)
    Signature.objects.create(
        work_order=wo, signature_type=Signature.SignatureType.VALIDATION,
        file_url="x.png", signer_name="Alguien", file_hash="h",
    )
    with pytest.raises(ValidationError) as exc:
        validate_transition(wo, WorkOrder.Status.IN_REVIEW, tec)
    assert "capturar la firma digital" in str(exc.value)


@pytest.mark.parametrize("extra", [{}, {"use_saved": True}])
def test_la_api_publica_no_crea_firmas_de_validacion(d, extra):
    tec = make_user(User.Role.TEC)
    wo_id = crear_ot(d, tec)
    c = client_for(tec)
    assert transicion(c, wo_id, WorkOrder.Status.IN_PROGRESS).status_code == 200
    firmar(tec)
    r = c.post(reverse("evidence-signatures-list"), {
        "work_order": str(wo_id), "image_data": base64.b64encode(png_bytes()).decode(),
        "signer_name": "Yo", "signature_type": "VALIDATION", **extra,
    }, format="json")
    assert r.status_code == 400
    assert not de_validacion(wo_id).exists()


# ── Integridad ────────────────────────────────────────────────────────────────

def test_el_acta_nueva_sale_en_v8_y_las_v1_a_v7_siguen_verificando(en_revision):
    assert integrity.INTEGRITY_ALGORITHM_VERSION == "8"
    assert integrity.SUPPORTED_VERSIONS[-1] == "8"
    e = en_revision
    firmar(e["admin"])
    assert aprobar(e["admin"], e["wo_id"]).status_code == 200
    wo = WorkOrder.objects.get(pk=e["wo_id"])
    reporte = GeneratedReport.objects.get(work_order=wo)
    assert reporte.integrity_version == "8"
    assert integrity.verify_work_order(wo).verified is True

    # Un acta calculada con la v7 (sin la firma de validacion) sigue
    # verificando aunque la OT ya tenga una.
    v7 = integrity.compute_wo_content_hash(wo, "7")
    assert "VALIDATION" not in str(integrity.build_integrity_payload(wo, "7"))
    GeneratedReport.objects.filter(pk=reporte.pk).update(integrity_version="7", content_hash=v7)
    assert integrity.verify_work_order(wo).verified is True


def test_el_hash_v8_cambia_si_cambia_la_firma_de_validacion(en_revision):
    e = en_revision
    firmar(e["admin"])
    assert aprobar(e["admin"], e["wo_id"]).status_code == 200
    wo = WorkOrder.objects.get(pk=e["wo_id"])
    v7, v8 = integrity.compute_wo_content_hash(wo, "7"), integrity.compute_wo_content_hash(wo, "8")
    assert "VALIDATION" in str(integrity.build_integrity_payload(wo, "8"))

    sin_trigger_de_firmas()
    de_validacion(wo.id).update(file_hash="0" * 64)
    assert integrity.compute_wo_content_hash(wo, "8") != v8
    assert integrity.verify_work_order(wo).verified is False
    assert integrity.compute_wo_content_hash(wo, "7") == v7, "la v7 no mira esa firma"


# ── Acta ──────────────────────────────────────────────────────────────────────

def _html_del_acta(wo, vista_previa=False):
    from apps.reports import generator
    from apps.reports.options import efectivas

    visto = {}
    real = generator.render_to_string

    def captura(plantilla, contexto):
        visto["html"] = real(plantilla, contexto)
        return visto["html"]

    with mock.patch("apps.reports.generator.render_to_string", side_effect=captura):
        if vista_previa:
            generator.preview_service_report_pdf(wo, {})
        else:
            generator._render(wo, efectivas({}))
    return visto["html"]


def test_el_acta_muestra_la_firma_de_validacion_el_nombre_y_solo_la_fecha(en_revision):
    e = en_revision
    firmar(e["admin"])
    assert aprobar(e["admin"], e["wo_id"]).status_code == 200
    wo = WorkOrder.objects.get(pk=e["wo_id"])
    sig = de_validacion(wo.id).get()

    for previa in (False, True):
        html = _html_del_acta(wo, vista_previa=previa)
        assert 'alt="Firma de validación"' in html
        assert sig.file_url.split("/")[-1] in html
        assert "Zz Admin" in html
        assert "Aprobado en TodoGas CMMS" not in html
        fecha = wo.status_history.filter(to_status="COMPLETED").get().changed_at
        assert f"{fecha:%d/%m/%Y}" in html


def test_una_ot_vieja_sin_firma_de_validacion_sigue_mostrando_el_nombre(en_revision):
    e = en_revision
    firmar(e["admin"])
    assert aprobar(e["admin"], e["wo_id"]).status_code == 200
    wo = WorkOrder.objects.get(pk=e["wo_id"])
    sin_trigger_de_firmas()
    de_validacion(wo.id).delete()  # como una OT completada antes de este cambio

    html = _html_del_acta(wo)
    assert 'alt="Firma de validación"' not in html
    assert "Aprobado en TodoGas CMMS" in html
    assert "Zz Admin" in html
    assert _html_del_acta(wo, vista_previa=True)


def test_la_firma_de_validacion_no_estira_el_periodo_de_trabajo_en_campo(en_revision):
    from apps.reports.generator import field_facts

    e = en_revision
    antes = field_facts(WorkOrder.objects.get(pk=e["wo_id"]))["field_work"]
    firmar(e["admin"])
    assert aprobar(e["admin"], e["wo_id"]).status_code == 200
    assert field_facts(WorkOrder.objects.get(pk=e["wo_id"]))["field_work"]["end"] == antes["end"]
