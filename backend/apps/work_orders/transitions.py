from datetime import timedelta

from django.db import transaction
from rest_framework.exceptions import APIException, ValidationError

from apps.users import permisos

from .models import WorkOrder, WorkOrderStatusHistory


class FirmaRequerida(APIException):
    """Quien aprueba no tiene firma guardada: HTTP 400 con el cuerpo fijado con el frontend."""

    status_code = 400
    default_code = "firma_requerida"

    def __init__(self):
        super().__init__({
            "code": "firma_requerida",
            "detail": "Registra tu firma en Mi perfil para aprobar esta orden.",
        })


# Quien puede quedar como asignado de una OT y ejecutarla. Ademas del tecnico,
# el administrador y el supervisor (decision del 2026-10-01): hacen reportes de
# instalaciones a las que no va un tecnico de mantenimiento.
EXECUTOR_ROLES = ("TEC", "ADMIN", "SUP")

# Each key is (from_status, to_status).
# "roles" lists which role strings can perform the transition.
# "require_assignee" means the user must be the assigned_to of the OT.
ALLOWED_TRANSITIONS = {
    (WorkOrder.Status.PENDING, WorkOrder.Status.IN_PROGRESS): {
        "roles": list(EXECUTOR_ROLES),
        "require_assignee": True,
    },
    (WorkOrder.Status.IN_PROGRESS, WorkOrder.Status.IN_REVIEW): {
        "roles": list(EXECUTOR_ROLES),
        "require_assignee": True,
    },
    # Aprobar y devolver son del permiso "revisar" (admin y supervisor lo traen;
    # a un tecnico se le puede sumar, apps.users.permisos).
    (WorkOrder.Status.IN_REVIEW, WorkOrder.Status.COMPLETED): {
        "permiso": "ot.revisar",
        "require_assignee": False,
    },
    (WorkOrder.Status.IN_REVIEW, WorkOrder.Status.IN_PROGRESS): {
        "permiso": "ot.revisar",
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
        if not permisos.puede(user, "ot.cancelar"):
            raise ValidationError("No tienes permiso para cancelar una OT: es del ADMIN o de quien él habilite.")
        if not comment:
            raise ValidationError("Se requiere un comentario para cancelar una OT.")
        return True

    key = (from_status, new_status)
    if key not in ALLOWED_TRANSITIONS:
        raise ValidationError(
            f"La transición '{from_status}' → '{new_status}' no está permitida."
        )

    rule = ALLOWED_TRANSITIONS[key]

    if "permiso" in rule:
        permitido = permisos.puede(user, rule["permiso"])
    else:
        permitido = user.role in rule["roles"]
    if not permitido:
        raise ValidationError(
            f"Tu rol '{user.role}' no puede realizar la transición "
            f"'{from_status}' → '{new_status}'."
        )

    if rule.get("require_assignee") and work_order.assigned_to_id != user.id:
        if user.role == "TEC":
            raise ValidationError("Solo el técnico asignado puede realizar esta transición.")
        raise ValidationError(
            "La ejecuta quien la tiene asignada. Asígnatela para iniciarla o enviarla a revisión."
        )

    if from_status == WorkOrder.Status.IN_PROGRESS and new_status == WorkOrder.Status.IN_REVIEW:
        # RF-OT-03 pide tres requisitos bloqueantes y, si falta alguno, que el
        # sistema "liste exactamente que falta". Por eso se acumulan todos en
        # vez de abortar en el primero: al tecnico en campo no le sirve
        # descubrirlos de uno en uno.
        faltantes = []

        # Cada tarea con checklist tiene que tenerlo completo. Con varias
        # tareas se nombra el activo, para que el tecnico sepa cual le falta.
        from django.core.exceptions import ObjectDoesNotExist
        tareas = [
            t for t in work_order.tasks.select_related("asset")
            if t.checklist_version_id and t.status != "CANCELLED"
        ]
        # Lo que quedo pendiente (no se pudo revisar) cuenta como incompleto y se
        # nombra: "Cubiculo 7: pendiente - aislado por aerosoles".
        from .serializers import pendientes_de_la_ot

        faltantes.extend(pendientes_de_la_ot(work_order))
        for tarea in tareas:
            try:
                completo = bool(tarea.checklist_response.completed_at)
            except ObjectDoesNotExist:
                completo = False
            if not completo:
                if len(tareas) == 1:
                    faltantes.append("completar el checklist")
                else:
                    faltantes.append(f"completar el checklist de {tarea.asset.name}")

        # RF-OT-03 exige "al menos 1 foto de evidencia con geolocalizacion",
        # pero RF-EV-01 es explicito en que la falta de senal GPS no bloquea la
        # captura. Se exige entonces la foto, no sus coordenadas: si no, un
        # tecnico en un sotano sin cobertura no podria cerrar la OT.
        if not work_order.photos.filter(hidden=False).exists():
            faltantes.append("subir al menos una foto de evidencia")

        # Solo cuenta la del tecnico: la de validacion la pone la aprobacion
        # despues, y no puede hacer pasar por firmada una OT sin firma.
        if not work_order.signatures.filter(signature_type="TECHNICIAN").exists():
            faltantes.append("capturar la firma digital")

        if faltantes:
            raise ValidationError(
                "No se puede enviar a revisión. Falta: " + "; ".join(faltantes) + "."
            )

    return True


def apply_transition(work_order, new_status, user, comment="", client_time=None):
    """
    Todo o nada: la OT, el ciclo de sus tareas y el historial se guardan juntos.
    La fila de la OT queda bloqueada hasta el final, asi dos aprobaciones a la
    vez no pasan las dos la validacion. El acta y el correo salen despues del
    commit: un worker que los tome antes leeria la OT sin aprobar.

    client_time: hora del telefono cuando la transicion se hizo sin red. Se
    acepta con la misma politica que el resto de datos de campo (device_time);
    fuera de tolerancia o ausente, vale la hora del servidor.
    """
    with transaction.atomic():
        # El estado que vale es el de la fila bloqueada, no el que traia el
        # objeto: otro pedido pudo cambiarlo mientras tanto.
        work_order.status = (
            WorkOrder.objects.select_for_update().values_list("status", flat=True).get(pk=work_order.pk)
        )
        desde = work_order.status
        _aplicar(work_order, new_status, user, comment, client_time)

    if new_status == WorkOrder.Status.COMPLETED:
        from apps.reports.tasks import generate_work_order_pdf, send_serious_findings_email

        def _avisar():
            generate_work_order_pdf.delay(str(work_order.id))
            # Hallazgo critico o equipo fuera de servicio: el hospital se
            # entera al aprobar, sin esperar a leer el acta.
            if any(f.is_serious for f in work_order.findings.all()):
                send_serious_findings_email.delay(str(work_order.id))

        transaction.on_commit(_avisar)

    # Devolver a correccion: el tecnico asignado se entera del motivo. Si quien
    # devuelve es el mismo asignado (admin que ejecuto su propia OT) no hay a
    # quien avisar.
    if (
        desde == WorkOrder.Status.IN_REVIEW
        and new_status == WorkOrder.Status.IN_PROGRESS
        and work_order.assigned_to_id
        and work_order.assigned_to_id != user.id
    ):
        transaction.on_commit(lambda: avisar_rechazo(work_order, user, comment))

    return work_order


def avisar_rechazo(work_order, rechaza, motivo):
    """
    Push y correo al tecnico asignado. Va despues del commit y un fallo de envio
    no deshace la devolucion: se registra y se sigue.
    """
    import logging

    log = logging.getLogger(__name__)
    try:
        from apps.notifications.service import send_rejection_notification

        send_rejection_notification(work_order, rechaza, motivo)
    except Exception:
        log.exception("No se pudo enviar el aviso push del rechazo de la OT %s", work_order.pk)
    try:
        from .tasks import send_rejection_email

        send_rejection_email.delay(str(work_order.pk), str(rechaza.pk), motivo)
    except Exception:
        log.exception("No se pudo encolar el correo del rechazo de la OT %s", work_order.pk)


def _aplicar(work_order, new_status, user, comment, client_time=None):
    validate_transition(work_order, new_status, user, comment)

    # Aprobar firma con la firma guardada de quien aprueba (tambien el
    # administrador que ejecuto la OT). Sin ella no se aprueba nada.
    firma_bytes = None
    if new_status == WorkOrder.Status.COMPLETED:
        from apps.evidence.copia_firma import leer_firma_guardada

        firma_bytes = leer_firma_guardada(user)
        if firma_bytes is None:
            raise FirmaRequerida()

    from_status = work_order.status
    from .device_time import device_time

    now = device_time(client_time, work_order)

    work_order.status = new_status

    if new_status == WorkOrder.Status.IN_PROGRESS and not work_order.started_at:
        work_order.started_at = now

    if new_status == WorkOrder.Status.COMPLETED:
        work_order.completed_at = now
        if work_order.started_at:
            # started_at puede haberse puesto con la hora del servidor al
            # sincronizar: la duracion nunca queda negativa.
            work_order.actual_duration = max(now - work_order.started_at, timedelta(0))

    work_order.save()

    # El ciclo de las tareas va antes que el acta: el hash de integridad cubre
    # el estado de cada tarea, y si se calculara con ellas aun "programadas"
    # la verificacion posterior (ya "finalizadas") daria alteracion.
    from apps.maintenance import services
    if new_status == WorkOrder.Status.COMPLETED:
        services.complete_work_order_tasks(work_order)
    elif new_status == WorkOrder.Status.CANCELLED:
        services.cancel_work_order_tasks(work_order)

    # El historial va antes que el acta: de ahi sale el "Validado por" (quien
    # aprobo y cuando). En desarrollo el acta se genera en el acto y saldria
    # sin validacion.
    WorkOrderStatusHistory.objects.create(
        work_order=work_order,
        from_status=from_status,
        to_status=new_status,
        changed_by=user,
        comment=comment,
        changed_at=now,
    )

    if firma_bytes is not None:
        _firmar_validacion(work_order, user, firma_bytes, now)


def _firmar_validacion(work_order, user, firma_bytes, now):
    """
    La firma de validacion de la OT: copia propia de la firma guardada de quien
    aprueba. Va en la misma transaccion que la aprobacion, asi una aprobacion
    que falla no deja firma huerfana, y antes del acta, que la imprime.
    """
    from apps.evidence.copia_firma import guardar_copia_de_firma
    from apps.evidence.models import Signature

    key, file_hash = guardar_copia_de_firma(work_order, Signature.SignatureType.VALIDATION, firma_bytes)
    try:
        Signature.objects.create(
            work_order=work_order,
            signature_type=Signature.SignatureType.VALIDATION,
            file_url=key,
            signer_name=(f"{user.first_name} {user.last_name}".strip() or user.email)[:200],
            signer_role=user.get_role_display(),
            file_hash=file_hash,
            signed_at=now,
        )
    except Exception:
        from django.core.files.storage import default_storage

        default_storage.delete(key)
        raise
