"""
La OT ya no lleva costo, y la fecha de intervencion se corrige en revision
(decisiones del cliente en la revision del 2026-10: audio3 15:15 "lo del
avance si, el costo no"; audio1 22:02 la fecha de intervencion editable).

- Costo: sale de la API y de la interfaz. La columna se queda en la base (hay
  datos) y nunca entro en el hash de integridad.
- Fecha de intervencion: admin o supervisor fijan inicio y fin con la OT en
  revision. Es una correccion explicita en campos propios (no pisa lo
  calculado), con quien y cuando; el valor anterior va a la auditoria; el
  acta y el correo usan el valor corregido, sin marca. Una OT cerrada no se
  toca. El hash lo incluye desde la version 7; las actas firmadas con la 5 o la 6
  siguen verificando.
"""

from datetime import timedelta
from unittest import mock

import pytest
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status

from apps.evidence.tests.firmas import firmar
from apps.audit.models import AuditLog
from apps.reports.generator import _render, field_facts
from apps.reports.models import GeneratedReport
from apps.reports.options import efectivas
from apps.users.models import User
from apps.work_orders import integrity
from apps.work_orders.models import WorkOrder
from apps.work_orders.tests.test_admin_ejecuta_y_corrige import (  # noqa: F401  (fixtures y ayudas)
    PNG_1PX,
    client_for,
    crear_ot,
    d,
    ejecutar,
    en_revision,
    make_user,
    transicion,
)

pytestmark = pytest.mark.django_db


def url_corregir(wo_id):
    return reverse("work-orders-correct-intervention", kwargs={"pk": wo_id})


def corregir_fecha(user, wo_id, inicio, fin):
    return client_for(user).post(
        url_corregir(wo_id),
        {"start": inicio.isoformat(), "end": fin.isoformat()},
        format="json",
    )


@pytest.fixture
def revision_antigua(en_revision):
    """
    Una OT en revision creada hace 3 dias: la fecha corregida tiene que caer
    despues de que existio la OT, y en la prueba la OT se acaba de crear.
    """
    WorkOrder.objects.filter(pk=en_revision["wo_id"]).update(created_at=timezone.now() - timedelta(days=3))
    return en_revision


def _ventana():
    ahora = timezone.now()
    return ahora - timedelta(hours=26), ahora - timedelta(hours=25)


# ── A. El costo ya no existe para el usuario ────────────────────────────────

def test_el_detalle_de_la_ot_no_trae_costo(en_revision):
    e = en_revision
    for user in (e["admin"], e["tec"]):
        datos = client_for(user).get(reverse("work-orders-detail", kwargs={"pk": e["wo_id"]})).data
        assert "total_cost" not in datos


def test_el_listado_de_ots_no_trae_costo(en_revision):
    filas = client_for(en_revision["admin"]).get(reverse("work-orders-list")).data["results"]
    assert filas and all("total_cost" not in f for f in filas)


def test_nadie_escribe_un_costo_en_la_ot(en_revision):
    e = en_revision
    WorkOrder.objects.filter(pk=e["wo_id"]).update(total_cost=0)
    url = reverse("work-orders-detail", kwargs={"pk": e["wo_id"]})
    for user in (e["admin"], e["tec"]):
        client_for(user).patch(url, {"total_cost": "999.99", "notes": "hola"}, format="json")
        assert WorkOrder.objects.get(pk=e["wo_id"]).total_cost == 0


def test_la_columna_del_costo_sigue_en_la_base_y_no_entra_en_el_hash(en_revision):
    # No se borra: hay datos. Y cambiarla no mueve el hash de ninguna version,
    # asi que las actas ya emitidas siguen verificando igual.
    wo = WorkOrder.objects.get(pk=en_revision["wo_id"])
    assert WorkOrder._meta.get_field("total_cost")
    antes = {v: integrity.compute_wo_content_hash(wo, v) for v in ("1", "2", "3", "4", "5")}
    WorkOrder.objects.filter(pk=wo.pk).update(total_cost=1234)
    wo.refresh_from_db()
    assert {v: integrity.compute_wo_content_hash(wo, v) for v in antes} == antes
    assert "total_cost" not in str(integrity.build_integrity_payload(wo))


# ── B. Corregir la fecha de intervencion ────────────────────────────────────

def test_el_admin_corrige_la_fecha_de_intervencion_en_revision(revision_antigua):
    e = revision_antigua
    wo_id = e["wo_id"]
    calculado = field_facts(WorkOrder.objects.get(pk=wo_id))["field_work"]
    inicio, fin = _ventana()

    r = corregir_fecha(e["admin"], wo_id, inicio, fin)
    assert r.status_code == 200, r.data
    assert parse_datetime(r.data["intervention_start_override"]) == inicio
    assert parse_datetime(r.data["intervention_end_override"]) == fin
    assert r.data["intervention_corrected_by_name"] == "Zz Admin"
    assert r.data["intervention_corrected_at"] is not None

    wo = WorkOrder.objects.get(pk=wo_id)
    assert wo.intervention_start_override == inicio and wo.intervention_end_override == fin
    assert wo.intervention_corrected_by == e["admin"] and wo.intervention_corrected_at is not None

    # El detalle trae la constancia para pintar "Corregido por".
    detalle = client_for(e["tec"]).get(reverse("work-orders-detail", kwargs={"pk": wo_id})).data
    assert detalle["intervention_corrected_by_name"] == "Zz Admin"
    # Y el valor calculado sigue ahi, sin pisarse.
    assert field_facts(wo)["field_work"]["start"] == inicio
    assert calculado["start"] != inicio


def test_la_correccion_deja_el_valor_anterior_en_la_auditoria(revision_antigua):
    e = revision_antigua
    wo_id = e["wo_id"]
    calculado = field_facts(WorkOrder.objects.get(pk=wo_id))["field_work"]
    inicio, fin = _ventana()
    assert corregir_fecha(e["admin"], wo_id, inicio, fin).status_code == 200

    log = AuditLog.objects.get(entity_type="WorkOrder", entity_id=wo_id, changes__correccion=True,
                               changes__has_key="intervention_start")
    assert log.user == e["admin"]
    assert parse_datetime(log.changes["intervention_start"]["from"]) == calculado["start"]
    assert parse_datetime(log.changes["intervention_start"]["to"]) == inicio
    assert parse_datetime(log.changes["intervention_end"]["from"]) == calculado["end"]
    assert parse_datetime(log.changes["intervention_end"]["to"]) == fin

    # Una segunda correccion deja como "anterior" la primera, no lo calculado.
    inicio2, fin2 = inicio - timedelta(hours=1), fin - timedelta(hours=1)
    assert corregir_fecha(e["admin"], wo_id, inicio2, fin2).status_code == 200
    ultimo = AuditLog.objects.filter(entity_type="WorkOrder", entity_id=wo_id,
                                     changes__has_key="intervention_start").order_by("-created_at").first()
    assert parse_datetime(ultimo.changes["intervention_start"]["from"]) == inicio
    assert parse_datetime(ultimo.changes["intervention_start"]["to"]) == inicio2


def test_lo_que_registro_el_tecnico_no_se_pisa(revision_antigua):
    from apps.checklists.models import ChecklistFieldResponse
    from apps.evidence.models import Photo

    e = revision_antigua
    horas = lambda: (
        [fr.answered_at for fr in ChecklistFieldResponse.objects.filter(response_id=e["cr"])],
        [p.taken_at for p in Photo.objects.filter(work_order_id=e["wo_id"])],
    )
    antes = horas()
    inicio, fin = _ventana()
    assert corregir_fecha(e["admin"], e["wo_id"], inicio, fin).status_code == 200
    assert horas() == antes


def test_el_acta_y_el_correo_usan_la_fecha_corregida_sin_marca(revision_antigua):
    e = revision_antigua
    inicio, fin = _ventana()
    assert corregir_fecha(e["admin"], e["wo_id"], inicio, fin).status_code == 200
    firmar(e["admin"])
    assert transicion(client_for(e["admin"]), e["wo_id"], WorkOrder.Status.COMPLETED).status_code == 200

    wo = WorkOrder.objects.get(pk=e["wo_id"])
    with mock.patch("apps.reports.generator.render_to_string", return_value="<p></p>") as r:
        _render(wo, efectivas({}))
    contexto = r.call_args.args[1]
    assert contexto["field_work"]["start"] == inicio and contexto["field_work"]["end"] == fin
    assert contexto["field_work"]["duration"], "la duracion sale de la fecha corregida"
    assert not any("correg" in str(v).lower() for v in contexto["field_work"].values())

    hechos = field_facts(wo)
    assert hechos["field_work"]["start"] == inicio and hechos["field_work"]["end"] == fin


def test_sin_correccion_el_acta_sigue_diciendo_lo_calculado(revision_antigua):
    wo = WorkOrder.objects.get(pk=revision_antigua["wo_id"])
    assert wo.intervention_start_override is None and wo.intervention_end_override is None
    horas = field_facts(wo)["field_work"]
    assert horas["start"] <= horas["end"]


# ── Quien puede, y cuando ───────────────────────────────────────────────────

def test_el_supervisor_de_su_hospital_corrige_y_el_de_otro_no(revision_antigua):
    e = revision_antigua
    inicio, fin = _ventana()
    ajeno = make_user(User.Role.SUP, hospital=e["otro"])
    assert corregir_fecha(ajeno, e["wo_id"], inicio, fin).status_code == 404
    sup = make_user(User.Role.SUP, hospital=e["h"])
    assert corregir_fecha(sup, e["wo_id"], inicio, fin).status_code == 200
    assert WorkOrder.objects.get(pk=e["wo_id"]).intervention_corrected_by == sup


def test_ni_el_tecnico_ni_el_hospital_corrigen_la_fecha(revision_antigua):
    e = revision_antigua
    inicio, fin = _ventana()
    assert corregir_fecha(e["tec"], e["wo_id"], inicio, fin).status_code == 403
    cli = make_user(User.Role.CLI, hospital=e["h"])
    assert corregir_fecha(cli, e["wo_id"], inicio, fin).status_code in (403, 404)
    assert WorkOrder.objects.get(pk=e["wo_id"]).intervention_start_override is None


def test_solo_se_corrige_con_la_ot_en_revision(revision_antigua):
    e = revision_antigua
    inicio, fin = _ventana()
    admin = client_for(e["admin"])

    # Devuelta al tecnico, en proceso: ahi manda lo que registre el.
    assert transicion(admin, e["wo_id"], WorkOrder.Status.IN_PROGRESS).status_code == 200
    r = corregir_fecha(e["admin"], e["wo_id"], inicio, fin)
    assert r.status_code == 400
    assert "revisión" in str(r.data)

    # Cerrada: inalterable.
    assert transicion(client_for(e["tec"]), e["wo_id"], WorkOrder.Status.IN_REVIEW).status_code == 200
    firmar(e["admin"])
    assert transicion(admin, e["wo_id"], WorkOrder.Status.COMPLETED).status_code == 200
    assert corregir_fecha(e["admin"], e["wo_id"], inicio, fin).status_code == 400
    wo = WorkOrder.objects.get(pk=e["wo_id"])
    assert wo.intervention_start_override is None and wo.intervention_corrected_by is None
    assert not AuditLog.objects.filter(entity_type="WorkOrder", entity_id=e["wo_id"],
                                       changes__has_key="intervention_start").exists()


# ── Validaciones ────────────────────────────────────────────────────────────

def test_el_fin_no_puede_ser_antes_del_inicio(revision_antigua):
    e = revision_antigua
    inicio, fin = _ventana()
    r = corregir_fecha(e["admin"], e["wo_id"], fin, inicio)
    assert r.status_code == 400
    assert "end" in r.data


def test_no_se_acepta_una_fecha_en_el_futuro(revision_antigua):
    e = revision_antigua
    ahora = timezone.now()
    r = corregir_fecha(e["admin"], e["wo_id"], ahora - timedelta(hours=1), ahora + timedelta(hours=2))
    assert r.status_code == 400
    assert "end" in r.data
    assert WorkOrder.objects.get(pk=e["wo_id"]).intervention_end_override is None


def test_no_se_acepta_una_fecha_anterior_a_la_creacion_de_la_ot(revision_antigua):
    e = revision_antigua
    creada = WorkOrder.objects.get(pk=e["wo_id"]).created_at
    r = corregir_fecha(e["admin"], e["wo_id"], creada - timedelta(days=1), creada + timedelta(hours=1))
    assert r.status_code == 400
    assert "start" in r.data


def test_sin_fechas_o_con_texto_basura_es_400(revision_antigua):
    e = revision_antigua
    c = client_for(e["admin"])
    assert c.post(url_corregir(e["wo_id"]), {}, format="json").status_code == 400
    assert c.post(url_corregir(e["wo_id"]), {"start": "ayer", "end": "hoy"}, format="json").status_code == 400


def test_quitar_la_correccion_vuelve_a_lo_calculado(revision_antigua):
    e = revision_antigua
    inicio, fin = _ventana()
    assert corregir_fecha(e["admin"], e["wo_id"], inicio, fin).status_code == 200
    r = client_for(e["admin"]).post(url_corregir(e["wo_id"]), {"start": None, "end": None}, format="json")
    assert r.status_code == 200, r.data
    wo = WorkOrder.objects.get(pk=e["wo_id"])
    assert wo.intervention_start_override is None and wo.intervention_end_override is None
    assert field_facts(wo)["field_work"]["start"] != inicio


# ── Integridad: version 7 ───────────────────────────────────────────────────

def test_el_hash_de_la_version_7_incluye_la_fecha_corregida_y_los_anteriores_no_cambian(revision_antigua):
    e = revision_antigua
    wo = WorkOrder.objects.get(pk=e["wo_id"])
    assert integrity.INTEGRITY_ALGORITHM_VERSION == "8"
    assert "7" in integrity.SUPPORTED_VERSIONS
    v5, v6, v7 = (integrity.compute_wo_content_hash(wo, v) for v in ("5", "6", "7"))

    inicio, fin = _ventana()
    assert corregir_fecha(e["admin"], e["wo_id"], inicio, fin).status_code == 200
    wo.refresh_from_db()
    assert integrity.compute_wo_content_hash(wo, "5") == v5, "las actas viejas siguen verificando"
    assert integrity.compute_wo_content_hash(wo, "6") == v6
    assert integrity.compute_wo_content_hash(wo, "7") != v7

    # Quitar la correccion devuelve el hash de la version 7 al de antes.
    WorkOrder.objects.filter(pk=wo.pk).update(intervention_start_override=None, intervention_end_override=None)
    wo.refresh_from_db()
    assert integrity.compute_wo_content_hash(wo, "7") == v7


def test_un_acta_nueva_sale_en_la_version_vigente_y_cambiar_la_fecha_despues_la_rompe(revision_antigua):
    e = revision_antigua
    inicio, fin = _ventana()
    assert corregir_fecha(e["admin"], e["wo_id"], inicio, fin).status_code == 200
    firmar(e["admin"])
    assert transicion(client_for(e["admin"]), e["wo_id"], WorkOrder.Status.COMPLETED).status_code == 200

    reporte = GeneratedReport.objects.get(work_order_id=e["wo_id"])
    assert reporte.integrity_version == integrity.INTEGRITY_ALGORITHM_VERSION
    wo = WorkOrder.objects.get(pk=e["wo_id"])
    assert integrity.verify_work_order(wo).verified is True

    # Mover la fecha a escondidas, ya cerrada, tiene que verse.
    WorkOrder.objects.filter(pk=wo.pk).update(intervention_end_override=fin + timedelta(minutes=30))
    wo.refresh_from_db()
    assert integrity.verify_work_order(wo).verified is False


@pytest.mark.parametrize("version", ["5", "6"])
def test_un_acta_de_una_version_anterior_sigue_verificando_aunque_la_ot_tenga_fecha_corregida(revision_antigua, version):
    e = revision_antigua
    firmar(e["admin"])
    assert transicion(client_for(e["admin"]), e["wo_id"], WorkOrder.Status.COMPLETED).status_code == 200
    wo = WorkOrder.objects.get(pk=e["wo_id"])
    # Se simula un acta firmada antes de la version 7.
    GeneratedReport.objects.filter(work_order=wo).update(
        integrity_version=version, content_hash=integrity.compute_wo_content_hash(wo, version),
    )
    assert integrity.verify_work_order(wo).verified is True
    inicio, fin = _ventana()
    WorkOrder.objects.filter(pk=wo.pk).update(intervention_start_override=inicio, intervention_end_override=fin)
    wo.refresh_from_db()
    assert integrity.verify_work_order(wo).verified is True


def test_la_cuenta_de_hospital_no_ve_quien_corrigio_la_fecha(revision_antigua):
    e = revision_antigua
    inicio, fin = _ventana()
    assert corregir_fecha(e["admin"], e["wo_id"], inicio, fin).status_code == 200
    cli = make_user(User.Role.CLI, hospital=e["h"])
    datos = client_for(cli).get(reverse("work-orders-detail", kwargs={"pk": e["wo_id"]})).data
    assert not [k for k in datos if k.startswith("intervention")]
