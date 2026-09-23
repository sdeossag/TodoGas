from django.utils import timezone
from rest_framework import serializers

from apps.assets.models import Asset, AssetNode
from apps.checklists.models import ChecklistTemplateVersion
from apps.maintenance.models import Task
from apps.maintenance.task_types import TaskTypeField
from apps.reports.failures import has_report_failure
from apps.users.models import User
from apps.users.scope import ScopedFieldsMixin

from .models import WorkOrder, WorkOrderStatusHistory

# La OT agrupa tareas: no tiene activo, version de checklist ni plan propios.
# Cada tarea lleva los suyos, y la OT solo el hospital y la ubicacion de la
# visita. Los campos de compatibilidad que tomaban lo de la primera tarea se
# retiraron en la fase 4.


def _tareas_vigentes(work_order):
    """
    Las tareas que cuentan como trabajo de la OT.

    Una tarea anulada sigue en la OT por historial, pero no suma activos: la
    tarjeta diria "3 activos" cuando el tecnico solo va a intervenir dos. En
    una OT anulada no queda ninguna vigente y se muestran todas.
    """
    tareas = list(work_order.tasks.all())
    vigentes = [t for t in tareas if t.status != Task.Status.CANCELLED]
    return vigentes or tareas


class WorkOrderStatusHistorySerializer(serializers.ModelSerializer):
    changed_by = serializers.SerializerMethodField()

    class Meta:
        model = WorkOrderStatusHistory
        fields = ["id", "from_status", "to_status", "changed_by", "comment", "changed_at"]

    def get_changed_by(self, obj):
        u = obj.changed_by
        return {"id": str(u.id), "full_name": f"{u.first_name} {u.last_name}".strip()}


class WorkOrderListSerializer(serializers.ModelSerializer):
    assets = serializers.SerializerMethodField()
    hospital = serializers.SerializerMethodField()
    assigned_to = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    has_report = serializers.SerializerMethodField()
    report_id = serializers.SerializerMethodField()
    # Numero legible OT-2026-00001 (RF-OT-02). Se anade sin quitar wo_number:
    # el APK publicado y el esquema SQLite offline siguen leyendo el entero.
    wo_code = serializers.CharField(read_only=True)
    assets_count = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()

    class Meta:
        model = WorkOrder
        fields = [
            "id", "wo_number", "wo_code", "title", "task_type", "status", "priority",
            "scheduled_date", "assets", "assets_count", "hospital", "location", "assigned_to",
            "created_at", "is_overdue", "has_report", "report_id",
        ]

    def get_assets(self, obj):
        """Los activos de la visita, sin repetir y en el orden de las tareas."""
        activos = {}
        for t in _tareas_vigentes(obj):
            a = t.asset
            activos.setdefault(a.id, {"id": str(a.id), "code": a.code, "name": a.name})
        return list(activos.values())

    def get_assets_count(self, obj):
        return len({t.asset_id for t in _tareas_vigentes(obj)})

    def get_hospital(self, obj):
        h = obj.hospital
        return {"id": str(h.id), "name": h.name}

    def get_location(self, obj):
        if not obj.location_id:
            return None
        return {"id": str(obj.location_id), "name": obj.location.name, "path": obj.location.path}

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
    status_history = WorkOrderStatusHistorySerializer(many=True, read_only=True)
    report_status = serializers.SerializerMethodField()
    tasks = serializers.SerializerMethodField()
    # Para que la app sepa sin red si ya hay foto y firma en el servidor: pasar
    # a revision las exige, y sin red no puede preguntarlo.
    photos_count = serializers.SerializerMethodField()
    signatures_count = serializers.SerializerMethodField()

    class Meta:
        model = WorkOrder
        fields = WorkOrderListSerializer.Meta.fields + [
            "photos_count", "signatures_count",
            "description", "classification_1", "classification_2",
            "progress", "progress_measure", "request_number",
            "started_at", "completed_at", "estimated_duration",
            "actual_duration", "downtime", "total_cost", "rating", "notes",
            "created_by", "report_status", "status_history",
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

    def get_photos_count(self, obj):
        return len(obj.photos.all())

    def get_signatures_count(self, obj):
        return len(obj.signatures.all())

    def get_created_by(self, obj):
        u = obj.created_by
        return {"id": str(u.id), "full_name": f"{u.first_name} {u.last_name}".strip()}

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
                "checklist": _checklist_progress(t),
                "description": t.description,
                "estimated_duration": serializers.DurationField().to_representation(t.estimated_duration)
                if t.estimated_duration else None,
                "calculated_date": t.calculated_date,
                "scheduled_date": t.scheduled_date,
                "completed_at": t.completed_at,
            }
            for t in obj.tasks.all()
        ]


def _checklist_progress(tarea):
    """
    Avance del checklist de la tarea, para la lista de tareas de la OT: cuantos
    campos van, cuantos obligatorios faltan y si ya se finalizo.
    """
    from django.core.exceptions import ObjectDoesNotExist

    try:
        respuesta = tarea.checklist_response
    except ObjectDoesNotExist:
        return None
    # Un grupo repetible cuenta una vez por toma: 20 tomas de 9 preguntas son
    # 180 respuestas, no 9.
    esperadas = respuesta.slots(list(respuesta.version.fields.all()))
    respondidas = {(fr.field_id, fr.repetition) for fr in respuesta.field_responses.all()}
    return {
        "response_id": str(respuesta.id),
        "answered": sum(1 for f, n in esperadas if (f.id, n) in respondidas),
        "total": len(esperadas),
        "required_missing": sum(
            1 for f, n in esperadas if f.is_required and (f.id, n) not in respondidas
        ),
        "completed_at": respuesta.completed_at,
        # El tecnico encontro otra cantidad que la del plan: el administrador
        # lo ve en la OT para corregir el plan del activo.
        "block_changes": [
            {"group": g, "planned": planeadas, "count": respuesta.count_for(g)}
            for g, planeadas in respuesta.planned_block_counts.items()
            if respuesta.count_for(g) != planeadas
        ],
    }


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


class ManualTaskSerializer(ScopedFieldsMixin, serializers.Serializer):
    """Un activo de la visita, con su checklist opcional."""

    scoped_fields = {"asset": "assets"}

    asset = serializers.PrimaryKeyRelatedField(
        queryset=Asset.objects.select_related("hospital")
    )
    checklist_version = serializers.PrimaryKeyRelatedField(
        queryset=ChecklistTemplateVersion.objects.all(),
        required=False, allow_null=True,
    )

    def validate_asset(self, value):
        if value.status != Asset.Status.ACTIVE:
            raise serializers.ValidationError(
                f"El activo '{value.code}' no está ACTIVE (status actual: {value.status})."
            )
        return value


class WorkOrderCreateSerializer(serializers.ModelSerializer):
    """
    Alta manual (correctivos). Una OT es una visita a un hospital y lleva una
    tarea por activo, cada una con su checklist.
    """

    tasks = ManualTaskSerializer(many=True, write_only=True, allow_empty=False)
    # Cualquier tipo activo del catalogo, preventivos incluidos (decision del 2026-09-23).
    task_type = TaskTypeField()
    location = serializers.PrimaryKeyRelatedField(
        queryset=AssetNode.objects.select_related("hospital"),
        required=False, allow_null=True,
    )

    class Meta:
        model = WorkOrder
        fields = [
            "tasks", "location", "task_type", "title", "description",
            "classification_1", "classification_2",
            "priority", "scheduled_date", "estimated_duration",
            "assigned_to", "notes", "request_number",
        ]


    def validate_assigned_to(self, value):
        if value is None:
            return value
        if value.role != "TEC":
            raise serializers.ValidationError(
                f"El usuario asignado debe tener rol TEC (rol actual: {value.role})."
            )
        return value

    def validate(self, attrs):
        entradas = attrs["tasks"]
        activos = [e["asset"] for e in entradas]

        repetidos = sorted({a.code for a in activos if activos.count(a) > 1})
        if repetidos:
            raise serializers.ValidationError(
                {"tasks": f"El activo {', '.join(repetidos)} está repetido en la OT."}
            )

        # Decision D4: una OT es una visita a un hospital.
        hospitales = {a.hospital_id for a in activos}
        if len(hospitales) > 1:
            raise serializers.ValidationError(
                {"tasks": "Todos los activos de una OT deben ser del mismo hospital."}
            )

        ubicacion = attrs.get("location")
        if ubicacion is not None and ubicacion.hospital_id != next(iter(hospitales)):
            raise serializers.ValidationError(
                {"location": "La ubicación es de otro hospital."}
            )
        return attrs

    def create(self, validated_data):
        from apps.maintenance.services import create_manual_work_order

        entradas = [
            (e["asset"], e.get("checklist_version")) for e in validated_data.pop("tasks")
        ]
        ubicacion = validated_data.pop("location", None)
        validated_data.setdefault("status", WorkOrder.Status.PENDING)
        return create_manual_work_order(
            entradas, self.context["request"].user, location=ubicacion, **validated_data,
        )


class TaskIdsSerializer(ScopedFieldsMixin, serializers.Serializer):
    scoped_fields = {"task_ids": "tasks"}
    task_ids = serializers.PrimaryKeyRelatedField(
        many=True, allow_empty=False,
        queryset=Task.objects.select_related("asset", "plan_task__checklist_template"),
        error_messages={"does_not_exist": "La tarea {pk_value} no existe."},
    )


class WorkOrderFromTasksSerializer(ScopedFieldsMixin, serializers.Serializer):
    """
    OT a partir de tareas pendientes: el planificador las selecciona y arma la
    visita, como la columna de pendientes de Fracttal y su "+ Nueva OT". Todas
    del mismo hospital (D4).
    """

    scoped_fields = {"task_ids": "tasks"}

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
    """Datos de la visita. El checklist es de cada tarea: ver TaskChecklistSerializer."""

    class Meta:
        model = WorkOrder
        fields = [
            "title", "description", "priority", "scheduled_date",
            "estimated_duration", "assigned_to",
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


class TaskChecklistSerializer(serializers.Serializer):
    """
    Cambiar el checklist de una tarea de la OT. El checklist es de la tarea,
    no de la OT: con varios activos cada uno lleva el suyo.
    """

    task = serializers.PrimaryKeyRelatedField(queryset=Task.objects.all())
    checklist_version = serializers.PrimaryKeyRelatedField(
        queryset=ChecklistTemplateVersion.objects.all(), allow_null=True
    )

    def validate(self, attrs):
        from apps.maintenance.services import _answered

        tarea = attrs["task"]
        if tarea.work_order_id != self.context["work_order"].id:
            raise serializers.ValidationError({"task": "La tarea no es de esta OT."})
        if _answered(tarea):
            raise serializers.ValidationError(
                {"checklist_version": (
                    "El checklist de esta tarea ya se empezó a diligenciar; no se "
                    "puede cambiar."
                )}
            )
        return attrs


class WorkOrderTechnicianUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkOrder
        fields = ["description", "notes", "progress", "actual_duration", "total_cost", "rating"]
