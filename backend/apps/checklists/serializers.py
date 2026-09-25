from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.maintenance.models import Task
from apps.work_orders.device_time import device_time
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
            "is_current", "repeatable_groups", "checklist_fields", "created_at",
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
    current_repeatable_groups = serializers.SerializerMethodField()
    fields_count = serializers.SerializerMethodField()

    class Meta:
        model = ChecklistTemplate
        fields = [
            "id", "name", "description", "is_active",
            "current_version_id", "current_version_number",
            "current_repeatable_groups", "fields_count",
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

    def get_current_repeatable_groups(self, obj):
        """El plan pide cuantas veces va cada uno ("Toma x 20")."""
        v = self._current_version(obj)
        return list(v.repeatable_groups) if v else []

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
    repeatable_groups = serializers.ListField(
        child=serializers.CharField(max_length=100), required=False, default=list
    )

    def validate(self, attrs):
        grupos = {f.get("group", "") for f in attrs["checklist_fields"]} - {""}
        sobran = [g for g in attrs["repeatable_groups"] if g not in grupos]
        if sobran:
            raise serializers.ValidationError(
                {"repeatable_groups": f"No hay campos en el grupo {', '.join(sobran)}."}
            )
        # Sin repetidos y en el orden en que aparecen los grupos.
        attrs["repeatable_groups"] = list(dict.fromkeys(attrs["repeatable_groups"]))
        return attrs

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
                repeatable_groups=validated_data.get("repeatable_groups", []),
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
        fields = [
            "id", "field", "field_label", "field_type", "repetition",
            "value", "notes", "answered_at", "out_of_range", "geo_address",
        ]

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
    repeatable_groups = serializers.ListField(source="version.repeatable_groups", read_only=True)

    class Meta:
        model = ChecklistResponse
        fields = [
            "id", "task", "work_order", "version", "version_number",
            "started_at", "completed_at", "completed_by", "completed_by_name",
            "field_responses", "version_fields", "repeatable_groups",
            "block_counts", "planned_block_counts", "created_at",
        ]
        read_only_fields = ["block_counts", "planned_block_counts"]

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
        # Desde la fase 3 el checklist se crea al meter la tarea en la OT. Si ya
        # existe se devuelve ese: una app sin actualizar, o un reintento de la
        # sincronizacion, no debe toparse con un error por pedirlo otra vez.
        existente = ChecklistResponse.objects.filter(task=validated_data["task"]).first()
        if existente is not None:
            if existente.version_id != validated_data["version"].id:
                raise serializers.ValidationError(
                    {"version": "La tarea ya tiene un checklist con otra versión."}
                )
            return existente
        return ChecklistResponse.objects.create(
            **validated_data,
            started_at=timezone.now(),
        )


class ChecklistFieldResponseCreateSerializer(serializers.ModelSerializer):
    repetition = serializers.IntegerField(required=False, default=0, min_value=0)
    # Hora en que el tecnico respondio en el telefono; la manda la cola offline.
    answered_at = serializers.DateTimeField(required=False, allow_null=True)

    class Meta:
        model = ChecklistFieldResponse
        fields = ["field", "repetition", "value", "notes", "answered_at"]

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

        # Un campo de un grupo repetible se responde por toma (1..N); uno que
        # no se repite, con 0.
        response = self.context["response"]
        repeticion = data.get("repetition", 0)
        if field.group and field.group in response.version.repeatable_groups:
            cuantas = response.count_for(field.group)
            if not 1 <= repeticion <= cuantas:
                raise serializers.ValidationError({"repetition": (
                    f"«{field.group}» va de 1 a {cuantas}; llegó {repeticion}."
                )})
        elif repeticion != 0:
            raise serializers.ValidationError(
                {"repetition": f"El campo '{field.label}' no se repite."}
            )
        return data

    def create(self, validated_data):
        response = self.context["response"]
        field = validated_data["field"]
        anterior = ChecklistFieldResponse.objects.filter(
            response=response, field=field, repetition=validated_data.get("repetition", 0),
        ).values_list("value", flat=True).first()
        obj, _ = ChecklistFieldResponse.objects.update_or_create(
            response=response,
            field=field,
            repetition=validated_data.get("repetition", 0),
            defaults={
                "value": validated_data.get("value", ""),
                "notes": validated_data.get("notes", ""),
                "answered_at": device_time(
                    validated_data.get("answered_at"), response.task.work_order
                ),
            },
        )
        # Un campo "Lectura de medidor" atado a una unidad deja la lectura en
        # el medidor del equipo y puede abrir una tarea por uso o por umbral.
        from apps.assets.meters import record_from_checklist

        request = self.context.get("request")
        record_from_checklist(obj, getattr(request, "user", None))
        # Un GPS nuevo o cambiado se convierte en direccion al confirmar: Google
        # no frena la sincronizacion del telefono.
        if field.field_type == "GPS" and obj.value != anterior:
            from django.db import transaction

            from .tasks import geocode_field_response

            if obj.geo_address:
                ChecklistFieldResponse.objects.filter(pk=obj.pk).update(geo_address="")
                obj.geo_address = ""
            transaction.on_commit(lambda: geocode_field_response.delay(str(obj.pk)))
        return obj
