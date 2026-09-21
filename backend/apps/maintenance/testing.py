"""
Ayudas para las pruebas: construir OTs y planes con el modelo de tareas.

Antes cada archivo de pruebas creaba `WorkOrder(asset=..., checklist_version=...)`
y planes con `frequency_value` y `assets`. Esos campos pasaron a las tareas; en
lugar de repetir en cada archivo como se arma una OT con su tarea, todos pasan
por aqui y cada prueba conserva lo que comprobaba.
"""

from datetime import date

from apps.work_orders.models import WorkOrder

from . import services
from .models import MaintenancePlan, PlanTask, Task

_ESTADO_TAREA = {
    WorkOrder.Status.COMPLETED: Task.Status.DONE,
    WorkOrder.Status.CANCELLED: Task.Status.CANCELLED,
}


def make_work_order(
    asset,
    created_by,
    *,
    status=WorkOrder.Status.PENDING,
    assigned_to=None,
    checklist_version=None,
    plan=None,
    task_type=WorkOrder.TaskType.CORRECTIVE,
    title="OT test",
    priority=WorkOrder.Priority.MEDIUM,
    scheduled_date=None,
    **extra,
):
    """
    Una OT con una tarea sobre `asset`, como las que existian antes del modelo
    de tareas. Con `plan`, la tarea viene de la primera tarea del plan y, si el
    activo ya tenia su pendiente, es esa misma la que entra en la OT.
    """
    fecha = scheduled_date or date.today()
    if isinstance(fecha, str):
        fecha = date.fromisoformat(fecha)

    wo = WorkOrder(
        hospital=asset.hospital,
        task_type=task_type,
        title=title,
        status=status,
        priority=priority,
        scheduled_date=fecha,
        assigned_to=assigned_to,
        created_by=created_by,
        **extra,
    )
    wo.save()

    estado = _ESTADO_TAREA.get(status, Task.Status.SCHEDULED)
    plan_task = plan.tasks.order_by("sort_order", "name").first() if plan else None
    campos = {
        "work_order": wo,
        "status": estado,
        "title": title,
        "task_type": task_type,
        "priority": priority,
        "checklist_version": checklist_version,
        "scheduled_date": fecha,
        "completed_at": wo.completed_at if estado == Task.Status.DONE else None,
    }

    pendiente = None
    if plan_task is not None:
        pendiente = Task.objects.filter(
            plan_task=plan_task, asset=asset, status=Task.Status.PENDING
        ).first()
    if pendiente is not None:
        for campo, valor in campos.items():
            setattr(pendiente, campo, valor)
        pendiente.save()
    else:
        Task.objects.create(
            asset=asset,
            plan_task=plan_task,
            calculated_date=fecha,
            created_by=created_by,
            **campos,
        )
    return wo


def make_plan(
    name,
    *,
    assets=(),
    frequency_value=6,
    frequency_unit=MaintenancePlan.FrequencyUnit.MONTHS,
    checklist_template=None,
    task_type=MaintenancePlan.TaskType.PREVENTIVE,
    is_active=True,
    next_due_date=None,
    fixed_schedule=False,
    **plan_fields,
):
    """
    Un plan con una tarea y sus activos asignados. `next_due_date` es la fecha
    de la primera pendiente de cada activo (antes era un campo del plan); sin
    ella, hoy.
    """
    plan = MaintenancePlan.objects.create(name=name, is_active=is_active, **plan_fields)
    PlanTask.objects.create(
        plan=plan,
        name=name,
        task_type=task_type,
        checklist_template=checklist_template,
        trigger=PlanTask.Trigger.DATE,
        frequency_value=frequency_value,
        frequency_unit=frequency_unit,
        fixed_schedule=fixed_schedule,
        start_date=next_due_date,
    )
    for asset in assets:
        services.set_asset_plan(asset, plan)
    return plan


def pending_task(plan, asset):
    """La tarea pendiente del activo para la primera tarea del plan."""
    return Task.objects.filter(
        plan_task__plan=plan, asset=asset, status__in=Task.OPEN_STATUSES
    ).first()
