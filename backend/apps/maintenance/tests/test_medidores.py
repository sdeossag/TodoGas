"""
Medidores y activadores por medidor (decision del 2026-09-24): las lecturas
salen del checklist (cuentan al sincronizar y se corrigen con la respuesta) o
se registran a mano; "cada N horas" abre la tarea cuando el uso acumulado
llega, y "cuando" la abre al cruzar un umbral y avisa por correo.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core import mail
from django.utils import timezone
from model_bakery import baker
from rest_framework.test import APIClient

from apps.assets.meters import meter_for, record_manual
from apps.assets.models import Asset, Hospital, MeterReading, MeterUnit
from apps.checklists.models import (
    ChecklistField,
    ChecklistTemplate,
    ChecklistTemplateVersion,
)
from apps.maintenance import services
from apps.maintenance.models import MaintenancePlan, MeterSchedule, PlanTask, Task
from apps.users.models import User
from apps.work_orders.models import WorkOrder

pytestmark = pytest.mark.django_db
AHORA = timezone.now()


def cliente(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def unidad(symbol):
    return MeterUnit.objects.get(symbol=symbol)


@pytest.fixture
def d():
    h = baker.make(Hospital, is_active=True)
    return {
        "h": h,
        "admin": baker.make(User, role=User.Role.ADMIN, is_active=True, email="jefe@todogas.co"),
        "sup": baker.make(User, role=User.Role.SUP, is_active=True),
        "tec": baker.make(User, role=User.Role.TEC, is_active=True),
        "bomba": Asset.objects.create(hospital=h, name="Bomba de vacío", code="BV-1"),
    }


def plan_con(asset, trigger, **campos):
    plan = MaintenancePlan.objects.create(name=f"PLAN {trigger} {PlanTask.objects.count()}")
    pt = PlanTask.objects.create(plan=plan, name=f"Tarea {trigger}", trigger=trigger, **campos)
    services.set_asset_plan(asset, plan)
    return pt


def leer(asset, symbol, valor, minutos=0, **kw):
    return record_manual(
        meter_for(asset, unidad(symbol)), Decimal(str(valor)), AHORA + timedelta(minutes=minutos), **kw,
    )


def abiertas(pt, asset):
    return list(Task.objects.filter(plan_task=pt, asset=asset, status__in=Task.OPEN_STATUSES))


# ── Unidades y acumulado ─────────────────────────────────────────────────────

def test_arranca_con_las_seis_unidades_del_cliente():
    assert set(MeterUnit.objects.values_list("name", "symbol")) == {
        ("AMPERIOS", "A"), ("HORAS", "H"), ("PRESION", "inHg"),
        ("PRESION", "PSI"), ("TEMPERATURA", "°C"), ("VOLTAJE", "V"),
    }
    assert list(MeterUnit.objects.filter(is_counter=True).values_list("symbol", flat=True)) == ["H"]


def test_el_acumulado_aguanta_el_reinicio_del_horometro(d):
    leer(d["bomba"], "H", 12000, 0)
    leer(d["bomba"], "H", 12050, 1)
    leer(d["bomba"], "H", 30, 2)            # se cambio el horometro: baja
    leer(d["bomba"], "H", 80, 3)
    ultima = leer(d["bomba"], "H", 10, 4, is_reset=True)
    assert ultima.accumulated == Decimal(12140)
    psi = leer(d["bomba"], "PSI", 45, 0)
    assert psi.accumulated is None, "una presion no acumula"


# ── Lecturas desde el checklist ──────────────────────────────────────────────

def _checklist_con_medidor(admin, symbol):
    t = ChecklistTemplate.objects.create(name=f"Preventivo bomba {symbol}")
    v = ChecklistTemplateVersion.objects.create(template=t, version_number=1, published_by=admin, is_current=True)
    campo = ChecklistField.objects.create(
        version=v, label=f"Lectura {symbol}", field_type=ChecklistField.FieldType.METER,
        options_json={"unit": symbol, "meter_unit": str(unidad(symbol).id)},
    )
    return t, campo


def test_la_lectura_del_checklist_llega_al_medidor_y_se_corrige_con_la_respuesta(d):
    t, campo = _checklist_con_medidor(d["admin"], "H")
    plan = MaintenancePlan.objects.create(name="PREVENTIVO BOMBA")
    PlanTask.objects.create(plan=plan, name="Preventivo", checklist_template=t,
                            frequency_value=6, frequency_unit="MONTHS")
    services.set_asset_plan(d["bomba"], plan)
    tarea = Task.objects.get(plan_task__plan=plan, asset=d["bomba"])
    ot, _ = services.create_work_order_for_tasks([tarea], d["admin"])
    ot.assigned_to = d["tec"]
    ot.status = WorkOrder.Status.IN_PROGRESS
    ot.save()
    respuesta = tarea.checklist_response
    c = cliente(d["tec"])
    url = f"/api/checklists/responses/{respuesta.id}/submit-field/"

    r = c.post(url, {"field": str(campo.id), "value": "582.5"}, format="json")
    assert r.status_code == 200, r.data
    lectura = MeterReading.objects.get()
    assert (lectura.value, lectura.source, lectura.task_id) == (Decimal("582.5"), "CHECKLIST", tarea.id)
    assert lectura.meter.asset == d["bomba"] and lectura.meter.unit.symbol == "H"

    c.post(url, {"field": str(campo.id), "value": "583"}, format="json")
    assert MeterReading.objects.get().value == Decimal(583), "corregir la respuesta corrige la lectura"


def test_un_campo_sin_unidad_no_deja_lectura(d):
    _, campo = _checklist_con_medidor(d["admin"], "H")
    ChecklistField.objects.filter(pk=campo.pk).update(options_json={"unit": "H"})
    from apps.assets.meters import record_from_checklist
    from apps.checklists.models import ChecklistFieldResponse

    fr = ChecklistFieldResponse(field=ChecklistField.objects.get(pk=campo.pk), value="10")
    assert record_from_checklist(fr) is None


# ── "Cada N horas" ───────────────────────────────────────────────────────────

def test_cada_n_horas_empieza_a_contar_con_la_primera_lectura(d):
    pt = plan_con(d["bomba"], "EVERY", meter_unit=unidad("H"), meter_interval=Decimal(500))
    assert not MeterSchedule.objects.exists(), "sin lecturas no hay desde donde contar"
    leer(d["bomba"], "H", 12000, 0)
    assert abiertas(pt, d["bomba"]) == [], "un horometro viejo no vence al instante"
    assert MeterSchedule.objects.get().next_due == Decimal(12500)
    leer(d["bomba"], "H", 12400, 1)
    assert abiertas(pt, d["bomba"]) == []
    lectura = leer(d["bomba"], "H", 12510, 2)
    [tarea] = abiertas(pt, d["bomba"])
    assert tarea.trigger_reading == lectura and tarea.meter_due == Decimal(12500)
    assert tarea.scheduled_date == timezone.localdate()
    leer(d["bomba"], "H", 12600, 3)
    assert len(abiertas(pt, d["bomba"])) == 1, "una sola abierta a la vez"


@pytest.mark.parametrize("fija, siguiente", [(False, "13120"), (True, "13000")])
def test_al_cerrar_el_siguiente_vencimiento(d, fija, siguiente):
    pt = plan_con(d["bomba"], "EVERY", meter_unit=unidad("H"), meter_interval=Decimal(500),
                  fixed_schedule=fija)
    leer(d["bomba"], "H", 12000, 0)
    leer(d["bomba"], "H", 12620, 1)         # vencia en 12500 y se leyo tarde
    [tarea] = abiertas(pt, d["bomba"])
    ot, _ = services.create_work_order_for_tasks([tarea], d["admin"])
    ot.status = WorkOrder.Status.COMPLETED
    ot.completed_at = AHORA + timedelta(minutes=5)
    ot.save()
    services.complete_work_order_tasks(ot)
    assert MeterSchedule.objects.get().next_due == Decimal(siguiente)
    assert abiertas(pt, d["bomba"]) == [], "no abre la siguiente hasta que el uso llegue"


# ── "Cuando" ─────────────────────────────────────────────────────────────────

def test_cuando_la_presion_baja_abre_la_tarea_y_avisa(d, django_capture_on_commit_callbacks):
    pt = plan_con(d["bomba"], "WHEN", meter_unit=unidad("PSI"), meter_comparator="LT",
                  meter_threshold=Decimal(50))
    leer(d["bomba"], "PSI", 55, 0)
    assert abiertas(pt, d["bomba"]) == [] and mail.outbox == []
    # El correo sale al confirmar la transaccion.
    with django_capture_on_commit_callbacks(execute=True):
        lectura = leer(d["bomba"], "PSI", 45, 1)
    [tarea] = abiertas(pt, d["bomba"])
    assert tarea.trigger_reading == lectura
    assert len(mail.outbox) == 1 and mail.outbox[0].to == ["jefe@todogas.co"]
    assert "45" in mail.outbox[0].body and "menor que 50" in mail.outbox[0].body
    with django_capture_on_commit_callbacks(execute=True):
        leer(d["bomba"], "PSI", 40, 2)
    assert len(abiertas(pt, d["bomba"])) == 1 and len(mail.outbox) == 1


def test_una_lectura_vieja_no_dispara(d):
    pt = plan_con(d["bomba"], "WHEN", meter_unit=unidad("PSI"), meter_comparator="LT",
                  meter_threshold=Decimal(50))
    leer(d["bomba"], "PSI", 60, 10)
    leer(d["bomba"], "PSI", 45, 0)          # registrada despues, pero de antes
    assert abiertas(pt, d["bomba"]) == []


def test_otra_unidad_u_otro_plan_no_dispara(d):
    pt = plan_con(d["bomba"], "WHEN", meter_unit=unidad("PSI"), meter_comparator="GT",
                  meter_threshold=Decimal(100))
    leer(d["bomba"], "inHg", 200, 0)
    otra = Asset.objects.create(hospital=d["h"], name="Otra", code="BV-2")
    leer(otra, "PSI", 200, 0)
    assert not Task.objects.filter(plan_task=pt).exists()


# ── Configuracion de la tarea del plan ───────────────────────────────────────

def test_validacion_de_los_activadores(d):
    plan = MaintenancePlan.objects.create(name="VALIDAR")
    c = cliente(d["admin"])
    base = {"plan": str(plan.id), "name": "X"}
    r = c.post("/api/maintenance/plan-tasks/", {**base, "trigger": "EVERY", "meter_unit": str(unidad("PSI").id),
                                                "meter_interval": "10"}, format="json")
    assert r.status_code == 400 and "no acumula" in str(r.data["meter_unit"])
    r = c.post("/api/maintenance/plan-tasks/", {**base, "trigger": "WHEN", "meter_unit": str(unidad("PSI").id)},
               format="json")
    assert r.status_code == 400 and {"meter_comparator", "meter_threshold"} <= set(r.data)
    r = c.post("/api/maintenance/plan-tasks/", {**base, "trigger": "WHEN", "meter_unit": str(unidad("PSI").id),
                                                "meter_comparator": "LT", "meter_threshold": "50"}, format="json")
    assert r.status_code == 201, r.data
    assert r.data["meter_unit_label"] == "PRESION (PSI)"


def test_pasar_de_fecha_a_umbral_anula_la_pendiente_por_fecha(d):
    pt = plan_con(d["bomba"], "DATE", frequency_value=6, frequency_unit="MONTHS")
    [pendiente] = abiertas(pt, d["bomba"])
    r = cliente(d["admin"]).patch(f"/api/maintenance/plan-tasks/{pt.id}/", {
        "trigger": "WHEN", "meter_unit": str(unidad("PSI").id), "meter_comparator": "LT", "meter_threshold": "50",
    }, format="json")
    assert r.status_code == 200, r.data
    pendiente.refresh_from_db()
    assert pendiente.status == "CANCELLED" and "umbral del medidor" in pendiente.cancellation_note


# ── API de lecturas ──────────────────────────────────────────────────────────

def test_el_supervisor_registra_a_mano_y_el_tecnico_no(d):
    meter = meter_for(d["bomba"], unidad("H"))
    datos = {"meter": str(meter.id), "value": "120.5", "note": "Lectura de ronda"}
    assert cliente(d["tec"]).post("/api/meter-readings/", datos, format="json").status_code == 403
    r = cliente(d["sup"]).post("/api/meter-readings/", datos, format="json")
    assert r.status_code == 201, r.data
    assert r.data["value"] == 120.5 and r.data["source"] == "MANUAL" and r.data["accumulated"] == 120.5
    r = cliente(d["tec"]).get(f"/api/meters/?asset_id={d['bomba'].id}")
    assert r.data[0]["last_reading"]["value"] == 120.5


def test_la_ficha_dice_cuanto_falta(d):
    plan_con(d["bomba"], "EVERY", meter_unit=unidad("H"), meter_interval=Decimal(500))
    leer(d["bomba"], "H", 1000, 0)
    leer(d["bomba"], "H", 1380, 1)
    r = cliente(d["admin"]).get(f"/api/meters/?asset_id={d['bomba'].id}")
    [disparo] = r.data[0]["triggers"]
    assert (disparo["next_due"], disparo["remaining"]) == (1500, 120)


def test_solo_se_borran_las_manuales_que_no_abrieron_tarea(d):
    plan_con(d["bomba"], "WHEN", meter_unit=unidad("PSI"), meter_comparator="LT", meter_threshold=Decimal(50))
    ok = leer(d["bomba"], "PSI", 60, 0)
    disparo = leer(d["bomba"], "PSI", 40, 1)
    c = cliente(d["admin"])
    assert c.delete(f"/api/meter-readings/{disparo.id}/").status_code == 400
    assert c.delete(f"/api/meter-readings/{ok.id}/").status_code == 204


def test_otro_hospital_no_ve_las_lecturas(d):
    leer(d["bomba"], "H", 10, 0)
    otro = baker.make(Hospital, is_active=True)
    cli = baker.make(User, role=User.Role.CLI, is_active=True, hospital=otro)
    assert cliente(cli).get("/api/meter-readings/").data["results"] == []
    assert cliente(cli).get("/api/meters/").data == []
