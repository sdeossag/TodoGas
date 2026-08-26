from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import WorkOrder, WorkOrderStatusHistory

# Each key is (from_status, to_status).
# "roles" lists which role strings can perform the transition.
# "require_assignee" means the TEC must be the assigned_to of the OT.
ALLOWED_TRANSITIONS = {
    (WorkOrder.Status.PENDING, WorkOrder.Status.IN_PROGRESS): {
        "roles": ["TEC"],
        "require_assignee": True,
    },
    (WorkOrder.Status.IN_PROGRESS, WorkOrder.Status.IN_REVIEW): {
        "roles": ["TEC"],
        "require_assignee": True,
    },
    (WorkOrder.Status.IN_REVIEW, WorkOrder.Status.COMPLETED): {
        "roles": ["ADMIN", "SUP"],
        "require_assignee": False,
    },
    (WorkOrder.Status.IN_REVIEW, WorkOrder.Status.IN_PROGRESS): {
        "roles": ["ADMIN", "SUP"],
        "require_assignee": False,
    },
}

_CANCELLABLE_STATUSES = {
    WorkOrder.Status.PENDING,
    WorkOrder.Status.IN_PROGRESS,
    WorkOrder.Status.IN_REVIEW,
}


def validate_transition(work_order, new_status, user, comment=""):
    from_status = work_order.status

    if new_status == WorkOrder.Status.CANCELLED:
        if from_status not in _CANCELLABLE_STATUSES:
            raise ValidationError(
                f"No se puede cancelar una OT en estado '{from_status}'."
            )
        if user.role != "ADMIN":
            raise ValidationError("Solo un ADMIN puede cancelar una OT.")
        if not comment:
            raise ValidationError("Se requiere un comentario para cancelar una OT.")
        return True

    key = (from_status, new_status)
    if key not in ALLOWED_TRANSITIONS:
        raise ValidationError(
            f"La transición '{from_status}' → '{new_status}' no está permitida."
        )

    rule = ALLOWED_TRANSITIONS[key]

    if user.role not in rule["roles"]:
        raise ValidationError(
            f"Tu rol '{user.role}' no puede realizar la transición "
            f"'{from_status}' → '{new_status}'."
        )

    if user.role == "TEC" and rule.get("require_assignee"):
        if work_order.assigned_to_id != user.id:
            raise ValidationError("Solo el técnico asignado puede realizar esta transición.")

    if from_status == WorkOrder.Status.IN_PROGRESS and new_status == WorkOrder.Status.IN_REVIEW:
        if work_order.checklist_version_id:
            from django.core.exceptions import ObjectDoesNotExist
            try:
                cr = work_order.checklist_response
                if not cr.completed_at:
                    raise ValidationError("El checklist debe estar completado antes de enviar a revisión.")
            except ObjectDoesNotExist:
                raise ValidationError("Debes completar el checklist antes de enviar a revisión.")

        if not work_order.signatures.exists():
            raise ValidationError(
                "No se puede enviar a revision sin al menos una firma digital registrada."
            )

    return True


def apply_transition(work_order, new_status, user, comment=""):
    validate_transition(work_order, new_status, user, comment)

    from_status = work_order.status
    now = timezone.now()

    work_order.status = new_status

    if new_status == WorkOrder.Status.IN_PROGRESS and not work_order.started_at:
        work_order.started_at = now

    if new_status == WorkOrder.Status.COMPLETED:
        work_order.completed_at = now
        if work_order.started_at:
            work_order.actual_duration = now - work_order.started_at

    work_order.save()

    if new_status == WorkOrder.Status.COMPLETED:
        from apps.reports.tasks import generate_work_order_pdf
        generate_work_order_pdf.delay(str(work_order.id))

    WorkOrderStatusHistory.objects.create(
        work_order=work_order,
        from_status=from_status,
        to_status=new_status,
        changed_by=user,
        comment=comment,
    )

    return work_order
