import uuid

from django.db import models
from django.utils import timezone


class GeneratedReport(models.Model):
    """
    PDF generado automáticamente al completar una OT.
    Incluye: datos del activo, checklist respondido, fotos, firmas.
    """

    class ReportType(models.TextChoices):
        WORK_ORDER = "WORK_ORDER", "Reporte de OT"
        MAINTENANCE = "MAINTENANCE", "Reporte de mantenimiento"
        DELIVERY = "DELIVERY", "Acta de entrega"
        CUSTOM = "CUSTOM", "Personalizado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_order = models.ForeignKey(
        "work_orders.WorkOrder", on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="reports"
    )
    report_type = models.CharField(max_length=15, choices=ReportType.choices)
    title = models.CharField(max_length=255)
    file_url = models.CharField(max_length=500)
    # sha256 de los bytes del PDF: prueba que el archivo entregado no cambio.
    file_hash = models.CharField(max_length=64)
    # sha256 del contenido probatorio de la OT (apps.work_orders.integrity):
    # prueba que el registro en base de datos sigue diciendo lo mismo. Vacio en
    # reportes que no son de una OT concreta, como el consolidado por periodo.
    content_hash = models.CharField(max_length=64, blank=True, default="")
    integrity_version = models.CharField(max_length=8, blank=True, default="")
    generated_by = models.ForeignKey(
        "users.User", on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="generated_reports"
    )
    generated_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reports_generatedreport"
        ordering = ["-generated_at"]

    def __str__(self):
        return f"{self.report_type}: {self.title}"


class ReportSendLog(models.Model):
    """Registro de envío de reportes por correo electrónico."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(
        GeneratedReport, on_delete=models.PROTECT,
        related_name="send_logs"
    )
    recipient_email = models.EmailField()
    recipient_name = models.CharField(max_length=200, blank=True, default="")
    sent_at = models.DateTimeField(default=timezone.now)
    was_successful = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reports_reportsendlog"
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.report.title} → {self.recipient_email}"
