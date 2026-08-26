import uuid

from django.db import models
from django.utils import timezone


class MaintenancePlan(models.Model):
    """
    Plan de mantenimiento. Genera OTs automáticamente según frecuencia.
    Fracttal: Plan de Tareas (174 planes observados).
    """

    class FrequencyUnit(models.TextChoices):
        DAYS = "DAYS", "Días"
        WEEKS = "WEEKS", "Semanas"
        MONTHS = "MONTHS", "Meses"
        YEARS = "YEARS", "Años"

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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, default="")
    task_type = models.CharField(
        max_length=15, choices=TaskType.choices, default=TaskType.PREVENTIVE
    )
    classification_1 = models.CharField(max_length=100, blank=True, default="")
    classification_2 = models.CharField(max_length=100, blank=True, default="")
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )
    estimated_duration = models.DurationField(null=True, blank=True)
    downtime_duration = models.DurationField(null=True, blank=True)
    frequency_value = models.PositiveIntegerField(default=6)
    frequency_unit = models.CharField(
        max_length=6, choices=FrequencyUnit.choices, default=FrequencyUnit.MONTHS
    )
    checklist_template = models.ForeignKey(
        "checklists.ChecklistTemplate", on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="maintenance_plans"
    )
    assets = models.ManyToManyField(
        "assets.Asset", blank=True,
        related_name="maintenance_plans"
    )
    restrict_to_hospital = models.ForeignKey(
        "assets.Hospital", on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="maintenance_plans"
    )
    is_active = models.BooleanField(default=True)
    last_generated_at = models.DateTimeField(null=True, blank=True)
    next_due_date = models.DateField(null=True, blank=True)
    fracttal_plan_id = models.CharField(
        max_length=50, blank=True, default="",
        help_text="ID del plan en Fracttal para trazabilidad de migracion."
    )
    fracttal_task_id = models.CharField(
        max_length=50, blank=True, default="",
        help_text="ID de la tarea en Fracttal para trazabilidad de migracion."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "maintenance_maintenanceplan"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} (cada {self.frequency_value} {self.get_frequency_unit_display()})"


class MaintenancePlanExecution(models.Model):
    """
    Registro de cada ejecución del plan (cada vez que se generan OTs).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(
        MaintenancePlan, on_delete=models.PROTECT,
        related_name="executions"
    )
    executed_at = models.DateTimeField(default=timezone.now)
    executed_by = models.ForeignKey(
        "users.User", on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="plan_executions"
    )
    work_orders_created = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "maintenance_maintenanceplanexecution"
        ordering = ["-executed_at"]

    def __str__(self):
        return f"{self.plan.name} — {self.executed_at:%Y-%m-%d}"
