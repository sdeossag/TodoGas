from django.db import transaction
from rest_framework import serializers

from apps.audit.models import AuditLog

from .models import InventoryItem, StockMovement


class InventoryItemSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.SerializerMethodField()

    class Meta:
        model = InventoryItem
        fields = [
            'id', 'name', 'code', 'description', 'unit_of_measure',
            'current_stock', 'min_stock', 'unit_cost', 'is_active',
            'is_low_stock', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'current_stock', 'created_at', 'updated_at']

    def get_is_low_stock(self, obj):
        return obj.current_stock <= obj.min_stock


class InventoryItemCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = [
            'id', 'name', 'code', 'description', 'unit_of_measure',
            'min_stock', 'unit_cost', 'is_active',
        ]
        read_only_fields = ['id']

    def validate_code(self, value):
        qs = InventoryItem.objects.filter(code=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe un item con este codigo.")
        return value


class StockMovementSerializer(serializers.ModelSerializer):
    item = serializers.SerializerMethodField()
    work_order = serializers.SerializerMethodField()
    performed_by = serializers.SerializerMethodField()
    stock_after = serializers.SerializerMethodField()

    class Meta:
        model = StockMovement
        fields = [
            'id', 'item', 'movement_type', 'quantity', 'work_order',
            'reference', 'notes', 'performed_by', 'performed_at',
            'stock_after',
        ]

    def get_item(self, obj):
        i = obj.item
        return {'id': str(i.id), 'name': i.name, 'code': i.code}

    def get_work_order(self, obj):
        if not obj.work_order_id:
            return None
        wo = obj.work_order
        return {'id': str(wo.id), 'wo_number': wo.wo_number, 'wo_code': wo.wo_code}

    def get_performed_by(self, obj):
        u = obj.performed_by
        return {'id': str(u.id), 'full_name': f'{u.first_name} {u.last_name}'.strip()}

    def get_stock_after(self, obj):
        # Approximation: current stock at read time
        return obj.item.current_stock


class StockMovementCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = [
            'item', 'movement_type', 'quantity', 'work_order',
            'reference', 'notes',
        ]

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor que cero.")
        return value

    def validate(self, attrs):
        item = attrs.get('item')
        movement_type = attrs.get('movement_type')
        quantity = attrs.get('quantity')

        if movement_type == StockMovement.MovementType.OUT:
            if item and item.current_stock < quantity:
                raise serializers.ValidationError(
                    f"Stock insuficiente. Disponible: {item.current_stock}"
                )
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        movement_type = validated_data['movement_type']
        quantity = validated_data['quantity']

        with transaction.atomic():
            item = InventoryItem.objects.select_for_update().get(
                pk=validated_data['item'].pk
            )
            if movement_type == StockMovement.MovementType.IN:
                item.current_stock += quantity
            elif movement_type == StockMovement.MovementType.OUT:
                item.current_stock -= quantity
            elif movement_type == StockMovement.MovementType.ADJUSTMENT:
                item.current_stock = quantity
            item.save(update_fields=['current_stock', 'updated_at'])

            validated_data['item'] = item
            movement = StockMovement.objects.create(
                **validated_data,
                performed_by=request.user,
            )

        try:
            AuditLog.objects.create(
                user=request.user if request else None,
                action=AuditLog.Action.CREATE,
                entity_type='StockMovement',
                entity_id=movement.id,
                changes={
                    'movement_type': movement_type,
                    'quantity': str(quantity),
                    'item_code': item.code,
                    'stock_after': str(item.current_stock),
                },
            )
        except Exception:
            pass

        return movement
