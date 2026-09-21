from .models import NotificationLog


def send_push_notification(user, title, body, data=None):
    """
    Placeholder FCM. Crea un NotificationLog y escribe en consola.
    En Sprint 11 se reemplaza la implementacion sin cambiar esta interfaz.
    """
    notification_type = (data or {}).get("type", NotificationLog.NotificationType.GENERAL)

    NotificationLog.objects.create(
        user=user,
        channel=NotificationLog.Channel.PUSH,
        notification_type=notification_type,
        title=title,
        body=body,
        entity_type=(data or {}).get("entity_type", ""),
        entity_id=(data or {}).get("entity_id") or None,
    )
    print(f"PUSH -> {user.email}: {title}")


def _que_se_atiende(work_order):
    """Un activo por su nombre; varios, por cuantos son."""
    tareas = list(work_order.tasks.select_related("asset")[:2])
    if len(tareas) == 1:
        return tareas[0].asset.name
    total = work_order.tasks.count()
    return f"{total} activos" if total else work_order.title


def send_assignment_notification(work_order):
    if not work_order.assigned_to:
        return
    user = work_order.assigned_to
    send_push_notification(
        user=user,
        title=f"Nueva OT asignada: {work_order.wo_code}",
        body=f"{_que_se_atiende(work_order)} — {work_order.hospital.name}",
        data={
            "type": NotificationLog.NotificationType.WO_ASSIGNED,
            "entity_type": "WorkOrder",
            "entity_id": str(work_order.id),
        },
    )


def send_overdue_alert(work_order):
    if not work_order.assigned_to:
        return
    user = work_order.assigned_to
    send_push_notification(
        user=user,
        title=f"OT vencida: {work_order.wo_code}",
        body=f"{_que_se_atiende(work_order)} — fecha programada: {work_order.scheduled_date}",
        data={
            "type": NotificationLog.NotificationType.WO_OVERDUE,
            "entity_type": "WorkOrder",
            "entity_id": str(work_order.id),
        },
    )
