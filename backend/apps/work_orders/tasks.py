import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage

from apps.users.models import User

from .models import WorkOrder

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_rejection_email(self, work_order_id, rechaza_id, motivo):
    """
    Correo al tecnico asignado cuando le devuelven la OT a correccion: el codigo,
    quien la devolvio y el motivo, para que no tenga que abrir la app a ver por que.
    """
    try:
        wo = WorkOrder.objects.select_related("assigned_to", "hospital").get(id=work_order_id)
        tecnico = wo.assigned_to
        if tecnico is None or not tecnico.email:
            return {"status": "skipped", "reason": "no email"}
        rechaza = User.objects.get(id=rechaza_id)
        quien = f"{rechaza.first_name} {rechaza.last_name}".strip() or rechaza.email
        cuerpo = (
            f"Hola {tecnico.first_name},\n\n"
            f"{quien} devolvió la orden {wo.wo_code} ({wo.title}, {wo.hospital.name}) "
            f"para que la corrijas.\n\n"
            f"Motivo:\n{motivo}\n\n"
            f"Entra a la app, corrige lo indicado y envíala de nuevo a revisión:\n"
            f"{settings.FRONTEND_URL}/mis-ordenes/{wo.id}\n\n"
            f"Equipo TodoGas"
        )
        EmailMessage(
            subject=f"OT devuelta para corrección - {wo.wo_code}",
            body=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[tecnico.email],
        ).send()
        return {"status": "sent", "to": [tecnico.email]}
    except Exception as exc:
        logger.exception("No se pudo avisar el rechazo de la OT %s: %s", work_order_id, exc)
        if self.request.is_eager or self.request.retries >= self.max_retries:
            return {"status": "failed", "error": str(exc)}
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
