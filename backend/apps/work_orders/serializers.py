from django.utils import timezone
from rest_framework import serializers

from .models import WorkOrder, WorkOrderStatusHistory


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

    class Meta:
        model = WorkOrder
        fields = [
            "id", "wo_number", "wo_code", "title", "task_type", "status", "priority",
            "scheduled_date", "asset", "hospital", "assigned_to",
            "created_at", "is_overdue", "has_report", "report_id",
        ]

    def get_asset(self, obj):
        a = obj.asset
        return {"id": str(a.id), "code": a.code, "name": a.name}

    def get_hospital(self, obj):
        h = obj.asset.hospital
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

    class Meta:
        model = WorkOrder
        fields = WorkOrderListSerializer.Meta.fields + [
            "description", "classification_1", "classification_2",
            "progress", "progress_measure", "request_number",
            "started_at", "completed_at", "estimated_duration",
            "actual_duration", "downtime", "total_cost", "rating", "notes",
            "created_by", "maintenance_plan", "checklist_version",
            "checklist_response_id", "report_status", "status_history",
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
        'missing' si esta cerrada y no la tiene.
        """
        if obj.status != WorkOrder.Status.COMPLETED:
            return "not_applicable"
        return "ok" if obj.reports.exists() else "missing"

    def get_created_by(self, obj):
        u = obj.created_by
        return {"id": str(u.id), "full_name": f"{u.first_name} {u.last_name}".strip()}

    def get_maintenance_plan(self, obj):
        if not obj.maintenance_plan:
            return None
        mp = obj.maintenance_plan
        return {"id": str(mp.id), "name": mp.name}

    def get_checklist_response_id(self, obj):
        from django.core.exceptions import ObjectDoesNotExist
        try:
            return str(obj.checklist_response.id)
        except ObjectDoesNotExist:
            return None

    def get_checklist_version(self, obj):
        if not obj.checklist_version:
            return None
        cv = obj.checklist_version
        return {
            "id": str(cv.id),
            "version_number": cv.version_number,
            "template_name": cv.template.name,
        }


class WorkOrderCreateSerializer(serializers.ModelSerializer):
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
        from apps.assets.models import Asset
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
        validated_data["created_by"] = self.context["request"].user
        validated_data.setdefault("status", WorkOrder.Status.PENDING)
        return super().create(validated_data)


class WorkOrderUpdateSerializer(serializers.ModelSerializer):
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


class WorkOrderTechnicianUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkOrder
        fields = ["description", "notes", "progress", "actual_duration", "total_cost", "rating"]
