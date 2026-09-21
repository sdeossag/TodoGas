from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.maintenance.models import Task
from apps.work_orders.models import WorkOrder

from .models import (
    ChecklistField,
    ChecklistFieldResponse,
    ChecklistResponse,
    ChecklistTemplate,
    ChecklistTemplateVersion,
)


class ChecklistFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistField
        fields = ["id", "label", "field_type", "group", "is_required", "sort_order", "options_json", "help_text"]
        read_only_fields = ["id"]


class ChecklistTemplateVersionSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source="template.name", read_only=True)
    published_by_name = serializers.SerializerMethodField()
    checklist_fields = serializers.SerializerMethodField()

    class Meta:
        model = ChecklistTemplateVersion
        fields = [
            "id", "template", "template_name", "version_number",
            "published_at", "published_by", "published_by_name",
            "is_current", "checklist_fields", "created_at",
        ]

    def get_published_by_name(self, obj):
        if not obj.published_by:
            return None
        name = f"{obj.published_by.first_name} {obj.published_by.last_name}".strip()
        return name or obj.published_by.email

    def get_checklist_fields(self, obj):
        qs = obj.fields.all().order_by("sort_order")
        return ChecklistFieldSerializer(qs, many=True).data


class ChecklistTemplateListSerializer(serializers.ModelSerializer):
    current_version_id = serializers.SerializerMethodField()
    current_version_number = serializers.SerializerMethodField()
    fields_count = serializers.SerializerMethodField()

    class Meta:
        model = ChecklistTemplate
        fields = [
            "id", "name", "description", "is_active",
            "current_version_id", "current_version_number", "fields_count",
            "created_at", "updated_at",
        ]

    def _current_version(self, obj):
        # `versions` llega con prefetch_related desde el viewset.
        for v in obj.versions.all():
            if v.is_current:
                return v
        return None

    def get_current_version_id(self, obj):
        """
        La OT se ata a una version, no a la plantilla. Sin este id el formulario
        de creacion de OT no tiene con que rellenar `checklist_version`.
        """
        v = self._current_version(obj)
        return str(v.id) if v else None

    def get_current_version_number(self, obj):
        v = self._current_version(obj)
        return v.version_number if v else None

    def get_fields_count(self, obj):
        v = self._current_version(obj)
        return len(v.fields.all()) if v else 0


class ChecklistTemplateDetailSerializer(serializers.ModelSerializer):
    versions = ChecklistTemplateVersionSerializer(many=True, read_only=True)

    class Meta:
        model = ChecklistTemplate
        fields = ["id", "name", "description", "is_active", "versions", "created_at", "updated_at"]


class ChecklistTemplateCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistTemplate
        fields = ["id", "name", "description", "is_active"]


class ChecklistVersionCreateSerializer(serializers.Serializer):
    checklist_fields = ChecklistFieldSerializer(many=True)

    def create(self, validated_data):
        fields_data = validated_data.pop("checklist_fields")
        template = self.context["template"]
        user = self.context["request"].user

        with transaction.atomic():
            template.versions.filter(is_current=True).update(is_current=False)
            last = template.versions.order_by("-version_number").first()
            next_number = (last.version_number + 1) if last else 1
            version = ChecklistTemplateVersion.objects.create(
                template=template,
                version_number=next_number,
                published_by=user,
                published_at=timezone.now(),
                is_current=True,
            )
            for field_data in fields_data:
                ChecklistField.objects.create(version=version, **field_data)

        return version


class ChecklistFieldResponseSerializer(serializers.ModelSerializer):
    field_label = serializers.CharField(source="field.label", read_only=True)
    field_type = serializers.CharField(source="field.field_type", read_only=True)
    out_of_range = serializers.SerializerMethodField()

    class Meta:
        model = ChecklistFieldResponse
        fields = ["id", "field", "field_label", "field_type", "value", "notes", "answered_at", "out_of_range"]

    def get_out_of_range(self, obj):
        return getattr(obj, "_out_of_range", False)


class ChecklistResponseSerializer(serializers.ModelSerializer):
    field_responses = ChecklistFieldResponseSerializer(many=True, read_only=True)
    completed_by_name = serializers.SerializerMethodField()
    # El checklist es de la tarea; `work_order` se sigue devolviendo porque
    # la app movil lo usa para asociar la respuesta a su OT.
    work_order = serializers.SerializerMethodField()
    version_number = serializers.IntegerField(source="version.version_number", read_only=True)
    version_fields = serializers.SerializerMethodField()

    class Meta:
        model = ChecklistResponse
        fields = [
            "id", "task", "work_order", "version", "version_number",
            "started_at", "completed_at", "completed_by", "completed_by_name",
            "field_responses", "version_fields", "created_at",
        ]

    def get_version_fields(self, obj):
        qs = obj.version.fields.all().order_by("sort_order")
        return ChecklistFieldSerializer(qs, many=True).data

    def get_work_order(self, obj):
        return str(obj.task.work_order_id) if obj.task.work_order_id else None

    def get_completed_by_name(self, obj):
        u = obj.completed_by
        if u is None:
            return None
        name = f"{u.first_name} {u.last_name}".strip()
        return name or u.email


class ChecklistResponseCreateSerializer(serializers.ModelSerializer):
    """
    Inicia el checklist de una tarea.

    Acepta la tarea, o la OT cuando la OT tiene una sola tarea: es como lo
    pide hoy la interfaz ("Iniciar checklist" sobre la OT). Con varias
    tareas hay que decir cual.
    """

    task = serializers.PrimaryKeyRelatedField(
        queryset=Task.objects.select_related("work_order"), required=False
    )
    work_order = serializers.PrimaryKeyRelatedField(
        queryset=WorkOrder.objects.all(), required=False, write_only=True
    )

    class Meta:
        model = ChecklistResponse
        fields = ["task", "work_order", "version"]

    def validate(self, data):
        tarea = data.get("task")
        work_order = data.pop("work_order", None)
        if tarea is None:
            if work_order is None:
                raise serializers.ValidationError(
                    {"task": "Indica la tarea (o la OT, si tiene una sola)."}
                )
            tareas = list(work_order.tasks.all()[:2])
            if len(tareas) != 1:
                raise serializers.ValidationError(
                    {"task": "La OT tiene varias tareas: indica de cual es el checklist."}
                )
            tarea = tareas[0]
            data["task"] = tarea
        if ChecklistResponse.objects.filter(task=tarea).exists():
            raise serializers.ValidationError(
                {"task": "Esta tarea ya tiene un checklist iniciado."}
            )
        version = data["version"]
        if tarea.checklist_version_id and tarea.checklist_version_id != version.id:
            raise serializers.ValidationError(
                {"version": "La versión no coincide con la asignada a la tarea."}
            )
        return data

    def to_representation(self, instance):
        # La respuesta del alta devolvia la OT; la app movil la sigue leyendo.
        data = super().to_representation(instance)
        data["id"] = str(instance.id)
        data["work_order"] = (
            str(instance.task.work_order_id) if instance.task.work_order_id else None
        )
        return data

    def create(self, validated_data):
        user = self.context["request"].user
        return ChecklistResponse.objects.create(
            **validated_data,
            completed_by=user,
            started_at=timezone.now(),
        )


class ChecklistFieldResponseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistFieldResponse
        fields = ["field", "value", "notes"]

    def validate_field(self, field):
        response = self.context["response"]
        if field.version_id != response.version_id:
            raise serializers.ValidationError("El campo no pertenece a la versión de este checklist.")
        return field

    def validate(self, data):
        field = data["field"]
        value = data.get("value", "")
        if field.is_required and not value.strip():
            raise serializers.ValidationError(
                {"value": f"El campo '{field.label}' es obligatorio."}
            )
        return data

    def create(self, validated_data):
        response = self.context["response"]
        field = validated_data["field"]
        obj, _ = ChecklistFieldResponse.objects.update_or_create(
            response=response,
            field=field,
            defaults={
                "value": validated_data.get("value", ""),
                "notes": validated_data.get("notes", ""),
                "answered_at": timezone.now(),
            },
        )
        return obj
