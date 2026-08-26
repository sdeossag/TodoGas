import uuid

from django.db import models
from django.utils import timezone


class Photo(models.Model):
    """
    Evidencia fotográfica vinculada a una OT, con metadatos GPS.
    Fracttal: tab Adjuntos en la tarea de la OT.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_order = models.ForeignKey(
        "work_orders.WorkOrder", on_delete=models.PROTECT,
        related_name="photos"
    )
    file_url = models.CharField(max_length=500)
    thumbnail_url = models.CharField(max_length=500, blank=True, default="")
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    taken_at = models.DateTimeField()
    caption = models.CharField(max_length=500, blank=True, default="")
    file_hash = models.CharField(max_length=64, blank=True, default="")
    uploaded_by = models.ForeignKey(
        "users.User", on_delete=models.PROTECT,
        related_name="uploaded_photos"
    )
    offline_uuid = models.UUIDField(null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "evidence_photo"
        ordering = ["work_order", "taken_at"]

    def __str__(self):
        return f"Foto OT-{self.work_order.wo_number} ({self.taken_at:%H:%M})"


class Signature(models.Model):
    """
    Firma digital vinculada a una OT. Inmutable.
    Certifica que el técnico completó el trabajo y el cliente recibió conforme.
    """

    class SignatureType(models.TextChoices):
        TECHNICIAN = "TECHNICIAN", "Firma del técnico"
        CLIENT = "CLIENT", "Firma del cliente"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_order = models.ForeignKey(
        "work_orders.WorkOrder", on_delete=models.PROTECT,
        related_name="signatures"
    )
    signature_type = models.CharField(max_length=12, choices=SignatureType.choices)
    file_url = models.CharField(max_length=500)
    signer_name = models.CharField(max_length=200)
    signer_role = models.CharField(max_length=100, blank=True, default="")
    file_hash = models.CharField(max_length=64)
    signed_at = models.DateTimeField(default=timezone.now)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "evidence_signature"
        constraints = [
            models.UniqueConstraint(
                fields=["work_order", "signature_type"],
                name="uq_signature_wo_type"
            )
        ]

    def __str__(self):
        return f"Firma {self.signature_type} OT-{self.work_order.wo_number}"
