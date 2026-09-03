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
        # RF-OT-03 pide tres requisitos bloqueantes y, si falta alguno, que el
        # sistema "liste exactamente que falta". Por eso se acumulan todos en
        # vez de abortar en el primero: al tecnico en campo no le sirve
        # descubrirlos de uno en uno.
        faltantes = []

        if work_order.checklist_version_id:
            from django.core.exceptions import ObjectDoesNotExist
            try:
                cr = work_order.checklist_response
                if not cr.completed_at:
                    faltantes.append("completar el checklist")
            except ObjectDoesNotExist:
                faltantes.append("completar el checklist")

        # RF-OT-03 exige "al menos 1 foto de evidencia con geolocalizacion",
        # pero RF-EV-01 es explicito en que la falta de senal GPS no bloquea la
        # captura. Se exige entonces la foto, no sus coordenadas: si no, un
        # tecnico en un sotano sin cobertura no podria cerrar la OT.
        if not work_order.photos.exists():
            faltantes.append("subir al menos una foto de evidencia")

        if not work_order.signatures.exists():
            faltantes.append("capturar la firma digital")

        if faltantes:
            raise ValidationError(
                "No se puede enviar a revisión. Falta: " + "; ".join(faltantes) + "."
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
