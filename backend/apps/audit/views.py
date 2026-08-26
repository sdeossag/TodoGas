from django.db.models import Q
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination

from apps.users.permissions import IsAdmin

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdmin]
    pagination_class = AuditPagination

    def get_queryset(self):
        qs = AuditLog.objects.select_related('user').order_by('-timestamp')
        p = self.request.query_params

        if v := p.get('user_id'):
            qs = qs.filter(user_id=v)
        if v := p.get('action'):
            qs = qs.filter(action=v)
        if v := p.get('entity_type'):
            qs = qs.filter(entity_type=v)
        if v := p.get('entity_id'):
            qs = qs.filter(entity_id=v)
        if v := p.get('date_from'):
            qs = qs.filter(timestamp__date__gte=v)
        if v := p.get('date_to'):
            qs = qs.filter(timestamp__date__lte=v)
        if v := p.get('search'):
            qs = qs.filter(
                Q(entity_type__icontains=v) | Q(action__icontains=v)
            )
        return qs
