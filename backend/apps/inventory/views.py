from django.db.models import F, Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import User
from apps.users.permissions import IsAdmin, IsAdminOrSup, IsAdminOrSupOrTec

from .models import InventoryItem, StockMovement
from .serializers import (
    InventoryItemCreateUpdateSerializer,
    InventoryItemSerializer,
    StockMovementCreateSerializer,
    StockMovementSerializer,
)


class InventoryItemViewSet(viewsets.ModelViewSet):
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'low_stock'):
            return [IsAdminOrSupOrTec()]
        return [IsAdmin()]

    def get_serializer_class(self):
        if self.action in ('create', 'partial_update'):
            return InventoryItemCreateUpdateSerializer
        return InventoryItemSerializer

    def get_queryset(self):
        qs = InventoryItem.objects.all()
        p = self.request.query_params
        if v := p.get('is_active'):
            qs = qs.filter(is_active=v.lower() == 'true')
        if v := p.get('search'):
            qs = qs.filter(Q(name__icontains=v) | Q(code__icontains=v))
        return qs

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=False, methods=['get'], url_path='low-stock')
    def low_stock(self, request):
        items = InventoryItem.objects.filter(current_stock__lte=F('min_stock'))
        return Response(InventoryItemSerializer(items, many=True).data)


class StockMovementViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAdminOrSupOrTec()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            return StockMovementCreateSerializer
        return StockMovementSerializer

    def get_queryset(self):
        qs = StockMovement.objects.select_related(
            'item', 'work_order', 'performed_by'
        )
        p = self.request.query_params
        if v := p.get('item_id'):
            qs = qs.filter(item_id=v)
        if v := p.get('movement_type'):
            qs = qs.filter(movement_type=v)
        if v := p.get('work_order_id'):
            qs = qs.filter(work_order_id=v)
        if v := p.get('date_from'):
            qs = qs.filter(performed_at__date__gte=v)
        if v := p.get('date_to'):
            qs = qs.filter(performed_at__date__lte=v)
        return qs

    def create(self, request, *args, **kwargs):
        user = request.user
        role = getattr(user, 'role', None)

        if role not in (User.Role.ADMIN, User.Role.SUP, User.Role.TEC):
            return Response(status=status.HTTP_403_FORBIDDEN)

        if role == User.Role.TEC:
            if request.data.get('movement_type') != StockMovement.MovementType.OUT:
                return Response(
                    {'detail': 'Los tecnicos solo pueden registrar salidas (OUT).'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            wo_id = request.data.get('work_order')
            if not wo_id:
                return Response(
                    {'detail': 'Los tecnicos deben vincular la salida a una OT.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            from apps.work_orders.models import WorkOrder
            try:
                wo = WorkOrder.objects.get(pk=wo_id)
            except WorkOrder.DoesNotExist:
                return Response(
                    {'detail': 'OT no encontrada.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if str(wo.assigned_to_id) != str(user.id):
                return Response(
                    {'detail': 'Solo puedes registrar salidas en tus propias OTs.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        serializer = StockMovementCreateSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        movement = serializer.save()
        return Response(
            StockMovementSerializer(movement).data,
            status=status.HTTP_201_CREATED,
        )


class StockAlertView(APIView):
    permission_classes = [IsAdminOrSup]

    def get(self, request):
        items = InventoryItem.objects.filter(current_stock__lte=F('min_stock'))
        return Response({
            'low_stock_count': items.count(),
            'items': InventoryItemSerializer(items, many=True).data,
        })
