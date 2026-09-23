import uuid

from django.db import models
from django.utils import timezone


class MaintenancePlan(models.Model):
    """
    Plan de tareas: el contenedor de las tareas que se repiten sobre un tipo de
    equipo. Fracttal: Plan de Tareas (174 planes observados).

    Cada activo apunta a un solo plan (Asset.plan) y el plan contiene las
    tareas (PlanTask), cada una con su checklist y su frecuencia. Lo que antes
    vivia aqui (frecuencia, checklist, tipo, fechas, lista de activos) paso a
    esos dos sitios.
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
    classification_1 = models.CharField(max_length=100, blank=True, default="")
    classification_2 = models.CharField(max_length=100, blank=True, default="")
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM,
        help_text="Prioridad por defecto de las tareas nuevas del plan.",
    )
    restrict_to_hospital = models.ForeignKey(
        "assets.Hospital", on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="maintenance_plans"
    )
    is_active = models.BooleanField(default=True)
    fracttal_plan_id = models.CharField(
        max_length=50, blank=True, default="",
        help_text="ID del plan en Fracttal para trazabilidad de migracion."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "maintenance_maintenanceplan"
        ordering = ["name"]

    def __str__(self):
        return self.name


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


class PlanTask(models.Model):
    """
    Tarea de un plan: la definicion que se repite sobre cada activo del plan.

    Fracttal: cada tarea de un Plan de Tareas, con sus subtareas (checklist) y
    su activador. El plan es solo el contenedor; la unidad de protocolo es la
    tarea, y cada una lleva su propia frecuencia. Asi un mismo plan puede tener
    el preventivo semestral, la prueba de instalacion de un solo uso y la prueba
    anual por evento que describio el cliente.
    """

    class Trigger(models.TextChoices):
        DATE = "DATE", "Fecha"
        EVENT = "EVENT", "Evento"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(
        MaintenancePlan, on_delete=models.PROTECT, related_name="tasks"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    task_type = models.CharField(
        max_length=15,
        choices=MaintenancePlan.TaskType.choices,
        default=MaintenancePlan.TaskType.PREVENTIVE,
    )
    priority = models.CharField(
        max_length=10,
        choices=MaintenancePlan.Priority.choices,
        default=MaintenancePlan.Priority.MEDIUM,
    )
    checklist_template = models.ForeignKey(
        "checklists.ChecklistTemplate", on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="plan_tasks",
    )
    # Cuantas veces va cada grupo repetible del checklist: {"Toma": 20}. Como
    # en Fracttal, la cantidad es del plan ("MANT. SALIDAS 20 TOMAS"); lo
    # nuevo es que el bloque se define una vez. No confundir con repeat_count.
    block_counts = models.JSONField(default=dict, blank=True)
    trigger = models.CharField(
        max_length=5, choices=Trigger.choices, default=Trigger.DATE
    )
    frequency_value = models.PositiveIntegerField(null=True, blank=True)
    frequency_unit = models.CharField(
        max_length=6, choices=MaintenancePlan.FrequencyUnit.choices,
        blank=True, default="",
    )
    repeat_count = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Vacio = se repite siempre. N = se ejecuta N veces y no se "
                  "vuelve a generar (Fracttal: Repetir por N).",
    )
    fixed_schedule = models.BooleanField(
        default=False,
        help_text="Con programacion fija la siguiente fecha calculada sale de la "
                  "calculada anterior; sin ella, de la fecha de realizacion. "
                  "Fracttal la trae desmarcada y asi la usa el cliente.",
    )
    estimated_duration = models.DurationField(null=True, blank=True)
    downtime_duration = models.DurationField(null=True, blank=True)
    start_date = models.DateField(
        null=True, blank=True,
        help_text="Fecha calculada de la primera ocurrencia en cada activo. "
                  "Vacio = el dia en que el activo recibe el plan.",
    )
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    fracttal_task_id = models.CharField(
        max_length=50, blank=True, default="",
        help_text="ID de la tarea en Fracttal para trazabilidad de migracion."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "maintenance_plantask"
        ordering = ["plan", "sort_order", "name"]
        constraints = [
            # Un activador por fecha sin frecuencia no puede calcular la
            # siguiente ocurrencia; el de evento no la necesita.
            models.CheckConstraint(
                condition=(
                    models.Q(trigger="EVENT")
                    | (
                        models.Q(frequency_value__isnull=False)
                        & ~models.Q(frequency_unit="")
                    )
                ),
                name="ck_plantask_date_trigger_has_frequency",
            ),
        ]

    def __str__(self):
        return f"{self.plan.name} → {self.name}"


class Task(models.Model):
    """
    Una ocurrencia de trabajo sobre un activo concreto.

    Nace pendiente (del plan o a mano), el planificador la agrupa en una OT y se
    cierra cuando la OT se completa o se cancela. Para cada tarea del plan y
    cada activo hay como mucho una abierta: esa tarea pendiente ES el
    calendario del activo, no hace falta otra tabla.

    Las tres fechas siguen a Fracttal:
      calculated_date  la pone el sistema segun la frecuencia; no cambia nunca
                       (cal_date_maintenance)
      scheduled_date   la vigente; la mueve la reprogramacion
                       (date_maintenance)
      completed_at     la de realizacion (final_date)

    El estado solo lo cambian las funciones de apps.maintenance.services.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        SCHEDULED = "SCHEDULED", "Programada"
        DONE = "DONE", "Finalizada"
        CANCELLED = "CANCELLED", "Cancelada"

    OPEN_STATUSES = (Status.PENDING, Status.SCHEDULED)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(
        "assets.Asset", on_delete=models.PROTECT, related_name="tasks"
    )
    plan_task = models.ForeignKey(
        PlanTask, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="occurrences",
        help_text="Vacio en las tareas creadas a mano (correctivos).",
    )
    work_order = models.ForeignKey(
        "work_orders.WorkOrder", on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="tasks",
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True, default="")
    task_type = models.CharField(
        max_length=15, choices=MaintenancePlan.TaskType.choices
    )
    priority = models.CharField(
        max_length=10,
        choices=MaintenancePlan.Priority.choices,
        default=MaintenancePlan.Priority.MEDIUM,
    )
    checklist_version = models.ForeignKey(
        "checklists.ChecklistTemplateVersion", on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="tasks",
        help_text="Se fija al meter la tarea en una OT, no al crearla: una "
                  "pendiente que espera meses no debe ejecutarse con una "
                  "version vieja del checklist.",
    )
    calculated_date = models.DateField()
    scheduled_date = models.DateField()
    estimated_duration = models.DurationField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancellation_note = models.TextField(
        blank=True, default="",
        help_text="Por que se cancelo: OT cancelada, cambio de plan, anulada a mano.",
    )
    sort_order = models.IntegerField(default=0)
    created_by = models.ForeignKey(
        "users.User", on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="created_tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "maintenance_task"
        ordering = ["sort_order", "created_at"]
        constraints = [
            # Reemplaza el "omitir si el activo ya tiene una OT activa" del
            # motor anterior, pero en la base: dos procesos a la vez no pueden
            # abrir dos ocurrencias de la misma tarea sobre el mismo activo.
            models.UniqueConstraint(
                fields=["plan_task", "asset"],
                condition=models.Q(status__in=["PENDING", "SCHEDULED"]),
                name="uq_task_one_open_per_plantask_asset",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status="PENDING", work_order__isnull=True)
                    | models.Q(status__in=["SCHEDULED", "DONE"], work_order__isnull=False)
                    | models.Q(status="CANCELLED")
                ),
                name="ck_task_status_matches_work_order",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "scheduled_date"], name="idx_task_status_scheduled"),
            models.Index(fields=["asset", "status"], name="idx_task_asset_status"),
        ]

    @property
    def is_open(self):
        return self.status in self.OPEN_STATUSES

    @staticmethod
    def next_maintenance_q():
        """
        Las tareas que cuentan como "proximo mantenimiento" de un activo: las
        abiertas que vienen de un plan activo. Un plan en pausa no cuenta (el
        activo sale "sin plan"), y un correctivo manual tampoco es su proximo
        mantenimiento.
        """
        return models.Q(
            status__in=["PENDING", "SCHEDULED"],
            plan_task__is_active=True,
            plan_task__plan__is_active=True,
        )

    def __str__(self):
        return f"{self.title} [{self.get_status_display()}]"


class RescheduleCause(models.Model):
    """Catalogo de causas de reprogramacion (Fracttal: Catalogos Auxiliares)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "maintenance_reschedulecause"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class TaskReschedule(models.Model):
    """
    Registro de una reprogramacion. Solo se anade: es el historial que Fracttal
    llama "Registros" y lo que permite medir cuanto se reprograma y por que.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(
        Task, on_delete=models.PROTECT, related_name="reschedules"
    )
    from_date = models.DateField()
    to_date = models.DateField()
    cause = models.ForeignKey(
        RescheduleCause, on_delete=models.PROTECT, related_name="reschedules"
    )
    note = models.TextField(blank=True, default="")
    changed_by = models.ForeignKey(
        "users.User", on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="task_reschedules",
    )
    changed_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "maintenance_taskreschedule"
        ordering = ["task", "changed_at"]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("TaskReschedule es un registro: no se edita.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("TaskReschedule es un registro: no se elimina.")

    def __str__(self):
        return f"{self.task.title}: {self.from_date} → {self.to_date}"
