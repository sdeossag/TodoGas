import uuid

from django.db import models
from django.utils import timezone


class Photo(models.Model):
    """
    Evidencia fotográfica vinculada a una OT, con metadatos GPS.
    Fracttal: tab Adjuntos en la tarea de la OT.
    """

    class Stage(models.TextChoices):
        BEFORE = "BEFORE", "Antes"
        AFTER = "AFTER", "Después"
        NONE = "", "Sin etiqueta"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_order = models.ForeignKey(
        "work_orders.WorkOrder", on_delete=models.PROTECT,
        related_name="photos"
    )
    # Opcional: en una OT con varios activos, de cual es la foto. El acta las
    # agrupa por tarea cuando la tienen.
    task = models.ForeignKey(
        "maintenance.Task", on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="photos",
    )
    # Foto de un hallazgo: sale con el hallazgo en el acta y en el portal.
    finding = models.ForeignKey(
        "work_orders.Finding", on_delete=models.PROTECT,
        null=True, blank=True, related_name="photos",
    )
    file_url = models.CharField(max_length=500)
    thumbnail_url = models.CharField(max_length=500, blank=True, default="")
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    taken_at = models.DateTimeField()
    caption = models.CharField(max_length=500, blank=True, default="")
    # Antes o despues del trabajo (audio3 ~05:10). Vacio en las fotos anteriores
    # a esta decision y en las que el tecnico no etiqueta.
    stage = models.CharField(max_length=6, choices=Stage.choices, blank=True, default="")
    file_hash = models.CharField(max_length=64, blank=True, default="")
    uploaded_by = models.ForeignKey(
        "users.User", on_delete=models.PROTECT,
        related_name="uploaded_photos"
    )
    offline_uuid = models.UUIDField(null=True, blank=True, unique=True)
    # Una foto mala no se borra (trazabilidad): se oculta del acta y del portal
    # del hospital, y queda quien la oculto (decision del 2026-10-01).
    hidden = models.BooleanField(default=False)
    hidden_by = models.ForeignKey(
        "users.User", on_delete=models.PROTECT, null=True, blank=True,
        related_name="hidden_photos"
    )
    hidden_at = models.DateTimeField(null=True, blank=True)
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
        # La pone la aprobacion de la OT con la firma guardada de quien aprueba;
        # no se crea ni se borra por la API de firmas.
        VALIDATION = "VALIDATION", "Firma de validación"

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
        # Orden estable para paginar, y deja la firma del tecnico antes que la
        # del cliente en el acta.
        ordering = ["work_order", "signature_type"]
        constraints = [
            models.UniqueConstraint(
                fields=["work_order", "signature_type"],
                name="uq_signature_wo_type"
            )
        ]

    def __str__(self):
        return f"Firma {self.signature_type} OT-{self.work_order.wo_number}"


class UserSignature(models.Model):
    """
    Firma que un usuario del sistema (tecnico, supervisor, administrador)
    registra una vez para no dibujarla en cada OT. Es un dato personal: solo la
    ve y la usa su duena, y puede reemplazarla o borrarla cuando quiera.

    No es la firma de la OT: al aplicarla se hace una copia propia en Signature,
    asi cambiarla o borrarla despues no altera las actas ya firmadas. La firma
    de quien recibe en el hospital (CLIENT) no se guarda nunca.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        "users.User", on_delete=models.PROTECT, related_name="saved_signature"
    )
    file_url = models.CharField(max_length=500)
    file_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "evidence_usersignature"

    def __str__(self):
        return f"Firma guardada de {self.user_id}"
