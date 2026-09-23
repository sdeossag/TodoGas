from rest_framework import serializers

from apps.users import scope
from apps.users.scope import ScopedFieldsMixin

from .models import Asset, AssetCustomField, AssetCustomFieldValue, AssetNode, Hospital


class _ContractStatusMixin:
    """"Sin contrato vigente" se avisa en la ficha, la lista y al armar una OT."""

    def get_contract_status(self, obj):
        from .contracts import estado_del_hospital
        return estado_del_hospital(obj)


class HospitalSerializer(_ContractStatusMixin, serializers.ModelSerializer):
    asset_count = serializers.SerializerMethodField()
    contract_status = serializers.SerializerMethodField()

    class Meta:
        model = Hospital
        fields = [
            "id", "name", "code", "nit", "address", "city", "department",
            "contact_name", "contact_phone", "contact_email",
            "latitude", "longitude", "is_active", "notes", "asset_count",
            "contract_status",
        ]
        read_only_fields = ["id", "asset_count"]

    def get_asset_count(self, obj):
        return obj.assets.filter(status=Asset.Status.ACTIVE).count()


class HospitalListSerializer(_ContractStatusMixin, serializers.ModelSerializer):
    asset_count = serializers.SerializerMethodField()
    contract_status = serializers.SerializerMethodField()

    class Meta:
        model = Hospital
        fields = ["id", "name", "code", "city", "is_active", "asset_count", "contract_status"]

    def get_asset_count(self, obj):
        return obj.assets.filter(status=Asset.Status.ACTIVE).count()


class AssetNodeSerializer(serializers.ModelSerializer):
    hospital = serializers.SerializerMethodField()
    parent = serializers.SerializerMethodField()
    children_count = serializers.SerializerMethodField()
    asset_count = serializers.SerializerMethodField()

    class Meta:
        model = AssetNode
        fields = [
            "id", "hospital", "parent", "name", "node_type", "code",
            "path", "sort_order", "is_active", "children_count", "asset_count",
        ]

    def get_hospital(self, obj):
        return {"id": str(obj.hospital_id), "name": obj.hospital.name}

    def get_parent(self, obj):
        if obj.parent_id:
            return {"id": str(obj.parent_id), "name": obj.parent.name}
        return None

    # Los dos conteos llegan anotados desde AssetNodeViewSet.get_queryset, en la
    # misma consulta del listado. El respaldo con .count() queda para la
    # respuesta de un create, cuyo nodo recien guardado no trae anotaciones.
    # Ambos son directos (no incluyen descendientes) y cuentan cualquier
    # estado: es exactamente lo que bloquea el borrado por on_delete=PROTECT.

    def get_children_count(self, obj):
        anotado = getattr(obj, "children_total", None)
        return anotado if anotado is not None else obj.children.count()

    def get_asset_count(self, obj):
        anotado = getattr(obj, "asset_total", None)
        return anotado if anotado is not None else obj.assets.count()


class AssetNodeCreateUpdateSerializer(ScopedFieldsMixin, serializers.ModelSerializer):
    """Serializer de escritura para las ubicaciones.

    AssetNodeSerializer expone `hospital` y `parent` como SerializerMethodField,
    o sea de solo lectura. El viewset lo usaba tambien para crear, asi que el
    POST descartaba esos dos campos en silencio y el INSERT se estrellaba contra
    el NOT NULL de hospital_id: un HTTP 500 en la cara del cliente en vez de una
    validacion. Crear ubicaciones era imposible por API.

    `path` no se acepta: lo materializa AssetNode.save() a partir del padre.
    """

    # Un usuario limitado a una parte del arbol solo crea dentro de ella.
    scoped_fields = {"hospital": "hospitals", "parent": "nodes"}

    class Meta:
        model = AssetNode
        fields = [
            "id", "hospital", "parent", "name", "node_type", "code",
            "sort_order", "is_active",
        ]
        read_only_fields = ["id"]
        # Sin el UniqueTogetherValidator que DRF deriva de la restriccion unica:
        # respondia antes que validate() con "Los campos hospital, parent, name
        # deben formar un conjunto unico", y en la raiz ni siquiera comprobaba
        # nada porque parent es NULL. validate() cubre ambos casos y dice que
        # campo corregir.
        validators = []

    def _hospital_de(self, attrs, campo):
        if campo in attrs:
            return attrs[campo]
        return getattr(self.instance, campo, None)

    def validate(self, attrs):
        hospital = self._hospital_de(attrs, "hospital")
        parent = self._hospital_de(attrs, "parent")
        if parent is None and scope.needs_node(self.context):
            raise serializers.ValidationError(
                {"parent": "Tu usuario está limitado a una parte del hospital: elige dónde va."}
            )

        if parent is not None:
            if hospital and parent.hospital_id != hospital.pk:
                raise serializers.ValidationError(
                    {"parent": "La ubicación superior pertenece a otro hospital."}
                )
            # Un ciclo dejaria path() en recursion infinita y el arbol
            # inalcanzable. Solo puede darse al reasignar el padre de un nodo
            # existente.
            if self.instance is not None:
                actual = parent
                while actual is not None:
                    if actual.pk == self.instance.pk:
                        raise serializers.ValidationError(
                            {"parent": "Una ubicación no puede quedar dentro de sí "
                                       "misma ni de una de sus sububicaciones."}
                        )
                    actual = actual.parent

        nombre = attrs.get("name", getattr(self.instance, "name", None))
        if hospital and nombre:
            hermanos = AssetNode.objects.filter(
                hospital=hospital, parent=parent, name=nombre
            )
            if self.instance is not None:
                hermanos = hermanos.exclude(pk=self.instance.pk)
            if hermanos.exists():
                # Sin esto la restriccion unica (hospital, parent, name) saltaba
                # como IntegrityError, otro 500.
                raise serializers.ValidationError(
                    {"name": "Ya existe una ubicación con ese nombre en el mismo "
                             "nivel."}
                )

        return attrs


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


class AssetMaintenanceFieldsMixin:
    """Estado de mantenimiento derivado, compartido por el listado y la ficha.

    Lee las anotaciones _last_maint y _next_due que pone AssetViewSet.get_queryset
    (subconsultas, no una query por activo). El fallback per-fila solo actua si el
    serializer se usa sobre un queryset sin anotar.

    Los tres SerializerMethodField se declaran en cada serializer y no aqui: DRF
    solo recoge campos declarados de bases que ya son serializers, asi que en un
    mixin plano se perderian en silencio.
    """

    def _next_due(self, obj):
        # La proxima fecha es la de la tarea abierta mas proxima del activo:
        # su pendiente (o la que ya esta en una OT). Sin tarea abierta no hay
        # plan que cumplir.
        if hasattr(obj, "_next_due"):
            return obj._next_due
        from apps.maintenance.models import Task
        return (
            obj.tasks
            .filter(Task.next_maintenance_q())
            .order_by("scheduled_date")
            .values_list("scheduled_date", flat=True)
            .first()
        )

    def get_last_maintenance_date(self, obj):
        if hasattr(obj, "_last_maint"):
            last = obj._last_maint
        else:
            from apps.maintenance.models import Task
            last = (
                obj.tasks
                .filter(status=Task.Status.DONE)
                .order_by("-completed_at")
                .values_list("completed_at", flat=True)
                .first()
            )
        return last.date().isoformat() if last else None

    def get_next_maintenance_date(self, obj):
        next_date = self._next_due(obj)
        return str(next_date) if next_date else None

    def get_maintenance_status(self, obj):
        from datetime import date
        next_date = self._next_due(obj)
        if next_date is None:
            return "no_plan"
        delta = (next_date - date.today()).days
        if delta < 0:
            return "overdue"
        if delta <= 15:
            return "due_soon"
        return "on_time"


class AssetSerializer(AssetMaintenanceFieldsMixin, serializers.ModelSerializer):
    hospital = serializers.SerializerMethodField()
    node = serializers.SerializerMethodField()
    custom_field_values = AssetCustomFieldValueSerializer(many=True, read_only=True)
    # La ficha muestra el mismo bloque de mantenimiento que el listado. Sin estos
    # tres campos llegaban undefined al frontend y AssetDetailPage pintaba
    # "Sin plan"/"Nunca" para cualquier activo, contradiciendo a /activos.
    last_maintenance_date = serializers.SerializerMethodField()
    next_maintenance_date = serializers.SerializerMethodField()
    maintenance_status = serializers.SerializerMethodField()
    plan = serializers.SerializerMethodField()
    coverage = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = [
            "id", "hospital", "node", "name", "code", "manufacturer", "model",
            "serial_number", "equipment_location", "barcode", "priority",
            "asset_type", "classification_1", "classification_2", "supplier",
            "purchase_date", "avg_daily_usage_hours", "status", "notes",
            "qr_code", "photo_url", "installation_date", "warranty_expiry",
            "created_at", "updated_at", "custom_field_values",
            "last_maintenance_date", "next_maintenance_date", "maintenance_status",
            "plan", "coverage",
        ]
        read_only_fields = ["id", "qr_code", "created_at", "updated_at"]

    def get_coverage(self, obj):
        """Garantia y contrato vigentes que cubren el equipo (o None cada uno)."""
        from .contracts import cobertura_del_activo
        return cobertura_del_activo(obj)

    def get_hospital(self, obj):
        return {"id": str(obj.hospital_id), "name": obj.hospital.name}

    def get_node(self, obj):
        if obj.node_id:
            return {"id": str(obj.node_id), "name": obj.node.name, "path": obj.node.path}
        return None

    def get_plan(self, obj):
        if obj.plan_id:
            return {"id": str(obj.plan_id), "name": obj.plan.name}
        return None


class AssetListSerializer(AssetMaintenanceFieldsMixin, serializers.ModelSerializer):
    hospital = serializers.SerializerMethodField()
    node = serializers.SerializerMethodField()
    plan = serializers.SerializerMethodField()
    last_maintenance_date = serializers.SerializerMethodField()
    next_maintenance_date = serializers.SerializerMethodField()
    maintenance_status = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = [
            "id", "name", "code", "hospital", "node", "plan",
            "asset_type", "status", "priority",
            # Columnas planas que el portal del cliente muestra en su tabla.
            "manufacturer", "model", "equipment_location",
            "last_maintenance_date", "next_maintenance_date", "maintenance_status",
        ]

    def get_hospital(self, obj):
        return {"id": str(obj.hospital_id), "name": obj.hospital.name}

    def get_node(self, obj):
        if obj.node_id:
            return {"id": str(obj.node_id), "path": obj.node.path}
        return None

    def get_plan(self, obj):
        if obj.plan_id:
            return {"id": str(obj.plan_id), "name": obj.plan.name}
        return None


class AssetCreateUpdateSerializer(ScopedFieldsMixin, serializers.ModelSerializer):
    # Un usuario limitado a una parte del arbol solo crea y mueve activos dentro de ella.
    scoped_fields = {"hospital": "hospitals", "node": "nodes"}

    class Meta:
        model = Asset
        fields = [
            "id", "hospital", "node", "name", "code", "manufacturer", "model",
            "serial_number", "equipment_location", "barcode", "priority",
            "asset_type", "classification_1", "classification_2", "supplier",
            "purchase_date", "avg_daily_usage_hours", "status", "notes",
            "photo_url", "installation_date", "warranty_expiry", "plan",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        plan = validated_data.pop("plan", None)
        asset = super().create(validated_data)
        if plan is not None:
            _set_plan(asset, plan, self.context)
        return asset

    def update(self, instance, validated_data):
        sentinel = object()
        plan = validated_data.pop("plan", sentinel)
        asset = super().update(instance, validated_data)
        if plan is not sentinel:
            _set_plan(asset, plan, self.context)
        return asset

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
        if node is None and scope.needs_node(self.context):
            raise serializers.ValidationError(
                {"node": "Tu usuario está limitado a una parte del hospital: elige la ubicación."}
            )
        if node and hospital and node.hospital_id != hospital.pk:
            raise serializers.ValidationError(
                {"node": "El nodo no pertenece al mismo hospital que el activo."}
            )
        plan = attrs.get("plan")
        if plan and plan.restrict_to_hospital_id and hospital and plan.restrict_to_hospital_id != hospital.pk:
            raise serializers.ValidationError(
                {"plan": f"El plan «{plan.name}» es solo para {plan.restrict_to_hospital.name}."}
            )
        return attrs


def _set_plan(asset, plan, context):
    """El plan del activo cambia por el servicio: la nueva pendiente hereda la
    fecha de la anterior y las del plan viejo se anulan (decision D7)."""
    from apps.maintenance.services import set_asset_plan

    request = context.get("request")
    set_asset_plan(asset, plan, getattr(request, "user", None))
