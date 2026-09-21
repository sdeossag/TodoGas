"""Ciclo de vida de las tareas (diseno aprobado el 2026-09-21, fase 1).

Cada prueba corresponde a una regla del diseno, y las que vienen de lo que se
verifico en el Fracttal del cliente lo dicen.
"""

from datetime import date, timedelta

import pytest
from dateutil.relativedelta import relativedelta
from django.db import IntegrityError, transaction
from django.utils import timezone
from model_bakery import baker

from apps.assets.models import Asset, Hospital
from apps.checklists.models import ChecklistTemplate, ChecklistTemplateVersion
from apps.maintenance import services
from apps.maintenance.models import PlanTask, RescheduleCause, Task, TaskReschedule
from apps.maintenance.testing import make_plan, make_work_order, pending_task
from apps.users.models import User
from apps.work_orders.models import WorkOrder

HOY = date.today()


@pytest.fixture
def admin(db):
    return baker.make(User, role=User.Role.ADMIN, is_active=True)


@pytest.fixture
def hospital(db):
    return baker.make(Hospital, is_active=True)


@pytest.fixture
def otro_hospital(db):
    return baker.make(Hospital, is_active=True)


def activo(hospital, **extra):
    extra.setdefault("status", Asset.Status.ACTIVE)
    return baker.make(Asset, hospital=hospital, **extra)


def cerrar(ot, cuando=None):
    ot.status = WorkOrder.Status.COMPLETED
    ot.completed_at = cuando or timezone.now()
    ot.save()
    return services.complete_work_order_tasks(ot)


# ── Asignar el plan a un activo (D7) ──────────────────────────────────────────

def test_asignar_plan_crea_la_primera_pendiente(hospital):
    a = activo(hospital)
    plan = make_plan("Alarmas", next_due_date=HOY + timedelta(days=20))

    services.set_asset_plan(a, plan)

    tarea = pending_task(plan, a)
    assert tarea.status == Task.Status.PENDING
    assert tarea.calculated_date == tarea.scheduled_date == HOY + timedelta(days=20)
    a.refresh_from_db()
    assert a.plan == plan


def test_cambiar_de_plan_hereda_la_fecha(hospital):
    """Audio 2 [18:39]: las tomas pasan de 3 a 4. El ciclo no vuelve a empezar."""
    a = activo(hospital)
    tres = make_plan("3 TOMAS", assets=[a], next_due_date=HOY + timedelta(days=40))
    cuatro = make_plan("4 TOMAS", next_due_date=HOY + timedelta(days=200))

    services.set_asset_plan(a, cuatro)

    vieja = Task.objects.get(plan_task__plan=tres, asset=a)
    assert vieja.status == Task.Status.CANCELLED
    assert "4 TOMAS" in vieja.cancellation_note
    nueva = pending_task(cuatro, a)
    assert nueva.scheduled_date == HOY + timedelta(days=40), "hereda la fecha, no la del plan nuevo"


def test_quitar_el_plan_anula_la_pendiente(hospital):
    a = activo(hospital)
    plan = make_plan("Alarmas", assets=[a])

    services.set_asset_plan(a, None)

    assert pending_task(plan, a) is None
    assert Task.objects.get(asset=a).status == Task.Status.CANCELLED


def test_asignar_a_varios_deja_exactamente_esos(hospital):
    a, b, c = activo(hospital), activo(hospital), activo(hospital)
    plan = make_plan("Cajas", assets=[a, b])

    services.assign_plan_to_assets(plan, [b, c])

    assert set(plan.assets.all()) == {b, c}
    assert pending_task(plan, a) is None
    assert pending_task(plan, c) is not None


def test_activo_dado_de_baja_no_genera(hospital):
    a = activo(hospital, status=Asset.Status.DECOMMISSIONED)
    plan = make_plan("Alarmas", assets=[a])

    assert pending_task(plan, a) is None


# ── Una sola tarea abierta por tarea del plan y activo ───────────────────────

def test_ensure_open_task_es_idempotente(hospital):
    a = activo(hospital)
    plan = make_plan("Alarmas", assets=[a])
    plan_task = plan.tasks.get()

    tarea, creada = services.ensure_open_task(plan_task, a)

    assert creada is False
    assert tarea == pending_task(plan, a)
    assert Task.objects.filter(plan_task=plan_task, asset=a).count() == 1


def test_la_base_impide_dos_tareas_abiertas(hospital):
    a = activo(hospital)
    plan = make_plan("Alarmas", assets=[a])
    existente = pending_task(plan, a)

    with pytest.raises(IntegrityError), transaction.atomic():
        Task.objects.create(
            asset=a, plan_task=existente.plan_task, status=Task.Status.PENDING,
            title="duplicada", task_type="PREVENTIVE",
            calculated_date=HOY, scheduled_date=HOY,
        )


def test_la_base_impide_pendiente_con_ot(hospital, admin):
    a = activo(hospital)
    ot = make_work_order(a, admin)

    with pytest.raises(IntegrityError), transaction.atomic():
        Task.objects.create(
            asset=a, work_order=ot, status=Task.Status.PENDING,
            title="incoherente", task_type="CORRECTIVE",
            calculated_date=HOY, scheduled_date=HOY,
        )


# ── Cerrar la OT: la siguiente ocurrencia (D3) ───────────────────────────────

def test_sin_programacion_fija_cuenta_desde_la_realizacion(hospital, admin):
    """Como el cliente: calculada = realizacion anterior + frecuencia."""
    a = activo(hospital)
    plan = make_plan("Alarmas", assets=[a], next_due_date=HOY - timedelta(days=10))
    ot, _ = services.create_work_order_for_tasks([pending_task(plan, a)], admin)
    hecho = timezone.now()

    cerrar(ot, hecho)

    siguiente = pending_task(plan, a)
    assert siguiente.calculated_date == timezone.localdate(hecho) + relativedelta(months=6)


def test_con_programacion_fija_cuenta_desde_la_calculada(hospital, admin):
    a = activo(hospital)
    due = HOY - timedelta(days=10)
    plan = make_plan("Alarmas", assets=[a], next_due_date=due, fixed_schedule=True)
    ot, _ = services.create_work_order_for_tasks([pending_task(plan, a)], admin)

    cerrar(ot)

    assert pending_task(plan, a).calculated_date == due + relativedelta(months=6)


def test_cerrar_marca_las_tareas_finalizadas(hospital, admin):
    a = activo(hospital)
    plan = make_plan("Alarmas", assets=[a])
    tarea = pending_task(plan, a)
    ot, _ = services.create_work_order_for_tasks([tarea], admin)

    cerrar(ot)

    tarea.refresh_from_db()
    assert tarea.status == Task.Status.DONE
    assert tarea.completed_at == ot.completed_at


def test_repetir_por_n_deja_de_generar(hospital, admin):
    """Fracttal: Repetir por 1 = tarea de un solo uso (pruebas de instalacion)."""
    a = activo(hospital)
    plan = make_plan("Instalacion", assets=[a])
    PlanTask.objects.filter(plan=plan).update(repeat_count=1)
    ot, _ = services.create_work_order_for_tasks([pending_task(plan, a)], admin)

    siguientes = cerrar(ot)

    assert siguientes == []
    assert pending_task(plan, a) is None


def test_plan_pausado_no_genera_la_siguiente(hospital, admin):
    a = activo(hospital)
    plan = make_plan("Alarmas", assets=[a])
    ot, _ = services.create_work_order_for_tasks([pending_task(plan, a)], admin)
    plan.is_active = False
    plan.save()

    assert cerrar(ot) == []


# ── Cancelar la OT (D6) ───────────────────────────────────────────────────────

def test_cancelar_la_ot_reemite_las_tareas_con_su_fecha(hospital, admin):
    """Como la 19453 -> 19454 del cliente."""
    a, b = activo(hospital), activo(hospital)
    plan = make_plan("Piso 3", assets=[a, b], next_due_date=HOY - timedelta(days=2))
    tareas = [pending_task(plan, a), pending_task(plan, b)]
    ot, _ = services.create_work_order_for_tasks(tareas, admin)
    ot.status = WorkOrder.Status.CANCELLED
    ot.save()

    reemitidas = services.cancel_work_order_tasks(ot)

    for t in tareas:
        t.refresh_from_db()
        assert t.status == Task.Status.CANCELLED
        assert t.work_order == ot, "quedan con la OT cancelada como registro"
        assert ot.wo_code in t.cancellation_note
    assert len(reemitidas) == 2
    for nueva in reemitidas:
        assert nueva.status == Task.Status.PENDING
        assert nueva.work_order is None
        assert nueva.scheduled_date == HOY - timedelta(days=2)


def test_cancelar_reemite_tambien_los_correctivos(hospital, admin):
    a = activo(hospital)
    ot = make_work_order(a, admin, status=WorkOrder.Status.CANCELLED)

    reemitidas = services.cancel_work_order_tasks(ot)

    # make_work_order ya la creo cancelada; no hay nada programado que reemitir.
    assert reemitidas == []

    ot2 = make_work_order(a, admin)
    reemitidas = services.cancel_work_order_tasks(ot2)
    assert len(reemitidas) == 1
    assert reemitidas[0].plan_task is None


# ── Agrupar en una OT ─────────────────────────────────────────────────────────

def test_una_ot_solo_puede_ser_de_un_hospital(hospital, otro_hospital, admin):
    """D4."""
    a, b = activo(hospital), activo(otro_hospital)
    plan = make_plan("Mixto", assets=[a, b])

    with pytest.raises(services.TaskStateError, match="mismo hospital"):
        services.create_work_order_for_tasks(
            [pending_task(plan, a), pending_task(plan, b)], admin
        )


def test_agrupar_varias_tareas_en_una_ot(hospital, admin):
    a, b, c = activo(hospital), activo(hospital), activo(hospital)
    plan = make_plan("Piso 3", assets=[a, b, c])
    Task.objects.filter(plan_task__plan=plan).update(estimated_duration=timedelta(minutes=30))
    tareas = [pending_task(plan, x) for x in (a, b, c)]

    ot, avisos = services.create_work_order_for_tasks(tareas, admin)

    assert avisos == []
    assert ot.hospital == hospital
    assert ot.tasks.count() == 3
    assert ot.estimated_duration == timedelta(minutes=90)
    assert list(ot.tasks.values_list("sort_order", flat=True)) == [0, 1, 2]
    assert "3 activos" in ot.title


def test_la_version_del_checklist_se_fija_al_programar(hospital, admin):
    a = activo(hospital)
    plantilla = baker.make(ChecklistTemplate, name="Alarma 3 gases")
    v1 = baker.make(ChecklistTemplateVersion, template=plantilla, version_number=1, is_current=True)
    plan = make_plan("Alarmas", assets=[a], checklist_template=plantilla)
    tarea = pending_task(plan, a)
    assert tarea.checklist_version is None, "la pendiente aun no tiene version"

    v1.is_current = False
    v1.save(update_fields=["is_current"])
    v2 = baker.make(ChecklistTemplateVersion, template=plantilla, version_number=2, is_current=True)
    services.create_work_order_for_tasks([tarea], admin)

    tarea.refresh_from_db()
    assert tarea.checklist_version == v2


def test_no_se_agrupa_una_tarea_que_no_esta_pendiente(hospital, admin):
    a = activo(hospital)
    plan = make_plan("Alarmas", assets=[a])
    tarea = pending_task(plan, a)
    services.create_work_order_for_tasks([tarea], admin)
    tarea.refresh_from_db()

    with pytest.raises(services.TaskStateError, match="no esta pendiente"):
        services.create_work_order_for_tasks([tarea], admin)


def test_ot_manual_crea_una_tarea_sin_plan(hospital, admin):
    a = activo(hospital)

    ot = services.create_manual_work_order(
        a, admin, task_type="CORRECTIVE", title="Fuga", scheduled_date=HOY,
    )

    tarea = ot.tasks.get()
    assert tarea.plan_task is None
    assert tarea.status == Task.Status.SCHEDULED
    assert ot.hospital == hospital


# ── Reprogramar y anular ─────────────────────────────────────────────────────

def test_reprogramar_exige_causa_y_deja_registro(hospital, admin):
    a = activo(hospital)
    plan = make_plan("Alarmas", assets=[a], next_due_date=HOY)
    tarea = pending_task(plan, a)
    causa = RescheduleCause.objects.get(name="NO DISPONIBLE")

    services.reschedule_task(tarea, HOY + timedelta(days=30), causa, admin, note="Cerrado por obra")

    tarea.refresh_from_db()
    assert tarea.scheduled_date == HOY + timedelta(days=30)
    assert tarea.calculated_date == HOY, "la calculada no cambia nunca"
    registro = TaskReschedule.objects.get(task=tarea)
    assert (registro.from_date, registro.to_date) == (HOY, HOY + timedelta(days=30))
    assert registro.note == "Cerrado por obra"


def test_las_causas_del_cliente_vienen_sembradas(db):
    nombres = set(RescheduleCause.objects.values_list("name", flat=True))
    assert {"3 VISITAS", "ADELANTADO", "APLAZADO", "NO DISPONIBLE", "SOLO 1 VISITA"} <= nombres
    assert len(nombres) >= 10


def test_no_se_reprograma_una_tarea_en_una_ot(hospital, admin):
    a = activo(hospital)
    ot = make_work_order(a, admin)
    causa = RescheduleCause.objects.get(name="APLAZADO")

    with pytest.raises(services.TaskStateError, match="Solo se reprograman"):
        services.reschedule_task(ot.primary_task, HOY, causa, admin)


def test_causa_inactiva_no_se_acepta(hospital, admin):
    a = activo(hospital)
    plan = make_plan("Alarmas", assets=[a])
    causa = RescheduleCause.objects.get(name="APLAZADO")
    causa.is_active = False
    causa.save()

    with pytest.raises(services.TaskStateError, match="desactivada"):
        services.reschedule_task(pending_task(plan, a), HOY, causa, admin)


def test_el_registro_de_reprogramacion_no_se_edita_ni_se_borra(hospital, admin):
    a = activo(hospital)
    plan = make_plan("Alarmas", assets=[a])
    causa = RescheduleCause.objects.get(name="APLAZADO")
    services.reschedule_task(pending_task(plan, a), HOY + timedelta(days=10), causa, admin)
    registro = TaskReschedule.objects.get()

    registro.note = "cambiado"
    with pytest.raises(ValueError):
        registro.save()
    with pytest.raises(ValueError):
        registro.delete()


def test_anular_exige_motivo_y_no_genera_la_siguiente(hospital):
    a = activo(hospital)
    plan = make_plan("Alarmas", assets=[a])
    tarea = pending_task(plan, a)

    with pytest.raises(services.TaskStateError):
        services.cancel_task(tarea, "  ")
    services.cancel_task(tarea, "El hospital retiro el equipo")

    tarea.refresh_from_db()
    assert tarea.status == Task.Status.CANCELLED
    assert pending_task(plan, a) is None


# ── Activador por evento ─────────────────────────────────────────────────────

def test_tarea_por_evento_no_se_genera_sola(hospital, admin):
    a = activo(hospital)
    plan = make_plan("Actas", assets=[a])
    evento = PlanTask.objects.create(
        plan=plan, name="ACTA DE ENTREGA", trigger=PlanTask.Trigger.EVENT,
    )
    services.sync_plan_task(evento)
    assert not Task.objects.filter(plan_task=evento).exists()

    tarea = services.create_event_task(evento, a, HOY, admin)

    assert tarea.status == Task.Status.PENDING
    with pytest.raises(services.TaskStateError, match="ya tiene"):
        services.create_event_task(evento, a, HOY, admin)


# ── Fase 2: siguiente fecha tras un aplazamiento ──────────────────────────────

@pytest.mark.parametrize("fija,esperada", [
    # Con programacion fija el ciclo no se corre: calculada anterior + 6 meses.
    (True, date(2026, 7, 10)),
    # Sin ella (el defecto, como el cliente): desde el dia en que se hizo.
    (False, date(2026, 8, 15)),
])
def test_siguiente_fecha_despues_de_aplazar(hospital, admin, fija, esperada):
    a = activo(hospital)
    plan = make_plan("Alarmas", assets=[a], next_due_date=date(2026, 1, 10), fixed_schedule=fija)
    tarea = pending_task(plan, a)
    services.reschedule_task(
        tarea, date(2026, 2, 15), RescheduleCause.objects.get(name="APLAZADO"), admin
    )
    ot, _ = services.create_work_order_for_tasks([tarea], admin)
    hecho = timezone.make_aware(timezone.datetime(2026, 2, 15, 10, 0))

    siguiente = cerrar(ot, hecho)[0]

    assert siguiente.calculated_date == esperada
    assert siguiente.scheduled_date == esperada
    tarea.refresh_from_db()
    assert tarea.calculated_date == date(2026, 1, 10), "la calculada no cambia nunca"


# ── Fase 2: cambios en la tarea del plan ──────────────────────────────────────

def _antes(pt):
    return {"is_active": pt.is_active, "trigger": pt.trigger, "start_date": pt.start_date}


def test_desactivar_la_tarea_del_plan_anula_sus_pendientes(hospital):
    a = activo(hospital)
    plan = make_plan("Alarmas", assets=[a])
    pt = plan.tasks.get()
    antes = _antes(pt)
    pt.is_active = False
    pt.save()

    services.plan_task_changed(pt, antes)

    tarea = Task.objects.get(plan_task=pt)
    assert tarea.status == Task.Status.CANCELLED
    assert "se desactivó" in tarea.cancellation_note


def test_reactivarla_vuelve_a_abrir_la_pendiente(hospital):
    a = activo(hospital)
    plan = make_plan("Alarmas", assets=[a])
    pt = plan.tasks.get()
    antes = _antes(pt)
    pt.is_active = False
    pt.save()
    services.plan_task_changed(pt, antes)

    antes = _antes(pt)
    pt.is_active = True
    pt.save()
    services.plan_task_changed(pt, antes)

    assert Task.objects.filter(plan_task=pt, status=Task.Status.PENDING).count() == 1


def test_pasar_a_evento_anula_las_pendientes(hospital):
    a = activo(hospital)
    plan = make_plan("Pruebas anuales", assets=[a])
    pt = plan.tasks.get()
    antes = _antes(pt)
    pt.trigger = PlanTask.Trigger.EVENT
    pt.save()

    services.plan_task_changed(pt, antes)

    assert not Task.objects.filter(plan_task=pt, status=Task.Status.PENDING).exists()


def test_cambiar_la_fecha_de_inicio_mueve_la_primera_ocurrencia(hospital, admin):
    a, b = activo(hospital), activo(hospital)
    plan = make_plan("Alarmas", assets=[a, b], next_due_date=HOY)
    pt = plan.tasks.get()
    # b ya se reprogramo: esa decision del planificador no se pisa.
    services.reschedule_task(
        pending_task(plan, b), HOY + timedelta(days=3),
        RescheduleCause.objects.get(name="APLAZADO"), admin,
    )
    antes = _antes(pt)
    pt.start_date = HOY + timedelta(days=30)
    pt.save()

    services.plan_task_changed(pt, antes)

    assert pending_task(plan, a).scheduled_date == HOY + timedelta(days=30)
    assert pending_task(plan, a).calculated_date == HOY + timedelta(days=30)
    assert pending_task(plan, b).scheduled_date == HOY + timedelta(days=3)


# ── Fase 2: acciones en lote ──────────────────────────────────────────────────

def test_reprogramar_varias_es_todo_o_nada(hospital, admin):
    a, b = activo(hospital), activo(hospital)
    plan = make_plan("Alarmas", assets=[a, b])
    ta, tb = pending_task(plan, a), pending_task(plan, b)
    services.create_work_order_for_tasks([tb], admin)
    tb.refresh_from_db()
    causa = RescheduleCause.objects.get(name="APLAZADO")

    with pytest.raises(services.TaskStateError, match=b.code):
        services.reschedule_tasks([ta, tb], HOY + timedelta(days=9), causa, admin)

    ta.refresh_from_db()
    assert ta.scheduled_date == HOY
    assert not TaskReschedule.objects.exists()


def test_reprogramar_varias_salta_las_que_ya_tienen_la_fecha(hospital, admin):
    a, b = activo(hospital), activo(hospital)
    plan = make_plan("Alarmas", assets=[a, b])
    destino = HOY + timedelta(days=9)
    causa = RescheduleCause.objects.get(name="APLAZADO")
    services.reschedule_task(pending_task(plan, a), destino, causa, admin)

    movidas = services.reschedule_tasks(
        [pending_task(plan, a), pending_task(plan, b)], destino, causa, admin
    )

    assert movidas == 1
    assert TaskReschedule.objects.count() == 2
