"""
Hallazgos (bloque E, decisiones del 2026-09-23).

El tecnico los registra mientras la OT esta abierta; uno que no resolvio en
sitio queda en la bandeja del planificador, que lo convierte en una tarea
correctiva pendiente (que luego agrupa en una OT como cualquier otra) o lo
descarta con motivo.
"""

from django.db import transaction
from django.utils import timezone

from apps.maintenance.models import MaintenancePlan, Task

from .models import Finding, WorkOrder

# Mientras la OT esta en estos estados el tecnico registra y corrige hallazgos.
# Enviada a revision, lo capturado es evidencia y no se toca.
EDITABLE = (WorkOrder.Status.PENDING, WorkOrder.Status.IN_PROGRESS)

# El planificador decide sobre un pendiente cuando la visita ya se entrego.
DECIDIBLE = (WorkOrder.Status.IN_REVIEW, WorkOrder.Status.COMPLETED)

_PRIORIDAD = {
    Finding.Severity.LOW: MaintenancePlan.Priority.LOW,
    Finding.Severity.MEDIUM: MaintenancePlan.Priority.MEDIUM,
    Finding.Severity.HIGH: MaintenancePlan.Priority.HIGH,
    Finding.Severity.CRITICAL: MaintenancePlan.Priority.HIGH,
}


class FindingStateError(Exception):
    pass


def _decidible(finding):
    if finding.status != Finding.Status.PENDING:
        raise FindingStateError(
            f"El hallazgo ya está {finding.get_status_display().lower()}."
        )
    if finding.work_order.status not in DECIDIBLE:
        raise FindingStateError(
            "Se decide sobre el hallazgo cuando la OT ya se envió a revisión."
        )


@transaction.atomic
def convert(finding, user, *, scheduled_date=None, note=""):
    """
    Crea la tarea correctiva pendiente del hallazgo. Sale en Tareas pendientes
    para agruparla en una OT; su prioridad sale de la severidad.
    """
    finding = Finding.objects.select_for_update().select_related("work_order").get(pk=finding.pk)
    _decidible(finding)
    fecha = scheduled_date or timezone.localdate()
    tarea = Task.objects.create(
        asset_id=finding.asset_id,
        plan_task=None,
        status=Task.Status.PENDING,
        title=f"Correctivo: {finding.description[:120]}",
        description=(
            f"Hallazgo de la {finding.work_order.wo_code} "
            f"({finding.get_severity_display().lower()}): {finding.description}"
        ),
        task_type=MaintenancePlan.TaskType.CORRECTIVE,
        priority=_PRIORIDAD[finding.severity],
        calculated_date=fecha,
        scheduled_date=fecha,
        created_by=user,
    )
    finding.status = Finding.Status.CONVERTED
    finding.corrective_task = tarea
    finding.decided_by = user
    finding.decided_at = timezone.now()
    finding.decision_note = note
    finding.save()
    return finding


@transaction.atomic
def dismiss(finding, user, note):
    if not (note or "").strip():
        raise FindingStateError("Escribe por qué se descarta el hallazgo.")
    finding = Finding.objects.select_for_update().select_related("work_order").get(pk=finding.pk)
    _decidible(finding)
    finding.status = Finding.Status.DISMISSED
    finding.decided_by = user
    finding.decided_at = timezone.now()
    finding.decision_note = note.strip()
    finding.save()
    return finding
