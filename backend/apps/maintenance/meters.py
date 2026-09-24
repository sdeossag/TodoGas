"""
Activadores por medidor de las tareas del plan (decision del 2026-09-24).

- "Cada" (EVERY): cada N unidades de un contador. El activo lleva en
  MeterSchedule el uso en que vence; cuando una lectura lo alcanza se abre la
  tarea con fecha de hoy. Al cerrarla, el siguiente vencimiento sale del uso
  al cerrar + N (o del vencimiento anterior + N, con programacion fija).
- "Cuando" (WHEN): una lectura cumple la condicion (presion < 50 PSI). Abre la
  tarea con fecha de hoy y avisa por correo a los administradores.

Como con las fechas, hay como mucho una tarea abierta por tarea del plan y
activo: si ya hay una, una lectura nueva no abre otra. Solo cuenta la ultima
lectura del medidor: corregir una lectura vieja no dispara nada.
"""

import operator

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import MeterSchedule, PlanTask

_COMPARA = {
    "EQ": operator.eq, "NE": operator.ne,
    "GT": operator.gt, "GTE": operator.ge,
    "LT": operator.lt, "LTE": operator.le,
}

METER_TRIGGERS = (PlanTask.Trigger.EVERY, PlanTask.Trigger.WHEN)


def condition_met(plan_task, value):
    return _COMPARA[plan_task.meter_comparator](value, plan_task.meter_threshold)


def _puede_abrir(plan_task, asset):
    from apps.assets.models import Asset

    from .services import _executions_done, _open_task

    if not (plan_task.is_active and plan_task.plan.is_active):
        return False
    if asset.status != Asset.Status.ACTIVE or asset.plan_id != plan_task.plan_id:
        return False
    if _open_task(plan_task, asset) is not None:
        return False
    if plan_task.repeat_count is not None:
        return _executions_done(plan_task, asset) < plan_task.repeat_count
    return True


def _abrir(plan_task, asset, reading, meter_due=None):
    from .services import _new_pending

    try:
        with transaction.atomic():
            tarea = _new_pending(plan_task, asset, timezone.localdate())
            tarea.trigger_reading = reading
            tarea.meter_due = meter_due
            tarea.save(update_fields=["trigger_reading", "meter_due", "updated_at"])
            return tarea
    except IntegrityError:
        # Otra lectura la abrio al mismo tiempo (indice unico parcial).
        return None


def _uso_actual(asset, unit):
    from apps.assets.meters import latest
    from apps.assets.models import Meter

    meter = Meter.objects.filter(asset=asset, unit=unit).first()
    ultima = latest(meter) if meter else None
    return ultima.accumulated if ultima is not None else None


def init_schedule(plan_task, asset, reset=False):
    """
    El primer vencimiento de una tarea "cada N" en un activo: el uso de hoy +
    N. No toca uno que ya exista, salvo `reset` (la tarea acaba de pasar a
    este activador). Sin lecturas no hay desde donde contar: el ciclo empieza
    con la primera (un horometro viejo que llega con 12.000 H no vence al
    instante).
    """
    if plan_task.trigger != PlanTask.Trigger.EVERY:
        return None
    base = _uso_actual(asset, plan_task.meter_unit)
    if base is None:
        MeterSchedule.objects.filter(plan_task=plan_task, asset=asset).delete()
        return None
    if reset:
        sched, _ = MeterSchedule.objects.update_or_create(
            plan_task=plan_task, asset=asset, defaults={"next_due": base + plan_task.meter_interval},
        )
        return sched
    sched, _ = MeterSchedule.objects.get_or_create(
        plan_task=plan_task, asset=asset, defaults={"next_due": base + plan_task.meter_interval},
    )
    return sched


def init_schedules_for_plan_task(plan_task, reset=False):
    for asset in plan_task.plan.assets.all():
        init_schedule(plan_task, asset, reset=reset)


def evaluate_reading(reading_id):
    """
    Evalua una lectura contra las tareas del plan del equipo con activador por
    medidor de esa unidad. Devuelve las tareas abiertas.
    """
    from apps.assets.meters import latest
    from apps.assets.models import MeterReading

    reading = MeterReading.objects.select_related("meter__asset", "meter__unit").filter(pk=reading_id).first()
    if reading is None:
        return []
    meter = reading.meter
    ultima = latest(meter)
    if ultima is None or ultima.pk != reading.pk:
        return []
    asset = meter.asset
    if not asset.plan_id:
        return []

    abiertas = []
    tareas = PlanTask.objects.filter(
        plan_id=asset.plan_id, meter_unit=meter.unit, trigger__in=METER_TRIGGERS,
    ).select_related("plan")
    for pt in tareas:
        if not _puede_abrir(pt, asset):
            continue
        if pt.trigger == PlanTask.Trigger.WHEN:
            if condition_met(pt, reading.value):
                tarea = _abrir(pt, asset, reading)
                if tarea is not None:
                    abiertas.append(tarea)
                    _avisar(tarea)
        elif reading.accumulated is not None:
            sched = init_schedule(pt, asset)
            if sched is not None and reading.accumulated >= sched.next_due:
                tarea = _abrir(pt, asset, reading, meter_due=sched.next_due)
                if tarea is not None:
                    abiertas.append(tarea)
    return abiertas


def _avisar(tarea):
    from .tasks import send_meter_alert

    transaction.on_commit(lambda: send_meter_alert.delay(str(tarea.pk)))


def task_completed(tarea):
    """
    Cerro una tarea "cada N": fija el siguiente vencimiento. Con programacion
    fija, el vencimiento anterior + N; sin ella (el defecto), el uso al
    cerrarla + N.
    """
    pt = tarea.plan_task
    if pt is None or pt.trigger != PlanTask.Trigger.EVERY:
        return None
    from apps.assets.meters import accumulated_at
    from apps.assets.models import Meter

    base = None
    if pt.fixed_schedule and tarea.meter_due is not None:
        base = tarea.meter_due
    else:
        meter = Meter.objects.filter(asset=tarea.asset, unit=pt.meter_unit).first()
        if meter is not None:
            base = accumulated_at(meter, tarea.completed_at or timezone.now())
    if base is None:
        if tarea.meter_due is None:
            return None
        base = tarea.meter_due
    sched, _ = MeterSchedule.objects.update_or_create(
        plan_task=pt, asset=tarea.asset, defaults={"next_due": base + pt.meter_interval},
    )
    return sched
