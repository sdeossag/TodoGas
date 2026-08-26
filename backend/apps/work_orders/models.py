import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class WorkOrder(models.Model):
    """
    Orden de Trabajo. 1 OT = 1 Asset (simplificación para offline).
    Fracttal: OT con Kanban de estados Pendiente → En Proceso → En Revisión → Finalizada.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        IN_PROGRESS = "IN_PROGRESS", "En Proceso"
        IN_REVIEW = "IN_REVIEW", "En Revisión"
        COMPLETED = "COMPLETED", "Finalizada"
        CANCELLED = "CANCELLED", "Cancelada"

    class TaskType(models.TextChoices):
        PREVENTIVE = "PREVENTIVE", "Preventivo"
        CORRECTIVE = "CORRECTIVE", "Correctivo"
        VERIFICATION = "VERIFICATION", "Verificación"
        INSTALLATION = "INSTALLATION", "Instalación"
        DELIVERY = "DELIVERY", "Entrega"

    class Priority(models.TextChoices):
        HIGH = "HIGH", "Alta"
        MEDIUM = "MEDIUM", "Media"
        LOW = "LOW", "Baja"

    class ProgressMeasure(models.TextChoices):
        SUBTASKS = "SUBTASKS", "Todas las subtareas"
        MANUAL = "MANUAL", "Manual"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wo_number = models.PositiveIntegerField(
        unique=True,
        help_text="Número legible auto-incremental. Fracttal: 19190, 19197, etc."
    )
    asset = models.ForeignKey(
        "assets.Asset", on_delete=models.PROTECT,
        related_name="work_orders"
    )
    task_type = models.CharField(max_length=15, choices=TaskType.choices)
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True, default="")
    classification_1 = models.CharField(max_length=100, blank=True, default="")
    classification_2 = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.PENDING,
        db_index=True
    )
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )
    progress = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    progress_measure = models.CharField(
        max_length=10, choices=ProgressMeasure.choices, default=ProgressMeasure.SUBTASKS
    )
    assigned_to = models.ForeignKey(
        "users.User", on_delete=models.PROTECT,
        related_name="assigned_work_orders",
        null=True, blank=True
    )
    created_by = models.ForeignKey(
        "users.User", on_delete=models.PROTECT,
        related_name="created_work_orders"
    )
    scheduled_date = models.DateField()
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    estimated_duration = models.DurationField(null=True, blank=True)
    actual_duration = models.DurationField(null=True, blank=True)
    downtime = models.DurationField(null=True, blank=True)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    rating = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    notes = models.TextField(blank=True, default="")
    maintenance_plan = models.ForeignKey(
        "maintenance.MaintenancePlan", on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="generated_work_orders"
    )
    request_number = models.IntegerField(null=True, blank=True)
    checklist_version = models.ForeignKey(
        "checklists.ChecklistTemplateVersion", on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="work_orders"
    )
    synced_at = models.DateTimeField(null=True, blank=True)
    offline_uuid = models.UUIDField(null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "work_orders_workorder"
        ordering = ["-wo_number"]
        indexes = [
            models.Index(fields=["status", "assigned_to"], name="idx_wo_status_assignee"),
            models.Index(fields=["asset", "status"], name="idx_wo_asset_status"),
            models.Index(fields=["scheduled_date"], name="idx_wo_scheduled_date"),
        ]

    def save(self, *args, **kwargs):
        if not self.wo_number:
            from django.db import transaction
            with transaction.atomic():
                last = WorkOrder.objects.select_for_update().order_by(
                    '-wo_number').first()
                self.wo_number = (last.wo_number + 1) if last else 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"OT-{self.wo_number} [{self.status}]"


class WorkOrderStatusHistory(models.Model):
    """
    Log de cambios de estado de una OT. Append-only.
    Cada cambio de estado se registra con timestamp y usuario.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_order = models.ForeignKey(
        WorkOrder, on_delete=models.PROTECT,
        related_name="status_history"
    )
    from_status = models.CharField(
        max_length=15, choices=WorkOrder.Status.choices,
        blank=True, default=""
    )
    to_status = models.CharField(max_length=15, choices=WorkOrder.Status.choices)
    changed_by = models.ForeignKey(
        "users.User", on_delete=models.PROTECT,
        related_name="wo_status_changes"
    )
    comment = models.TextField(blank=True, default="")
    changed_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "work_orders_workorderstatushistory"
        ordering = ["work_order", "changed_at"]

    def __str__(self):
        return f"OT-{self.work_order.wo_number}: {self.from_status} → {self.to_status}"
