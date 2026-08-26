import uuid

from django.db import models
from django.utils import timezone


class NotificationLog(models.Model):
    """
    Registro de notificaciones enviadas.
    Fracttal: panel de notificaciones en el header del dashboard.
    """

    class Channel(models.TextChoices):
        PUSH = "PUSH", "Push notification"
        EMAIL = "EMAIL", "Correo electrónico"
        SMS = "SMS", "SMS"
        IN_APP = "IN_APP", "Notificación in-app"

    class NotificationType(models.TextChoices):
        WO_ASSIGNED = "WO_ASSIGNED", "OT asignada"
        WO_COMPLETED = "WO_COMPLETED", "OT completada"
        WO_OVERDUE = "WO_OVERDUE", "OT vencida"
        PLAN_GENERATED = "PLAN_GENERATED", "Plan generó OTs"
        STOCK_LOW = "STOCK_LOW", "Stock bajo"
        GENERAL = "GENERAL", "General"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "users.User", on_delete=models.PROTECT,
        related_name="notifications"
    )
    channel = models.CharField(max_length=6, choices=Channel.choices)
    notification_type = models.CharField(max_length=15, choices=NotificationType.choices)
    title = models.CharField(max_length=255)
    body = models.TextField()
    entity_type = models.CharField(max_length=100, blank=True, default="")
    entity_id = models.UUIDField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(default=timezone.now)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications_notificationlog"
        ordering = ["-sent_at"]
        indexes = [
            models.Index(
                fields=["user", "is_read", "sent_at"],
                name="idx_notif_user_read"
            ),
        ]

    def __str__(self):
        return f"{self.notification_type} → {self.user.email}"
