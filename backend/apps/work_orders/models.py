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
        help_text="Secuencial global. Se muestra siempre a través de wo_code."
    )
    wo_year = models.PositiveSmallIntegerField(
        null=True, blank=True, db_index=True,
        help_text="Año de creación. Solo compone el número legible (wo_code)."
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
            # Los tres siguientes los creo la migracion 0002 pero nunca se
            # declararon aqui: sin esto `makemigrations` los da por sobrantes y
            # genera una migracion que los borra.
            models.Index(fields=["status", "scheduled_date"], name="idx_wo_status_scheduled"),
            models.Index(fields=["maintenance_plan", "status"], name="idx_wo_plan_status"),
            models.Index(fields=["assigned_to", "status"], name="idx_wo_assignee_status"),
        ]

    @property
    def wo_code(self):
        """
        Número legible de la OT: OT-2026-00001 (RF-OT-02).

        El secuencial es global, no se reinicia cada año: el requisito dice
        "el secuencial es global (no por hospital)" y el año solo compone la
        etiqueta. Mantenerlo global evita cambiar la unicidad de wo_number y
        que dos OTs de años distintos compartan secuencial.
        """
        año = self.wo_year or (self.created_at.year if self.created_at else None)
        if año is None:
            return f"OT-{self.wo_number:05d}"
        return f"OT-{año}-{self.wo_number:05d}"

    def save(self, *args, **kwargs):
        if not self.wo_number:
            from django.db import transaction
            with transaction.atomic():
                last = WorkOrder.objects.select_for_update().order_by(
                    '-wo_number').first()
                self.wo_number = (last.wo_number + 1) if last else 1
        if not self.wo_year:
            self.wo_year = timezone.now().year
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.wo_code} [{self.status}]"


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
