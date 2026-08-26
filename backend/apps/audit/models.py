import uuid

from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    """
    Log de auditoría inmutable (append-only).
    Registra cualquier cambio en cualquier entidad del sistema.
    """

    class Action(models.TextChoices):
        CREATE = "CREATE", "Crear"
        UPDATE = "UPDATE", "Actualizar"
        DELETE = "DELETE", "Eliminar"
        STATUS_CHANGE = "STATUS_CHANGE", "Cambio de estado"
        LOGIN = "LOGIN", "Inicio de sesión"
        SYNC = "SYNC", "Sincronización offline"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "users.User", on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="audit_logs"
    )
    action = models.CharField(max_length=15, choices=Action.choices)
    entity_type = models.CharField(max_length=100)
    entity_id = models.UUIDField()
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True, default="")
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_auditlog"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id"], name="idx_audit_entity"),
            models.Index(fields=["user", "timestamp"], name="idx_audit_user_time"),
        ]

    def save(self, *args, **kwargs):
        """Prohibir updates: solo INSERT."""
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise ValueError("AuditLog es append-only. No se permite UPDATE.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prohibir deletes."""
        raise ValueError("AuditLog es append-only. No se permite DELETE.")

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.action} {self.entity_type} por {self.user}"
