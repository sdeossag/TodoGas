import uuid

from django.db.models import Q
from django.http import StreamingHttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.users.permissions import IsAdmin

from .exporter import ExportRangeError, export_filename, iter_csv_lines, resolve_date_range
from .ip import client_ip
from .models import AuditLog
from .serializers import AuditLogSerializer

# Filtros que se registran en la auditoria de la exportacion (las fechas van aparte).
EXPORT_FILTER_KEYS = ('user_id', 'action', 'entity_type', 'entity_id', 'search')


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdmin]
    # Usa config.pagination.DefaultPagination, identica a la que este
    # ViewSet definia por su cuenta cuando era el unico endpoint paginado.

    def get_queryset(self):
        return self._apply_filters(
            AuditLog.objects.select_related('user').order_by('-timestamp'),
            self.request.query_params,
        )

    @staticmethod
    def _apply_filters(qs, p):
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

    @action(detail=False, methods=['get'], url_path='export')
    def export(self, request):
        """CSV del log con los mismos filtros y permisos que el listado.

        Sin fechas exporta los ultimos 90 dias; el rango maximo es de 366 dias.
        """
        p = request.query_params
        try:
            d_from, d_to = resolve_date_range(p.get('date_from'), p.get('date_to'))
        except ExportRangeError as exc:
            return Response({'detail': str(exc)}, status=400)

        # Los filtros de fecha se sustituyen por el rango ya resuelto, para que
        # la exportacion nunca salga sin acotar.
        params = p.copy()
        params['date_from'] = d_from.isoformat()
        params['date_to'] = d_to.isoformat()
        qs = self._apply_filters(
            AuditLog.objects.select_related('user').order_by('timestamp'),
            params,
        )

        # Acceso masivo a datos personales (Habeas Data): queda constancia de quien
        # exporto, cuando, con que filtros y rango. Si no se puede registrar, no se
        # entrega el archivo: la excepcion propaga y responde 500.
        filtros = {k: p[k] for k in EXPORT_FILTER_KEYS if p.get(k)}
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.EXPORT,
            entity_type='AuditLog',
            entity_id=uuid.uuid4(),
            changes={
                'filters': filtros,
                'date_from': d_from.isoformat(),
                'date_to': d_to.isoformat(),
            },
            ip_address=client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )

        response = StreamingHttpResponse(
            iter_csv_lines(qs), content_type='text/csv; charset=utf-8'
        )
        response['Content-Disposition'] = f'attachment; filename="{export_filename(d_from, d_to)}"'
        response['Cache-Control'] = 'no-store'
        return response
