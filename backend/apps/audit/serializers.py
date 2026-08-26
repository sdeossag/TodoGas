from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'action', 'entity_type', 'entity_id',
            'changes', 'ip_address', 'timestamp',
        ]
        read_only_fields = [
            'id', 'user', 'action', 'entity_type', 'entity_id',
            'changes', 'ip_address', 'timestamp',
        ]

    def get_user(self, obj):
        if not obj.user_id:
            return None
        u = obj.user
        return {
            'id': str(u.id),
            'full_name': f'{u.first_name} {u.last_name}'.strip(),
        }
