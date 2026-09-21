from django.utils import timezone
from rest_framework import serializers

from apps.assets.models import Asset, AssetNode
from apps.checklists.models import ChecklistTemplateVersion
from apps.maintenance.models import Task
from apps.reports.failures import has_report_failure
from apps.users.models import User

from .models import WorkOrder, WorkOrderStatusHistory

# Fase 1 del modelo de tareas: la OT agrupa tareas y ya no tiene activo,
# version de checklist ni plan propios. Mientras las pantallas y la app
# movil se reescriben para varias tareas (fases 3 y 4), la API sigue
# devolviendo esos campos tomados de la primera tarea, y el alta sigue
# aceptando un activo y una version. Son campos del serializer, no columnas.


class WorkOrderStatusHistorySerializer(serializers.ModelSerializer):
    changed_by = serializers.SerializerMethodField()

    class Meta:
        model = WorkOrderStatusHistory
        fields = ["id", "from_status", "to_status", "changed_by", "comment", "changed_at"]

    def get_changed_by(self, obj):
        u = obj.changed_by
        return {"id": str(u.id), "full_name": f"{u.first_name} {u.last_name}".strip()}


class WorkOrderListSerializer(serializers.ModelSerializer):
    asset = serializers.SerializerMethodField()
    hospital = serializers.SerializerMethodField()
    assigned_to = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    has_report = serializers.SerializerMethodField()
    report_id = serializers.SerializerMethodField()
    # Numero legible OT-2026-00001 (RF-OT-02). Se anade sin quitar wo_number:
    # el APK publicado y el esquema SQLite offline siguen leyendo el entero.
    wo_code = serializers.CharField(read_only=True)
    assets_count = serializers.SerializerMethodField()

    class Meta:
        model = WorkOrder
        fields = [
            "id", "wo_number", "wo_code", "title", "task_type", "status", "priority",
            "scheduled_date", "asset", "assets_count", "hospital", "assigned_to",
            "created_at", "is_overdue", "has_report", "report_id",
        ]

    def get_asset(self, obj):
        tarea = obj.primary_task
        if tarea is None:
            return None
        a = tarea.asset
        return {"id": str(a.id), "code": a.code, "name": a.name}

    def get_assets_count(self, obj):
        # Una OT armada desde pendientes lleva varios activos; `asset` es solo
        # el primero (compatibilidad hasta la fase 4).
        return len({t.asset_id for t in obj.tasks.all()})

    def get_hospital(self, obj):
        h = obj.hospital
        return {"id": str(h.id), "name": h.name}

    def get_assigned_to(self, obj):
        if not obj.assigned_to:
            return None
        u = obj.assigned_to
        return {"id": str(u.id), "full_name": f"{u.first_name} {u.last_name}".strip()}

    def get_is_overdue(self, obj):
        if obj.status in (WorkOrder.Status.COMPLETED, WorkOrder.Status.CANCELLED):
            return False
        return obj.scheduled_date < timezone.now().date()

    def get_has_report(self, obj):
        if obj.status == WorkOrder.Status.COMPLETED:
            return obj.reports.exists()
        return None

    def get_report_id(self, obj):
        """
        Id del PDF mas reciente. El portal del cliente lo necesita para
        descargar sin tener que abrir el detalle de la OT.
        """
        if obj.status != WorkOrder.Status.COMPLETED:
            return None
        # `reports` viene con prefetch_related en el viewset: ordenar en Python
        # evita una consulta extra por fila.
        reports = sorted(
            obj.reports.all(), key=lambda r: r.generated_at, reverse=True
        )
        return str(reports[0].id) if reports else None


class WorkOrderDetailSerializer(WorkOrderListSerializer):
    created_by = serializers.SerializerMethodField()
    maintenance_plan = serializers.SerializerMethodField()
    checklist_version = serializers.SerializerMethodField()
    status_history = WorkOrderStatusHistorySerializer(many=True, read_only=True)
    checklist_response_id = serializers.SerializerMethodField()
    report_status = serializers.SerializerMethodField()
    tasks = serializers.SerializerMethodField()

    class Meta:
        model = WorkOrder
        fields = WorkOrderListSerializer.Meta.fields + [
            "description", "classification_1", "classification_2",
            "progress", "progress_measure", "request_number",
            "started_at", "completed_at", "estimated_duration",
            "actual_duration", "downtime", "total_cost", "rating", "notes",
            "created_by", "maintenance_plan", "checklist_version",
            "checklist_response_id", "report_status", "status_history",
            "tasks",
            "synced_at", "offline_uuid",
        ]

    def get_report_status(self, obj):
        """
        Estado del acta de una OT cerrada.

        La generacion del PDF corre en Celery y no bloquea el cierre de la OT.
        Si falla y agota los reintentos, la OT queda COMPLETED sin acta: antes
        eso solo constaba en los logs del servidor y en la interfaz aparecia
        como una pestana de reportes vacia, indistinguible de "todavia se esta
        generando". Este campo permite avisar y ofrecer el reintento
        (POST .../regenerate-report/).

        'not_applicable' mientras la OT no este cerrada, 'ok' si ya tiene acta,
        'failed' si consta un fallo de generacion, y 'missing' si esta cerrada,
        no tiene acta y tampoco hay fallo registrado: sigue generandose.

        Distinguir 'failed' de 'missing' es lo que permite a la interfaz dejar
        de sondear en vacio. Antes las dos situaciones eran el mismo estado y la
        pestaña de reportes giraba dos minutos antes de rendirse.
        """
        if obj.status != WorkOrder.Status.COMPLETED:
            return "not_applicable"
        if obj.reports.exists():
            return "ok"
        if has_report_failure(obj.id):
            return "failed"
        return "missing"

    def get_created_by(self, obj):
        u = obj.created_by
        return {"id": str(u.id), "full_name": f"{u.first_name} {u.last_name}".strip()}

    def get_maintenance_plan(self, obj):
        tarea = obj.primary_task
        if tarea is None or tarea.plan_task is None:
            return None
        mp = tarea.plan_task.plan
        return {"id": str(mp.id), "name": mp.name}

    def get_checklist_response_id(self, obj):
        return _response_id(obj.primary_task)

    def get_checklist_version(self, obj):
        return _version_dict(obj.primary_task)

    def get_tasks(self, obj):
        return [
            {
                "id": str(t.id),
                "status": t.status,
                "title": t.title,
                "task_type": t.task_type,
                "asset": {
                    "id": str(t.asset_id),
                    "code": t.asset.code,
                    "name": t.asset.name,
                    "location": t.asset.node.path if t.asset.node_id else None,
                },
                "plan": (
                    {"id": str(t.plan_task.plan_id), "name": t.plan_task.plan.name}
                    if t.plan_task_id else None
                ),
                "checklist_version": _version_dict(t),
                "checklist_response_id": _response_id(t),
                "calculated_date": t.calculated_date,
                "scheduled_date": t.scheduled_date,
                "completed_at": t.completed_at,
            }
            for t in obj.tasks.all()
        ]


def _response_id(tarea):
    if tarea is None:
        return None
    from django.core.exceptions import ObjectDoesNotExist
    try:
        return str(tarea.checklist_response.id)
    except ObjectDoesNotExist:
        return None


def _version_dict(tarea):
    if tarea is None or tarea.checklist_version is None:
        return None
    cv = tarea.checklist_version
    return {
        "id": str(cv.id),
        "version_number": cv.version_number,
        "template_name": cv.template.name,
    }


class WorkOrderCreateSerializer(serializers.ModelSerializer):
    # Compatibilidad: el alta de hoy es de un activo con un checklist
    # opcional. Se convierte en una OT con una tarea manual.
    asset = serializers.PrimaryKeyRelatedField(
        queryset=Asset.objects.select_related("hospital"), write_only=True
    )
    checklist_version = serializers.PrimaryKeyRelatedField(
        queryset=ChecklistTemplateVersion.objects.all(),
        required=False, allow_null=True, write_only=True,
    )

    class Meta:
        model = WorkOrder
        fields = [
            "asset", "task_type", "title", "description",
            "classification_1", "classification_2",
            "priority", "scheduled_date", "estimated_duration",
            "assigned_to", "checklist_version", "notes", "request_number",
        ]

    def validate_task_type(self, value):
        allowed = {WorkOrder.TaskType.CORRECTIVE, WorkOrder.TaskType.VERIFICATION}
        if value not in allowed:
            raise serializers.ValidationError(
                "Solo se pueden crear OTs de tipo CORRECTIVE o VERIFICATION. "
                "Las OTs PREVENTIVE las genera el sistema automáticamente."
            )
        return value

    def validate_asset(self, value):
        if value.status != Asset.Status.ACTIVE:
            raise serializers.ValidationError(
                f"El activo '{value.code}' no está ACTIVE (status actual: {value.status})."
            )
        return value

    def validate_assigned_to(self, value):
        if value is None:
            return value
        if value.role != "TEC":
            raise serializers.ValidationError(
                f"El usuario asignado debe tener rol TEC (rol actual: {value.role})."
            )
        return value

    def create(self, validated_data):
        from apps.maintenance.services import create_manual_work_order

        asset = validated_data.pop("asset")
        version = validated_data.pop("checklist_version", None)
        validated_data.setdefault("status", WorkOrder.Status.PENDING)
        return create_manual_work_order(
            asset, self.context["request"].user,
            checklist_version=version, **validated_data,
        )


class WorkOrderFromTasksSerializer(serializers.Serializer):
    """
    OT a partir de tareas pendientes: el planificador las selecciona y arma la
    visita, como la columna de pendientes de Fracttal y su "+ Nueva OT". Todas
    del mismo hospital (D4).
    """

    task_ids = serializers.PrimaryKeyRelatedField(
        many=True, allow_empty=False,
        queryset=Task.objects.select_related("asset__hospital", "plan_task__checklist_template"),
    )
    title = serializers.CharField(max_length=500, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    priority = serializers.ChoiceField(choices=WorkOrder.Priority.choices, required=False)
    scheduled_date = serializers.DateField(required=False)
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True),
        required=False, allow_null=True,
    )
    location = serializers.PrimaryKeyRelatedField(
        queryset=AssetNode.objects.all(), required=False, allow_null=True,
    )

    def validate_assigned_to(self, value):
        if value is not None and value.role != "TEC":
            raise serializers.ValidationError(
                f"El usuario asignado debe tener rol TEC (rol actual: {value.role})."
            )
        return value

    def validate(self, attrs):
        tareas = attrs["task_ids"]
        if len({t.id for t in tareas}) != len(tareas):
            raise serializers.ValidationError({"task_ids": "Hay tareas repetidas."})
        no_pendientes = [t for t in tareas if t.status != Task.Status.PENDING]
        if no_pendientes:
            raise serializers.ValidationError({"task_ids": (
                "Solo se agrupan tareas pendientes. No lo estan: "
                + ", ".join(f"{t.asset.code} ({t.get_status_display()})" for t in no_pendientes[:5])
            )})
        hospitales = {t.asset.hospital for t in tareas}
        if len(hospitales) > 1:
            raise serializers.ValidationError({"task_ids": (
                "Una OT es de un solo hospital y estas tareas son de "
                + " y ".join(sorted(h.name for h in hospitales)) + "."
            )})
        ubicacion = attrs.get("location")
        hospital = hospitales.pop()
        if ubicacion is not None and ubicacion.hospital_id != hospital.id:
            raise serializers.ValidationError(
                {"location": f"La ubicacion no es de {hospital.name}."}
            )
        return attrs

    def create(self, validated_data):
        from apps.maintenance.services import create_work_order_for_tasks

        tareas = validated_data.pop("task_ids")
        ot, avisos = create_work_order_for_tasks(
            tareas,
            self.context["request"].user,
            title=validated_data.get("title") or None,
            description=validated_data.get("description", ""),
            notes=validated_data.get("notes", ""),
            priority=validated_data.get("priority"),
            scheduled_date=validated_data.get("scheduled_date"),
            assigned_to=validated_data.get("assigned_to"),
            location=validated_data.get("location"),
        )
        self.warnings = avisos
        return ot


class WorkOrderUpdateSerializer(serializers.ModelSerializer):
    # Compatibilidad: cambia el checklist de la primera tarea, mientras no
    # se haya empezado a diligenciar.
    checklist_version = serializers.PrimaryKeyRelatedField(
        queryset=ChecklistTemplateVersion.objects.all(),
        required=False, allow_null=True, write_only=True,
    )

    class Meta:
        model = WorkOrder
        fields = [
            "title", "description", "priority", "scheduled_date",
            "estimated_duration", "assigned_to", "checklist_version",
            "notes", "classification_1", "classification_2",
        ]

    def validate_assigned_to(self, value):
        if value is None:
            return value
        if value.role != "TEC":
            raise serializers.ValidationError(
                f"El usuario asignado debe tener rol TEC (rol actual: {value.role})."
            )
        return value

    def validate_checklist_version(self, value):
        tarea = self.instance.primary_task if self.instance else None
        if tarea is not None and _response_id(tarea) is not None:
            raise serializers.ValidationError(
                "El checklist de esta OT ya se empezo a diligenciar; no se "
                "puede cambiar."
            )
        return value

    def update(self, instance, validated_data):
        sentinel = object()
        version = validated_data.pop("checklist_version", sentinel)
        instance = super().update(instance, validated_data)
        tarea = instance.primary_task
        if version is not sentinel and tarea is not None:
            tarea.checklist_version = version
            tarea.save(update_fields=["checklist_version", "updated_at"])
        return instance


class WorkOrderTechnicianUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkOrder
        fields = ["description", "notes", "progress", "actual_duration", "total_cost", "rating"]
