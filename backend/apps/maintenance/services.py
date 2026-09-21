"""
Ciclo de vida de las tareas (diseno aprobado el 2026-09-21).

Es el unico sitio que cambia `Task.status`. Las vistas, el motor diario y las
transiciones de la OT llaman a estas funciones en vez de escribir el estado a
mano, porque cada cambio arrastra otros: cerrar una tarea crea la siguiente,
cancelar una OT reemite sus tareas, cambiar el plan de un activo hereda la
fecha. Si alguien escribiera `status` directamente, el calendario del activo
quedaria roto sin que nada avisara.

Reglas, siguiendo lo que hace el cliente en su Fracttal:

- Por cada tarea del plan y cada activo hay como mucho una tarea abierta
  (pendiente o programada). La garantiza la base con un indice unico parcial.
- Sin programacion fija (el defecto, D3) la siguiente fecha calculada es la
  fecha de realizacion + frecuencia; con ella, la calculada anterior + frecuencia.
- Al cancelar una OT sus tareas quedan con ella y se reemiten como pendientes
  con la misma fecha (D6).
- Cambiar el plan de un activo anula sus pendientes del plan viejo y las del
  nuevo heredan la fecha (D7).
"""

from datetime import timedelta

from dateutil.relativedelta import relativedelta
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import MaintenancePlan, PlanTask, RescheduleCause, Task, TaskReschedule

ADELANTADO = "ADELANTADO"

_PESO_PRIORIDAD = {
    MaintenancePlan.Priority.HIGH: 0,
    MaintenancePlan.Priority.MEDIUM: 1,
    MaintenancePlan.Priority.LOW: 2,
}


class TaskStateError(ValueError):
    """La operacion no es valida para el estado actual de la tarea o la OT."""


# ── Fechas ────────────────────────────────────────────────────────────────────

def add_frequency(start, value, unit):
    """Suma `value` unidades de frecuencia a una fecha."""
    unidad = MaintenancePlan.FrequencyUnit
    if unit == unidad.DAYS:
        return start + timedelta(days=value)
    if unit == unidad.WEEKS:
        return start + timedelta(weeks=value)
    if unit == unidad.MONTHS:
        return start + relativedelta(months=value)
    if unit == unidad.YEARS:
        return start + relativedelta(years=value)
    raise ValueError(f"Unidad de frecuencia desconocida: {unit!r}")


def next_calculated_date(plan_task, closed_task):
    """
    Fecha calculada de la ocurrencia que sigue a `closed_task`.

    Sin programacion fija cuenta desde el dia en que se hizo, que es como
    trabaja el cliente: en el historial real de una alarma, la fecha calculada
    de cada ciclo es la de realizacion anterior + 6 meses, al microsegundo.
    """
    if plan_task.fixed_schedule or closed_task.completed_at is None:
        base = closed_task.calculated_date
    else:
        base = timezone.localdate(closed_task.completed_at)
    return add_frequency(base, plan_task.frequency_value, plan_task.frequency_unit)


# ── Generacion de pendientes ──────────────────────────────────────────────────

def _executions_done(plan_task, asset):
    return Task.objects.filter(
        plan_task=plan_task, asset=asset, status=Task.Status.DONE
    ).count()


def can_generate(plan_task, asset):
    """True si la tarea del plan debe tener una ocurrencia abierta en el activo."""
    from apps.assets.models import Asset

    if not (plan_task.is_active and plan_task.plan.is_active):
        return False
    if plan_task.trigger != PlanTask.Trigger.DATE:
        return False
    if asset.status != Asset.Status.ACTIVE or asset.plan_id != plan_task.plan_id:
        return False
    if plan_task.repeat_count is not None:
        return _executions_done(plan_task, asset) < plan_task.repeat_count
    return True


def _new_pending(plan_task, asset, fecha, created_by=None):
    return Task.objects.create(
        asset=asset,
        plan_task=plan_task,
        status=Task.Status.PENDING,
        title=plan_task.name,
        description=plan_task.description,
        task_type=plan_task.task_type,
        priority=plan_task.priority,
        calculated_date=fecha,
        scheduled_date=fecha,
        estimated_duration=plan_task.estimated_duration,
        created_by=created_by,
    )


def _open_task(plan_task, asset):
    return Task.objects.filter(
        plan_task=plan_task, asset=asset, status__in=Task.OPEN_STATUSES
    ).first()


def ensure_open_task(plan_task, asset, fecha=None, created_by=None):
    """
    Garantiza que el par tarea del plan x activo tenga su tarea abierta.

    Devuelve (tarea, creada). Si no debe generarse (plan inactivo, activo dado de
    baja, activador por evento, repeticiones agotadas) devuelve (None, False).
    Sin `fecha`, la primera ocurrencia cae en `start_date` o hoy, y las
    siguientes salen del ultimo cierre.
    """
    abierta = _open_task(plan_task, asset)
    if abierta is not None:
        return abierta, False
    if not can_generate(plan_task, asset):
        return None, False

    if fecha is None:
        ultima = (
            Task.objects.filter(plan_task=plan_task, asset=asset, status=Task.Status.DONE)
            .order_by("-completed_at")
            .first()
        )
        if ultima is not None:
            fecha = next_calculated_date(plan_task, ultima)
        else:
            fecha = plan_task.start_date or timezone.localdate()

    try:
        with transaction.atomic():
            return _new_pending(plan_task, asset, fecha, created_by), True
    except IntegrityError:
        # Otro proceso la abrio entre la consulta y el INSERT: el indice unico
        # parcial lo impidio. La suya es tan buena como la nuestra.
        return _open_task(plan_task, asset), False


def sync_plan_task(plan_task, created_by=None):
    """Tras crear o reactivar una tarea del plan, abre la pendiente de cada activo."""
    creadas = 0
    for asset in plan_task.plan.assets.all():
        _, creada = ensure_open_task(plan_task, asset, created_by=created_by)
        creadas += int(creada)
    return creadas


def _cancel_pending_of(plan_task, note):
    for tarea in Task.objects.filter(plan_task=plan_task, status=Task.Status.PENDING):
        _cancel(tarea, note)


def _move_first_occurrences(plan_task, old_start):
    """
    Si se cambia la fecha de inicio de una tarea del plan, sus primeras
    ocurrencias (las que nacieron con esa fecha y nunca se reprogramaron ni se
    hicieron) se mueven con ella. Sin esto, corregir la fecha de inicio justo
    despues de crear la tarea no tendria efecto: las pendientes ya existian.
    """
    nueva = plan_task.start_date or timezone.localdate()
    candidatas = Task.objects.filter(
        plan_task=plan_task, status=Task.Status.PENDING,
        calculated_date=old_start, scheduled_date=old_start,
        reschedules__isnull=True,
    )
    for tarea in candidatas:
        ya_hecha = Task.objects.filter(
            plan_task=plan_task, asset_id=tarea.asset_id, status=Task.Status.DONE
        ).exists()
        if not ya_hecha:
            tarea.calculated_date = nueva
            tarea.scheduled_date = nueva
            tarea.save(update_fields=["calculated_date", "scheduled_date", "updated_at"])


@transaction.atomic
def plan_task_changed(plan_task, before, created_by=None):
    """
    Aplica a las tareas abiertas un cambio en la definicion de la tarea del plan.

    `before` trae is_active, trigger y start_date como estaban antes de guardar.
    Desactivar la tarea, o pasarla a activarse por evento, anula sus pendientes:
    "esta ya no toca". Reactivarla vuelve a abrir la de cada activo, contada
    desde su ultima realizacion. Cambiar la frecuencia no mueve las pendientes:
    la nueva se aplica al calcular la siguiente, como en Fracttal.
    """
    por_fecha = PlanTask.Trigger.DATE
    antes = before["is_active"] and before["trigger"] == por_fecha
    ahora = plan_task.is_active and plan_task.trigger == por_fecha

    if before["is_active"] and not plan_task.is_active:
        _cancel_pending_of(plan_task, f"La tarea «{plan_task.name}» del plan se desactivó.")
        return
    if antes and not ahora:
        _cancel_pending_of(
            plan_task, f"La tarea «{plan_task.name}» del plan pasó a activarse por evento."
        )
        return
    if ahora:
        if before["start_date"] and before["start_date"] != plan_task.start_date:
            _move_first_occurrences(plan_task, before["start_date"])
        if plan_task.plan.is_active:
            sync_plan_task(plan_task, created_by)


def create_event_task(plan_task, asset, fecha, created_by):
    """
    Ocurrencia de una tarea con activador por evento (acta de entrega, prueba
    anual por cliente). Nunca se generan solas: las crea el planificador.
    """
    if plan_task.trigger != PlanTask.Trigger.EVENT:
        raise TaskStateError("Solo las tareas con activador por evento se crean a mano.")
    if asset.plan_id != plan_task.plan_id:
        raise TaskStateError("El activo no tiene asignado el plan de esta tarea.")
    if _open_task(plan_task, asset) is not None:
        raise TaskStateError("Ese activo ya tiene esta tarea abierta.")
    return _new_pending(plan_task, asset, fecha, created_by)


# ── Plan del activo (D7) ──────────────────────────────────────────────────────

def _cancel(task, note):
    task.status = Task.Status.CANCELLED
    task.cancellation_note = note
    task.save(update_fields=["status", "cancellation_note", "updated_at"])


@transaction.atomic
def set_asset_plan(asset, new_plan, created_by=None):
    """
    Asigna, cambia o quita el plan de un activo.

    Al cambiar de plan (de "3 TOMAS" a "4 TOMAS"), las pendientes del plan viejo
    se anulan y las del nuevo heredan la fecha de la mas proxima: el ciclo del
    activo no vuelve a empezar. Devuelve esa fecha heredada, o None si no habia
    pendiente de la que heredar. Las tareas que ya estan dentro de una OT no se
    tocan; al cerrarse no generan la siguiente porque el activo ya no tiene ese
    plan.
    """
    nuevo_id = new_plan.id if new_plan else None
    heredada = None

    if asset.plan_id and asset.plan_id != nuevo_id:
        pendientes = list(
            Task.objects.filter(
                asset=asset,
                plan_task__plan_id=asset.plan_id,
                status=Task.Status.PENDING,
            )
        )
        if pendientes:
            heredada = min(t.scheduled_date for t in pendientes)
        destino = f"«{new_plan.name}»" if new_plan else "ninguno"
        for tarea in pendientes:
            _cancel(tarea, f"El activo cambió de plan de tareas (ahora: {destino}).")

    if asset.plan_id != nuevo_id:
        asset.plan = new_plan
        asset.save(update_fields=["plan", "updated_at"])

    if new_plan is not None:
        for plan_task in new_plan.tasks.filter(is_active=True, trigger=PlanTask.Trigger.DATE):
            ensure_open_task(plan_task, asset, fecha=heredada, created_by=created_by)
    return heredada


def assign_plan_to_assets(plan, assets, created_by=None):
    """
    Deja exactamente `assets` con este plan: asigna los nuevos y quita los que
    ya no estan. Un activo que tenia otro plan se cambia a este (D7).
    """
    objetivo = {a.id for a in assets}
    for asset in plan.assets.exclude(id__in=objetivo):
        set_asset_plan(asset, None, created_by)
    for asset in assets:
        if asset.plan_id != plan.id:
            set_asset_plan(asset, plan, created_by)


# ── Tareas y OTs ──────────────────────────────────────────────────────────────

def _current_version(plan_task):
    if plan_task is None or not plan_task.checklist_template_id:
        return None
    from apps.checklists.models import ChecklistTemplateVersion

    return ChecklistTemplateVersion.objects.filter(
        template_id=plan_task.checklist_template_id, is_current=True
    ).first()


def schedule_tasks(tasks, work_order):
    """
    Mete tareas pendientes en una OT y fija la version vigente de su checklist.

    Devuelve avisos: una tarea cuyo checklist no tiene version publicada entra
    igual, sin checklist, porque no generarla cancelaria el preventivo en
    silencio; lo que no puede pasar es que nadie se entere.
    """
    avisos = []
    for orden, tarea in enumerate(tasks):
        if tarea.status != Task.Status.PENDING:
            raise TaskStateError(
                f"La tarea «{tarea.title}» no esta pendiente ({tarea.get_status_display()})."
            )
        if tarea.asset.hospital_id != work_order.hospital_id:
            raise TaskStateError(
                "Todas las tareas de una OT deben ser de activos del mismo hospital."
            )
        if tarea.plan_task_id:
            version = _current_version(tarea.plan_task)
            if version is None and tarea.plan_task.checklist_template_id:
                avisos.append(
                    f"La plantilla '{tarea.plan_task.checklist_template.name}' no tiene "
                    f"version publicada: la tarea «{tarea.title}» entra sin checklist."
                )
            tarea.checklist_version = version
        tarea.work_order = work_order
        tarea.status = Task.Status.SCHEDULED
        tarea.sort_order = orden
        tarea.save(update_fields=[
            "work_order", "status", "checklist_version", "sort_order", "updated_at",
        ])
    return avisos


def _default_title(tasks):
    if len(tasks) == 1:
        tarea = tasks[0]
        prefijo = "[PM] " if tarea.plan_task_id else ""
        return f"{prefijo}{tarea.title} — {tarea.asset.name}"[:500]
    tipo = MaintenancePlan.TaskType(tasks[0].task_type).label
    return f"{tipo} — {len(tasks)} activos"[:500]


@transaction.atomic
def create_work_order_for_tasks(
    tasks, created_by, *, title=None, assigned_to=None, scheduled_date=None,
    priority=None, task_type=None, location=None, description="", notes="",
):
    """
    Agrupa tareas pendientes en una OT nueva (Fracttal: "+ Nueva OT").

    Devuelve (ot, avisos). Todas deben ser del mismo hospital (D4).
    """
    from apps.work_orders.models import WorkOrder

    tasks = list(tasks)
    if not tasks:
        raise TaskStateError("Una OT necesita al menos una tarea.")
    hospitales = {t.asset.hospital_id for t in tasks}
    if len(hospitales) > 1:
        raise TaskStateError(
            "Todas las tareas de una OT deben ser de activos del mismo hospital."
        )

    duraciones = [t.estimated_duration for t in tasks if t.estimated_duration]
    ot = WorkOrder(
        hospital_id=hospitales.pop(),
        location=location,
        task_type=task_type or tasks[0].task_type,
        title=title or _default_title(tasks),
        description=description,
        priority=priority or min(
            (t.priority for t in tasks), key=lambda p: _PESO_PRIORIDAD.get(p, 9)
        ),
        status=WorkOrder.Status.PENDING,
        scheduled_date=scheduled_date or min(t.scheduled_date for t in tasks),
        estimated_duration=sum(duraciones, timedelta()) if duraciones else None,
        created_by=created_by,
        assigned_to=assigned_to,
        notes=notes,
    )
    ot.save()
    avisos = schedule_tasks(tasks, ot)
    return ot, avisos


@transaction.atomic
def create_manual_work_order(asset, created_by, checklist_version=None, **campos):
    """
    OT a mano sobre un activo, como el alta de OT de hoy (correctivos).

    Crea la OT y una tarea sin plan de origen, ya programada. En la fase 4 el
    alta acepta varios activos.
    """
    from apps.work_orders.models import WorkOrder

    ot = WorkOrder(hospital=asset.hospital, created_by=created_by, **campos)
    ot.save()
    Task.objects.create(
        asset=asset,
        plan_task=None,
        work_order=ot,
        status=Task.Status.SCHEDULED,
        title=ot.title,
        description=ot.description,
        task_type=ot.task_type,
        priority=ot.priority,
        checklist_version=checklist_version,
        calculated_date=ot.scheduled_date,
        scheduled_date=ot.scheduled_date,
        estimated_duration=ot.estimated_duration,
        created_by=created_by,
    )
    return ot


def complete_work_order_tasks(work_order):
    """La OT se completo: sus tareas se cierran y cada una genera la siguiente."""
    ahora = work_order.completed_at or timezone.now()
    siguientes = []
    for tarea in work_order.tasks.filter(status=Task.Status.SCHEDULED).select_related(
        "plan_task__plan", "asset"
    ):
        tarea.status = Task.Status.DONE
        tarea.completed_at = ahora
        tarea.save(update_fields=["status", "completed_at", "updated_at"])
        if tarea.plan_task_id and can_generate(tarea.plan_task, tarea.asset):
            fecha = next_calculated_date(tarea.plan_task, tarea)
            siguientes.append(_new_pending(tarea.plan_task, tarea.asset, fecha))
    return siguientes


def cancel_work_order_tasks(work_order):
    """
    La OT se cancelo (D6): sus tareas quedan con ella como registro y se
    reemiten como pendientes con la misma fecha, listas para reagruparse. Es lo
    que hizo el cliente con la 19453: cancelada y 49 segundos despues las mismas
    tres tareas estaban en la 19454.
    """
    reemitidas = []
    for tarea in work_order.tasks.filter(status=Task.Status.SCHEDULED).select_related(
        "plan_task__plan", "asset"
    ):
        _cancel(tarea, f"OT {work_order.wo_code} cancelada.")
        if tarea.plan_task_id and not can_generate(tarea.plan_task, tarea.asset):
            continue
        reemitidas.append(
            Task.objects.create(
                asset=tarea.asset,
                plan_task=tarea.plan_task,
                status=Task.Status.PENDING,
                title=tarea.title,
                description=tarea.description,
                task_type=tarea.task_type,
                priority=tarea.priority,
                calculated_date=tarea.calculated_date,
                scheduled_date=tarea.scheduled_date,
                estimated_duration=tarea.estimated_duration,
            )
        )
    return reemitidas


# ── Acciones del planificador ─────────────────────────────────────────────────

def get_cause(name):
    """Causa del catalogo por nombre. La siembra la migracion; esto la repone."""
    cause, _ = RescheduleCause.objects.get_or_create(name=name)
    return cause


@transaction.atomic
def reschedule_task(task, new_date, cause, changed_by, note=""):
    """
    Mueve la fecha programada de una pendiente. Exige causa del catalogo y deja
    registro; la fecha calculada no se toca.
    """
    if task.status != Task.Status.PENDING:
        raise TaskStateError(
            "Solo se reprograman tareas pendientes. Para mover una tarea que ya "
            "esta en una OT, cambia la fecha de la OT."
        )
    if not cause.is_active:
        raise TaskStateError(f"La causa «{cause.name}» esta desactivada.")
    if new_date == task.scheduled_date:
        raise TaskStateError("La tarea ya esta programada para esa fecha.")
    TaskReschedule.objects.create(
        task=task,
        from_date=task.scheduled_date,
        to_date=new_date,
        cause=cause,
        note=note,
        changed_by=changed_by,
    )
    task.scheduled_date = new_date
    task.save(update_fields=["scheduled_date", "updated_at"])
    return task


def cancel_task(task, note):
    """Anula una pendiente: "esta ya no toca". No se crea la siguiente."""
    if task.status != Task.Status.PENDING:
        raise TaskStateError("Solo se anulan tareas pendientes.")
    if not note.strip():
        raise TaskStateError("Indica por que se anula la tarea.")
    _cancel(task, note.strip())
    return task


def _all_pending(tasks, verbo):
    no_pendientes = [t for t in tasks if t.status != Task.Status.PENDING]
    if no_pendientes:
        nombres = ", ".join(f"{t.asset.code} ({t.get_status_display()})" for t in no_pendientes[:5])
        raise TaskStateError(f"Solo se {verbo} tareas pendientes. No lo estan: {nombres}.")


@transaction.atomic
def reschedule_tasks(tasks, new_date, cause, changed_by, note=""):
    """
    Reprograma varias pendientes a la misma fecha, todas o ninguna. Las que ya
    tenian esa fecha se dejan como estan y sin registro. Devuelve cuantas se
    movieron.
    """
    tasks = list(tasks)
    _all_pending(tasks, "reprograman")
    movidas = 0
    for tarea in tasks:
        if tarea.scheduled_date != new_date:
            reschedule_task(tarea, new_date, cause, changed_by, note)
            movidas += 1
    return movidas


@transaction.atomic
def cancel_tasks(tasks, note):
    """Anula varias pendientes con la misma nota, todas o ninguna."""
    tasks = list(tasks)
    _all_pending(tasks, "anulan")
    for tarea in tasks:
        cancel_task(tarea, note)
    return len(tasks)
