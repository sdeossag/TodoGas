from django.db.models import Min
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from apps.assets.models import Asset
from apps.checklists.models import ChecklistTemplate
from apps.users.scope import ScopedFieldsMixin

from .models import MaintenancePlan, PlanTask, RescheduleCause, Task, TaskReschedule

# Fase 2 del modelo de tareas: el plan es una cabecera (nombre, prioridad por
# defecto, activo o pausado) y lo que se repite vive en sus tareas (PlanTask).
# Los activos no se guardan en el plan: cada activo apunta a su plan (D7).


# ── Plan de tareas ────────────────────────────────────────────────────────────

class PlanTaskSummarySerializer(serializers.ModelSerializer):
    """Lo que la lista de planes muestra de cada tarea."""

    class Meta:
        model = PlanTask
        fields = [
            "id", "name", "task_type", "trigger", "frequency_value",
            "frequency_unit", "repeat_count", "is_active",
        ]


class MaintenancePlanListSerializer(serializers.ModelSerializer):
    tasks = serializers.SerializerMethodField()
    assets_count = serializers.IntegerField(source="assets_total", read_only=True)
    pending_count = serializers.IntegerField(source="pending_total", read_only=True)
    overdue_count = serializers.IntegerField(source="overdue_total", read_only=True)
    next_due_date = serializers.DateField(source="next_due", read_only=True)
    compliance_percentage = serializers.SerializerMethodField()

    class Meta:
        model = MaintenancePlan
        fields = [
            "id", "name", "description", "priority", "is_active",
            "classification_1", "classification_2",
            "tasks", "assets_count", "pending_count", "overdue_count",
            "next_due_date", "compliance_percentage",
        ]

    def get_tasks(self, obj):
        return PlanTaskSummarySerializer(obj.tasks.all(), many=True).data

    def get_compliance_percentage(self, obj):
        # Tareas del plan programadas este mes que se hicieron. Cuenta por
        # activo, no por OT: una OT puede llevar tareas de varios activos.
        total = getattr(obj, "month_total", 0)
        if not total:
            return None
        return round(obj.month_done / total * 100, 1)


class MaintenancePlanDetailSerializer(MaintenancePlanListSerializer):
    restrict_to_hospital = serializers.SerializerMethodField()
    assets = serializers.SerializerMethodField()

    class Meta(MaintenancePlanListSerializer.Meta):
        fields = MaintenancePlanListSerializer.Meta.fields + [
            "restrict_to_hospital", "assets", "created_at", "updated_at",
        ]

    def get_tasks(self, obj):
        return PlanTaskSerializer(obj.tasks.all(), many=True).data

    def get_restrict_to_hospital(self, obj):
        if obj.restrict_to_hospital_id:
            return {"id": str(obj.restrict_to_hospital_id), "name": obj.restrict_to_hospital.name}
        return None

    def get_assets(self, obj):
        proximas = dict(
            Task.objects.filter(
                plan_task__plan=obj, plan_task__is_active=True,
                status__in=Task.OPEN_STATUSES,
            )
            .order_by()
            .values("asset_id")
            .annotate(fecha=Min("scheduled_date"))
            .values_list("asset_id", "fecha")
        )
        return [
            {
                "id": str(a.id),
                "code": a.code,
                "name": a.name,
                "status": a.status,
                "hospital": {"id": str(a.hospital_id), "name": a.hospital.name},
                "node_path": a.node.path if a.node_id else "",
                "next_due_date": proximas.get(a.id),
            }
            for a in obj.assets.select_related("hospital", "node").order_by("code")
        ]


class MaintenancePlanCreateUpdateSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        max_length=255,
        validators=[UniqueValidator(
            queryset=MaintenancePlan.objects.all(),
            message="Ya existe un plan de tareas con ese nombre.",
        )],
    )

    class Meta:
        model = MaintenancePlan
        fields = [
            "id", "name", "description", "classification_1", "classification_2",
            "priority", "restrict_to_hospital", "is_active",
        ]
        read_only_fields = ["id"]


class AssetIdsSerializer(serializers.Serializer):
    asset_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Asset.objects.select_related("plan"), allow_empty=False,
    )


# ── Tarea del plan ────────────────────────────────────────────────────────────

class PlanTaskSerializer(serializers.ModelSerializer):
    checklist_template = serializers.PrimaryKeyRelatedField(
        queryset=ChecklistTemplate.objects.all(), required=False, allow_null=True,
    )
    checklist_template_name = serializers.SerializerMethodField()
    open_count = serializers.SerializerMethodField()
    done_count = serializers.SerializerMethodField()

    class Meta:
        model = PlanTask
        fields = [
            "id", "plan", "name", "description", "task_type", "priority",
            "checklist_template", "checklist_template_name", "block_counts",
            "trigger", "frequency_value", "frequency_unit", "repeat_count",
            "fixed_schedule", "estimated_duration", "downtime_duration",
            "start_date", "sort_order", "is_active", "open_count", "done_count",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            "priority": {"required": False},
            "sort_order": {"required": False},
        }

    def get_checklist_template_name(self, obj):
        return obj.checklist_template.name if obj.checklist_template_id else None

    def get_open_count(self, obj):
        if hasattr(obj, "open_total"):
            return obj.open_total
        return obj.occurrences.filter(status__in=Task.OPEN_STATUSES).count()

    def get_done_count(self, obj):
        if hasattr(obj, "done_total"):
            return obj.done_total
        return obj.occurrences.filter(status=Task.Status.DONE).count()

    def validate_checklist_template(self, value):
        """Rechaza plantillas sin version publicada.

        La tarea se ata a la version al entrar en una OT: si no hay ninguna con
        is_current, entra sin nada que diligenciar.
        """
        if value is None:
            return value
        if not value.versions.filter(is_current=True).exists():
            raise serializers.ValidationError(
                f"La plantilla '{value.name}' no tiene una version publicada. "
                "Publicala desde el editor de checklists o elige otra plantilla."
            )
        return value

    def validate_block_counts(self, value):
        """{"Toma": 20}: cuantas veces va cada grupo repetible del checklist."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Indica la cantidad por grupo, p. ej. {\"Toma\": 20}.")
        limpio = {}
        for grupo, cuantas in value.items():
            try:
                cuantas = int(cuantas)
            except (TypeError, ValueError):
                cuantas = 0
            if cuantas < 1:
                raise serializers.ValidationError(f"«{grupo}» necesita al menos 1.")
            limpio[str(grupo)] = cuantas
        return limpio

    def validate_repeat_count(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError(
                "Indica cuantas veces (al menos 1), o deja vacio para repetir siempre."
            )
        return value

    def validate(self, attrs):
        instancia = self.instance
        if instancia is not None:
            attrs.pop("plan", None)  # una tarea no se cambia de plan

        def actual(campo, defecto=None):
            if campo in attrs:
                return attrs[campo]
            return getattr(instancia, campo) if instancia else defecto

        if actual("trigger", PlanTask.Trigger.DATE) == PlanTask.Trigger.DATE:
            errores = {}
            valor = actual("frequency_value")
            if not valor or valor <= 0:
                errores["frequency_value"] = "Una tarea por fecha necesita una frecuencia mayor a 0."
            if not actual("frequency_unit"):
                errores["frequency_unit"] = "Indica la unidad de la frecuencia."
            if errores:
                raise serializers.ValidationError(errores)
        return attrs

    def _user(self):
        request = self.context.get("request")
        return getattr(request, "user", None)

    def create(self, validated_data):
        from . import services

        plan = validated_data["plan"]
        validated_data.setdefault("priority", plan.priority)
        if "sort_order" not in validated_data:
            ultima = plan.tasks.order_by("-sort_order").values_list("sort_order", flat=True).first()
            validated_data["sort_order"] = (ultima or 0) + 1
        tarea = PlanTask.objects.create(**validated_data)
        if tarea.is_active and tarea.trigger == PlanTask.Trigger.DATE and plan.is_active:
            services.sync_plan_task(tarea, self._user())
        return tarea

    def update(self, instance, validated_data):
        from . import services

        antes = {
            "is_active": instance.is_active,
            "trigger": instance.trigger,
            "start_date": instance.start_date,
        }
        instance = super().update(instance, validated_data)
        services.plan_task_changed(instance, antes, self._user())
        # Los conteos anotados al leer la tarea ya no valen: se recalculan.
        for anotacion in ("open_total", "done_total"):
            instance.__dict__.pop(anotacion, None)
        return instance


class EventOccurrenceSerializer(serializers.Serializer):
    asset = serializers.PrimaryKeyRelatedField(queryset=Asset.objects.all())
    scheduled_date = serializers.DateField()


# ── Tareas ────────────────────────────────────────────────────────────────────

class TaskSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    asset = serializers.SerializerMethodField()
    hospital = serializers.SerializerMethodField()
    plan = serializers.SerializerMethodField()
    plan_task = serializers.SerializerMethodField()
    work_order = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    is_rescheduled = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id", "status", "status_display", "title", "description", "task_type",
            "priority", "calculated_date", "scheduled_date", "completed_at",
            "estimated_duration", "cancellation_note", "is_overdue", "is_rescheduled",
            "asset", "hospital", "plan", "plan_task", "work_order",
        ]

    def get_asset(self, obj):
        a = obj.asset
        return {
            "id": str(a.id),
            "code": a.code,
            "name": a.name,
            "node_id": str(a.node_id) if a.node_id else None,
            "node_path": a.node.path if a.node_id else "",
        }

    def get_hospital(self, obj):
        return {"id": str(obj.asset.hospital_id), "name": obj.asset.hospital.name}

    def get_plan(self, obj):
        if obj.plan_task_id:
            plan = obj.plan_task.plan
            return {"id": str(plan.id), "name": plan.name}
        return None

    def get_plan_task(self, obj):
        pt = obj.plan_task
        if pt is None:
            return None
        return {
            "id": str(pt.id),
            "name": pt.name,
            "trigger": pt.trigger,
            "frequency_value": pt.frequency_value,
            "frequency_unit": pt.frequency_unit,
            "fixed_schedule": pt.fixed_schedule,
        }

    def get_work_order(self, obj):
        wo = obj.work_order
        if wo is None:
            return None
        # A la cuenta de hospital no se le muestra la OT de una tarea que
        # sigue abierta: lo en curso no lo ve (decision del 2026-09-23).
        if self.context.get("for_client") and obj.is_open:
            return None
        datos = {"id": str(wo.id), "wo_code": wo.wo_code, "status": wo.status}
        if self.context.get("with_reports"):
            acta = max(wo.reports.all(), key=lambda r: r.generated_at, default=None)
            datos["report_id"] = str(acta.id) if acta else None
        return datos

    def get_is_overdue(self, obj):
        from django.utils import timezone

        return obj.is_open and obj.scheduled_date < timezone.localdate()

    def get_is_rescheduled(self, obj):
        return obj.scheduled_date != obj.calculated_date


class RescheduleCauseSerializer(serializers.ModelSerializer):
    class Meta:
        model = RescheduleCause
        fields = ["id", "name", "is_active", "sort_order"]


class TaskRescheduleSerializer(serializers.ModelSerializer):
    cause = serializers.CharField(source="cause.name", read_only=True)
    changed_by = serializers.SerializerMethodField()

    class Meta:
        model = TaskReschedule
        fields = ["id", "from_date", "to_date", "cause", "note", "changed_by", "changed_at"]

    def get_changed_by(self, obj):
        u = obj.changed_by
        if u is None:
            return None
        return {"id": str(u.id), "full_name": f"{u.first_name} {u.last_name}".strip() or u.email}


class RescheduleInputSerializer(serializers.Serializer):
    scheduled_date = serializers.DateField()
    cause_id = serializers.PrimaryKeyRelatedField(
        queryset=RescheduleCause.objects.filter(is_active=True),
        error_messages={
            "does_not_exist": "Esa causa no existe o esta desactivada.",
            "required": "La causa es obligatoria.",
            "null": "La causa es obligatoria.",
        },
    )
    note = serializers.CharField(required=False, allow_blank=True, default="")


class CancelInputSerializer(serializers.Serializer):
    note = serializers.CharField(
        error_messages={
            "blank": "Indica por que se anula la tarea.",
            "required": "Indica por que se anula la tarea.",
        },
    )


def _task_ids_field():
    return serializers.PrimaryKeyRelatedField(
        many=True, allow_empty=False,
        queryset=Task.objects.select_related("asset"),
    )


class BulkRescheduleInputSerializer(ScopedFieldsMixin, RescheduleInputSerializer):
    scoped_fields = {"task_ids": "tasks"}
    task_ids = _task_ids_field()


class BulkCancelInputSerializer(ScopedFieldsMixin, CancelInputSerializer):
    scoped_fields = {"task_ids": "tasks"}
    task_ids = _task_ids_field()
