"""
Proceso diario de mantenimiento, sobre el modelo de tareas.

Hace dos cosas:

1. Red de seguridad: cada tarea de plan x activo tiene su tarea pendiente. En
   condiciones normales ya existe (se crea al asignar el plan y al cerrar la
   anterior); esto repone la que falte.

2. Si la configuracion lo pide, convierte en OT las pendientes que vencen. Es el
   equivalente de "Permitir que la generacion automatica de OTs se active por la
   fecha de programacion" de Fracttal, que el cliente tiene apagado (decision
   D1): alli las OTs las arma el planificador desde las tareas pendientes.
   Aqui queda encendido durante la fase 1 solo para que la aplicacion siga
   funcionando como antes hasta que exista la pantalla de pendientes.
"""

import logging
import uuid

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from . import services
from .models import MaintenancePlan, MaintenancePlanExecution, PlanTask, Task

logger = logging.getLogger(__name__)


def auto_create_enabled():
    return getattr(settings, "MAINTENANCE_AUTO_CREATE_WORK_ORDERS", False)


def ensure_open_tasks():
    """Abre la pendiente de cada tarea de plan x activo que no la tenga."""
    creadas = 0
    tareas = PlanTask.objects.filter(
        is_active=True, plan__is_active=True, trigger=PlanTask.Trigger.DATE
    ).select_related("plan")
    for plan_task in tareas:
        creadas += services.sync_plan_task(plan_task)
    return creadas


def _creator(triggered_by):
    if triggered_by is not None:
        return triggered_by
    from apps.users.models import User

    return User.objects.filter(role=User.Role.ADMIN).first()


def get_plans_due_today():
    """Planes activos con alguna tarea pendiente vencida o que vence hoy."""
    hoy = timezone.localdate()
    return (
        MaintenancePlan.objects.filter(
            is_active=True,
            tasks__is_active=True,
            tasks__occurrences__status=Task.Status.PENDING,
            tasks__occurrences__scheduled_date__lte=hoy,
        )
        .distinct()
    )


def generate_work_orders_for_plan(plan, triggered_by=None, manual=False):
    """
    Crea una OT por cada tarea pendiente del plan que toca.

    Corrida programada: las pendientes con fecha programada de hoy o antes.

    Disparo manual ("Disparar ahora"): todas las pendientes del plan. Las que
    vencian mas adelante se reprograman a hoy con causa ADELANTADO, que es
    exactamente lo que el cliente registra en Fracttal cuando adelanta una
    visita; queda en el historial de la tarea. Antes esto era un caso especial
    que no tocaba el calendario; ahora la fecha calculada no cambia nunca y la
    siguiente se cuenta segun la programacion de la tarea.

    Devuelve {'created', 'skipped', 'warnings', 'execution_id'}.
    """
    hoy = timezone.localdate()
    creador = _creator(triggered_by)
    if creador is None:
        return {
            "created": 0,
            "skipped": 0,
            "warnings": ["No se encontró usuario administrador para crear OTs."],
            "execution_id": None,
        }

    creadas = 0
    omitidas = 0
    avisos = []

    with transaction.atomic():
        for plan_task in plan.tasks.filter(is_active=True, trigger=PlanTask.Trigger.DATE):
            services.sync_plan_task(plan_task)

        abiertas = (
            Task.objects.filter(plan_task__plan=plan, status__in=Task.OPEN_STATUSES)
            .select_related("asset__hospital", "plan_task__checklist_template")
            .order_by("scheduled_date")
        )
        adelanto = services.get_cause(services.ADELANTADO) if manual else None

        for tarea in abiertas:
            if tarea.status == Task.Status.SCHEDULED:
                omitidas += 1
                avisos.append(
                    f"Activo '{tarea.asset.code}': ya tiene una OT activa para este protocolo."
                )
                continue
            if tarea.scheduled_date > hoy:
                if not manual:
                    continue
                services.reschedule_task(
                    tarea, hoy, adelanto, triggered_by,
                    note="Disparo manual desde el protocolo.",
                )
                avisos.append(
                    f"Activo '{tarea.asset.code}': la tarea se adelantó al {hoy} "
                    "(causa ADELANTADO)."
                )
            _ot, avisos_ot = services.create_work_order_for_tasks([tarea], creador)
            avisos.extend(a for a in avisos_ot if a not in avisos)
            creadas += 1

        ejecucion = MaintenancePlanExecution.objects.create(
            plan=plan,
            executed_by=triggered_by,
            work_orders_created=creadas,
            notes=f"Creadas: {creadas}, omitidas: {omitidas}.",
        )

    return {
        "created": creadas,
        "skipped": omitidas,
        "warnings": avisos,
        "execution_id": str(ejecucion.id),
    }


def run_daily_generation():
    """
    Corrida diaria (Celery beat). Repone pendientes y, si esta encendida la
    creacion automatica, convierte en OT las que vencen.

    Returns {'plans_processed', 'total_created', 'total_skipped', 'errors',
    'tasks_opened'}.
    """
    from apps.audit.models import AuditLog

    summary = {
        "plans_processed": 0,
        "total_created": 0,
        "total_skipped": 0,
        "errors": [],
        "tasks_opened": ensure_open_tasks(),
    }
    if not auto_create_enabled():
        return summary

    for plan in list(get_plans_due_today()):
        try:
            result = generate_work_orders_for_plan(plan)
            summary["plans_processed"] += 1
            summary["total_created"] += result["created"]
            summary["total_skipped"] += result["skipped"]

            if result["execution_id"]:
                AuditLog.objects.create(
                    user=None,
                    action=AuditLog.Action.CREATE,
                    entity_type="MaintenancePlanExecution",
                    entity_id=uuid.UUID(result["execution_id"]),
                    changes={
                        "plan": str(plan.id),
                        "created": result["created"],
                        "skipped": result["skipped"],
                        "warnings": result["warnings"],
                    },
                )
            logger.info(
                "[engine] Plan '%s': %d OTs creadas, %d omitidas.",
                plan.name, result["created"], result["skipped"],
            )
        except Exception as exc:
            summary["errors"].append({"plan": str(plan.id), "error": str(exc)})
            logger.error("[engine] Error en plan '%s': %s", plan.name, exc, exc_info=True)

    return summary
