from rest_framework import serializers

from .meters import latest
from .models import Meter, MeterReading, MeterUnit


def _num(valor):
    """Decimal sin ceros de sobra: 582.000 -> 582, 13.500 -> 13.5."""
    if valor is None:
        return None
    return float(valor.normalize())


class MeterUnitSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()

    class Meta:
        model = MeterUnit
        fields = ["id", "name", "symbol", "label", "is_counter", "is_active", "sort_order"]
        read_only_fields = ["id"]
        extra_kwargs = {"sort_order": {"required": False}}

    def get_label(self, obj):
        return str(obj)


class MeterReadingSerializer(serializers.ModelSerializer):
    """
    Alta manual desde la ficha del equipo. Las del checklist llegan con la
    respuesta y aqui solo se leen.
    """

    meter = serializers.PrimaryKeyRelatedField(queryset=Meter.objects.select_related("asset", "unit"))
    value = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=0)
    read_at = serializers.DateTimeField(required=False)
    recorded_by_name = serializers.SerializerMethodField()
    task_info = serializers.SerializerMethodField()
    opened_task = serializers.SerializerMethodField()

    class Meta:
        model = MeterReading
        fields = [
            "id", "meter", "value", "accumulated", "read_at", "source", "is_reset", "note",
            "recorded_by_name", "task_info", "opened_task", "created_at",
        ]
        read_only_fields = ["id", "accumulated", "source", "created_at"]

    def get_fields(self):
        campos = super().get_fields()
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            from apps.users import scope

            campos["meter"].queryset = scope.assets(campos["meter"].queryset, user, prefix="asset__")
        return campos

    def to_representation(self, obj):
        datos = super().to_representation(obj)
        datos["value"] = _num(obj.value)
        datos["accumulated"] = _num(obj.accumulated)
        return datos

    def get_recorded_by_name(self, obj):
        u = obj.recorded_by
        if u is None:
            return None
        return f"{u.first_name} {u.last_name}".strip() or u.email

    def get_opened_task(self, obj):
        """Si abrio una tarea: entonces no se borra."""
        return obj.triggered_tasks.exists()

    def get_task_info(self, obj):
        if not obj.task_id:
            return None
        ot = obj.task.work_order
        return {
            "id": str(obj.task_id),
            "title": obj.task.title,
            "work_order": {"id": str(ot.id), "wo_code": ot.wo_code} if ot else None,
        }


class MeterSerializer(serializers.ModelSerializer):
    """
    Medidor del equipo con su ultima lectura y, si el plan tiene tareas "cada
    N" o "cuando" de esa unidad, como va cada una.
    """

    unit_info = MeterUnitSerializer(source="unit", read_only=True)
    last_reading = serializers.SerializerMethodField()
    triggers = serializers.SerializerMethodField()

    class Meta:
        model = Meter
        fields = ["id", "asset", "unit", "unit_info", "last_reading", "triggers", "created_at"]
        read_only_fields = ["id", "created_at"]
        validators = []

    def get_fields(self):
        campos = super().get_fields()
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if "asset" in campos and user is not None and user.is_authenticated:
            from apps.users import scope

            campos["asset"].queryset = scope.assets(campos["asset"].queryset, user)
        return campos

    def get_last_reading(self, obj):
        r = latest(obj)
        if r is None:
            return None
        return {"value": _num(r.value), "accumulated": _num(r.accumulated), "read_at": r.read_at}

    def get_triggers(self, obj):
        from apps.maintenance.models import MeterSchedule, PlanTask

        asset = obj.asset
        if not asset.plan_id:
            return []
        ultima = latest(obj)
        uso = ultima.accumulated if ultima is not None else None
        filas = []
        for pt in PlanTask.objects.filter(
            plan_id=asset.plan_id, meter_unit=obj.unit, is_active=True,
            trigger__in=[PlanTask.Trigger.EVERY, PlanTask.Trigger.WHEN],
        ):
            fila = {"plan_task": str(pt.id), "name": pt.name, "trigger": pt.trigger}
            if pt.trigger == PlanTask.Trigger.EVERY:
                sched = MeterSchedule.objects.filter(plan_task=pt, asset=asset).first()
                fila["interval"] = _num(pt.meter_interval)
                fila["next_due"] = _num(sched.next_due) if sched else None
                fila["remaining"] = (
                    _num(sched.next_due - uso) if sched is not None and uso is not None else None
                )
            else:
                fila["comparator"] = pt.meter_comparator
                fila["comparator_display"] = pt.get_meter_comparator_display()
                fila["threshold"] = _num(pt.meter_threshold)
            filas.append(fila)
        return filas

    def validate(self, attrs):
        if Meter.objects.filter(asset=attrs["asset"], unit=attrs["unit"]).exists():
            raise serializers.ValidationError({"unit": "El equipo ya tiene un medidor de esa unidad."})
        return attrs
