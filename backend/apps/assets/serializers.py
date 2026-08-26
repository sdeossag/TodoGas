from rest_framework import serializers

from .models import Asset, AssetCustomField, AssetCustomFieldValue, AssetNode, Hospital


class HospitalSerializer(serializers.ModelSerializer):
    asset_count = serializers.SerializerMethodField()

    class Meta:
        model = Hospital
        fields = [
            "id", "name", "code", "nit", "address", "city", "department",
            "contact_name", "contact_phone", "contact_email",
            "latitude", "longitude", "is_active", "notes", "asset_count",
        ]
        read_only_fields = ["id", "asset_count"]

    def get_asset_count(self, obj):
        return obj.assets.filter(status=Asset.Status.ACTIVE).count()


class HospitalListSerializer(serializers.ModelSerializer):
    asset_count = serializers.SerializerMethodField()

    class Meta:
        model = Hospital
        fields = ["id", "name", "code", "city", "is_active", "asset_count"]

    def get_asset_count(self, obj):
        return obj.assets.filter(status=Asset.Status.ACTIVE).count()


class AssetNodeSerializer(serializers.ModelSerializer):
    hospital = serializers.SerializerMethodField()
    parent = serializers.SerializerMethodField()
    children_count = serializers.SerializerMethodField()

    class Meta:
        model = AssetNode
        fields = [
            "id", "hospital", "parent", "name", "node_type", "code",
            "path", "sort_order", "is_active", "children_count",
        ]

    def get_hospital(self, obj):
        return {"id": str(obj.hospital_id), "name": obj.hospital.name}

    def get_parent(self, obj):
        if obj.parent_id:
            return {"id": str(obj.parent_id), "name": obj.parent.name}
        return None

    def get_children_count(self, obj):
        return obj.children.count()


class AssetNodeTreeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = AssetNode
        fields = ["id", "name", "node_type", "code", "path", "sort_order", "is_active", "children"]

    def get_children(self, obj):
        qs = obj.children.filter(is_active=True).order_by("sort_order", "name")
        return AssetNodeTreeSerializer(qs, many=True).data


class AssetCustomFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetCustomField
        fields = [
            "id", "asset_type_name", "field_name", "field_type",
            "is_required", "options", "sort_order",
        ]


class AssetCustomFieldValueSerializer(serializers.ModelSerializer):
    field = serializers.SerializerMethodField()

    class Meta:
        model = AssetCustomFieldValue
        fields = ["id", "field", "value"]

    def get_field(self, obj):
        return {"id": str(obj.field_id), "field_name": obj.field.field_name}


class AssetSerializer(serializers.ModelSerializer):
    hospital = serializers.SerializerMethodField()
    node = serializers.SerializerMethodField()
    custom_field_values = AssetCustomFieldValueSerializer(many=True, read_only=True)

    class Meta:
        model = Asset
        fields = [
            "id", "hospital", "node", "name", "code", "manufacturer", "model",
            "serial_number", "equipment_location", "barcode", "priority",
            "asset_type", "classification_1", "classification_2", "supplier",
            "purchase_date", "avg_daily_usage_hours", "status", "notes",
            "qr_code", "photo_url", "installation_date", "warranty_expiry",
            "created_at", "updated_at", "custom_field_values",
        ]
        read_only_fields = ["id", "qr_code", "created_at", "updated_at"]

    def get_hospital(self, obj):
        return {"id": str(obj.hospital_id), "name": obj.hospital.name}

    def get_node(self, obj):
        if obj.node_id:
            return {"id": str(obj.node_id), "name": obj.node.name, "path": obj.node.path}
        return None


class AssetListSerializer(serializers.ModelSerializer):
    hospital = serializers.SerializerMethodField()
    node = serializers.SerializerMethodField()
    last_maintenance_date = serializers.SerializerMethodField()
    next_maintenance_date = serializers.SerializerMethodField()
    maintenance_status = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = [
            "id", "name", "code", "hospital", "node",
            "asset_type", "status", "priority",
            "last_maintenance_date", "next_maintenance_date", "maintenance_status",
        ]

    def get_hospital(self, obj):
        return {"id": str(obj.hospital_id), "name": obj.hospital.name}

    def get_node(self, obj):
        if obj.node_id:
            return {"id": str(obj.node_id), "path": obj.node.path}
        return None

    def get_last_maintenance_date(self, obj):
        from apps.work_orders.models import WorkOrder
        last = (
            obj.work_orders
            .filter(status=WorkOrder.Status.COMPLETED)
            .order_by("-completed_at")
            .values_list("completed_at", flat=True)
            .first()
        )
        return last.date().isoformat() if last else None

    def get_next_maintenance_date(self, obj):
        next_date = (
            obj.maintenance_plans
            .filter(is_active=True, next_due_date__isnull=False)
            .order_by("next_due_date")
            .values_list("next_due_date", flat=True)
            .first()
        )
        return str(next_date) if next_date else None

    def get_maintenance_status(self, obj):
        from datetime import date
        today = date.today()
        next_date = (
            obj.maintenance_plans
            .filter(is_active=True, next_due_date__isnull=False)
            .order_by("next_due_date")
            .values_list("next_due_date", flat=True)
            .first()
        )
        if next_date is None:
            return "no_plan"
        delta = (next_date - today).days
        if delta < 0:
            return "overdue"
        if delta <= 15:
            return "due_soon"
        return "on_time"


class AssetCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = [
            "id", "hospital", "node", "name", "code", "manufacturer", "model",
            "serial_number", "equipment_location", "barcode", "priority",
            "asset_type", "classification_1", "classification_2", "supplier",
            "purchase_date", "avg_daily_usage_hours", "status", "notes",
            "photo_url", "installation_date", "warranty_expiry",
        ]
        read_only_fields = ["id"]

    def validate_code(self, value):
        qs = Asset.objects.filter(code=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe un activo con este código.")
        return value

    def validate(self, attrs):
        node = attrs.get("node", getattr(self.instance, "node", None))
        hospital = attrs.get("hospital", getattr(self.instance, "hospital", None))
        if node and hospital and node.hospital_id != hospital.pk:
            raise serializers.ValidationError(
                {"node": "El nodo no pertenece al mismo hospital que el activo."}
            )
        return attrs
