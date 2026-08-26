from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from rest_framework import serializers

from apps.assets.models import Asset

from .models import MaintenancePlan, MaintenancePlanExecution


class MaintenancePlanExecutionSerializer(serializers.ModelSerializer):
    plan = serializers.SerializerMethodField()
    executed_by = serializers.SerializerMethodField()

    class Meta:
        model = MaintenancePlanExecution
        fields = ['id', 'plan', 'executed_at', 'executed_by', 'work_orders_created', 'notes']
        read_only_fields = ['id']

    def get_plan(self, obj):
        return {'id': str(obj.plan_id), 'name': obj.plan.name}

    def get_executed_by(self, obj):
        if obj.executed_by_id:
            u = obj.executed_by
            return {'id': str(u.id), 'full_name': f'{u.first_name} {u.last_name}'.strip()}
        return None


class MaintenancePlanListSerializer(serializers.ModelSerializer):
    assets_count = serializers.SerializerMethodField()
    checklist_template = serializers.SerializerMethodField()
    last_execution = serializers.SerializerMethodField()
    compliance_percentage = serializers.SerializerMethodField()

    class Meta:
        model = MaintenancePlan
        fields = [
            'id', 'name', 'task_type', 'frequency_value', 'frequency_unit',
            'is_active', 'assets_count', 'checklist_template', 'last_execution',
            'next_due_date', 'compliance_percentage',
        ]

    def get_assets_count(self, obj):
        return obj.assets.count()

    def get_checklist_template(self, obj):
        if obj.checklist_template_id:
            return {'id': str(obj.checklist_template_id), 'name': obj.checklist_template.name}
        return None

    def get_last_execution(self, obj):
        last = obj.executions.order_by('-executed_at').first()
        if last:
            return {
                'executed_at': last.executed_at,
                'work_orders_created': last.work_orders_created,
            }
        return None

    def get_compliance_percentage(self, obj):
        today = date.today()
        qs = obj.generated_work_orders.filter(
            scheduled_date__year=today.year,
            scheduled_date__month=today.month,
        )
        total = qs.count()
        if total == 0:
            return None
        from apps.work_orders.models import WorkOrder
        completed = qs.filter(status=WorkOrder.Status.COMPLETED).count()
        return round(completed / total * 100, 1)


class MaintenancePlanDetailSerializer(MaintenancePlanListSerializer):
    restrict_to_hospital = serializers.SerializerMethodField()
    assets = serializers.SerializerMethodField()
    executions = serializers.SerializerMethodField()
    next_5_dates = serializers.SerializerMethodField()

    class Meta(MaintenancePlanListSerializer.Meta):
        fields = MaintenancePlanListSerializer.Meta.fields + [
            'description', 'classification_1', 'classification_2', 'priority',
            'estimated_duration', 'downtime_duration',
            'restrict_to_hospital', 'assets', 'executions', 'next_5_dates',
            'last_generated_at', 'created_at', 'updated_at',
        ]

    def get_restrict_to_hospital(self, obj):
        if obj.restrict_to_hospital_id:
            return {'id': str(obj.restrict_to_hospital_id), 'name': obj.restrict_to_hospital.name}
        return None

    def get_assets(self, obj):
        return [
            {
                'id': str(a.id),
                'code': a.code,
                'name': a.name,
                'hospital_name': a.hospital.name,
            }
            for a in obj.assets.select_related('hospital').all()
        ]

    def get_executions(self, obj):
        last5 = obj.executions.order_by('-executed_at')[:5]
        return MaintenancePlanExecutionSerializer(last5, many=True).data

    def get_next_5_dates(self, obj):
        if not obj.next_due_date:
            return []
        dates = []
        fu = obj.frequency_unit
        fv = obj.frequency_value
        current = obj.next_due_date
        for _ in range(5):
            dates.append(str(current))
            if fu == MaintenancePlan.FrequencyUnit.DAYS:
                current = current + timedelta(days=fv)
            elif fu == MaintenancePlan.FrequencyUnit.WEEKS:
                current = current + timedelta(weeks=fv)
            elif fu == MaintenancePlan.FrequencyUnit.MONTHS:
                current = current + relativedelta(months=fv)
            elif fu == MaintenancePlan.FrequencyUnit.YEARS:
                current = current + relativedelta(years=fv)
        return dates


class MaintenancePlanCreateUpdateSerializer(serializers.ModelSerializer):
    assets = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Asset.objects.all(),
    )

    class Meta:
        model = MaintenancePlan
        fields = [
            'id', 'name', 'description', 'task_type', 'classification_1', 'classification_2',
            'priority', 'estimated_duration', 'downtime_duration',
            'frequency_value', 'frequency_unit', 'checklist_template', 'assets',
            'restrict_to_hospital', 'is_active',
        ]
        read_only_fields = ['id']

    def validate_frequency_value(self, value):
        if value <= 0:
            raise serializers.ValidationError("La frecuencia debe ser mayor a 0.")
        return value

    def validate_assets(self, value):
        if not value:
            raise serializers.ValidationError("El plan debe tener al menos un activo.")
        return value

    def create(self, validated_data):
        from .engine import calculate_next_due_date
        assets = validated_data.pop('assets', [])
        plan = MaintenancePlan(**validated_data)
        plan.next_due_date = calculate_next_due_date(plan, from_date=date.today())
        plan.save()
        plan.assets.set(assets)
        return plan

    def update(self, instance, validated_data):
        assets = validated_data.pop('assets', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if assets is not None:
            instance.assets.set(assets)
        return instance
