from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

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
    current_version_number = serializers.SerializerMethodField()
    fields_count = serializers.SerializerMethodField()

    class Meta:
        model = ChecklistTemplate
        fields = [
            "id", "name", "description", "is_active",
            "current_version_number", "fields_count",
            "created_at", "updated_at",
        ]

    def get_current_version_number(self, obj):
        v = obj.versions.filter(is_current=True).first()
        return v.version_number if v else None

    def get_fields_count(self, obj):
        v = obj.versions.filter(is_current=True).first()
        return v.fields.count() if v else 0


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
    version_number = serializers.IntegerField(source="version.version_number", read_only=True)
    version_fields = serializers.SerializerMethodField()

    class Meta:
        model = ChecklistResponse
        fields = [
            "id", "work_order", "version", "version_number",
            "started_at", "completed_at", "completed_by", "completed_by_name",
            "field_responses", "version_fields", "created_at",
        ]

    def get_version_fields(self, obj):
        qs = obj.version.fields.all().order_by("sort_order")
        return ChecklistFieldSerializer(qs, many=True).data

    def get_completed_by_name(self, obj):
        u = obj.completed_by
        name = f"{u.first_name} {u.last_name}".strip()
        return name or u.email


class ChecklistResponseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistResponse
        fields = ["work_order", "version"]

    def validate_work_order(self, work_order):
        if ChecklistResponse.objects.filter(work_order=work_order).exists():
            raise serializers.ValidationError("Esta OT ya tiene un checklist iniciado.")
        return work_order

    def validate(self, data):
        work_order = data["work_order"]
        version = data["version"]
        if work_order.checklist_version_id and work_order.checklist_version_id != version.id:
            raise serializers.ValidationError(
                {"version": "La versión no coincide con la asignada a la OT."}
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
