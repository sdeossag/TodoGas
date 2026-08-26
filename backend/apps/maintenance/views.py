from datetime import date

from dateutil.relativedelta import relativedelta
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users.permissions import IsAdmin, IsAdminOrSup
from apps.work_orders.models import WorkOrder

from .engine import calculate_next_due_date, generate_work_orders_for_plan
from .models import MaintenancePlan
from .serializers import (
    MaintenancePlanCreateUpdateSerializer,
    MaintenancePlanDetailSerializer,
    MaintenancePlanListSerializer,
)


class MaintenancePlanViewSet(viewsets.ModelViewSet):
    queryset = (
        MaintenancePlan.objects
        .select_related('checklist_template', 'restrict_to_hospital')
        .prefetch_related(
            'assets__hospital',
            'executions__executed_by',
        )
    )

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'compliance'):
            return [IsAdminOrSup()]
        if self.action in ('create', 'update', 'partial_update', 'trigger', 'pause', 'resume'):
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return MaintenancePlanCreateUpdateSerializer
        if self.action == 'retrieve':
            return MaintenancePlanDetailSerializer
        return MaintenancePlanListSerializer

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=True, methods=['post'])
    def trigger(self, request, pk=None):
        plan = self.get_object()
        result = generate_work_orders_for_plan(plan, triggered_by=request.user)
        return Response(result, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        plan = self.get_object()
        plan.is_active = False
        plan.save(update_fields=['is_active'])
        return Response({'id': str(plan.id), 'is_active': False})

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        plan = self.get_object()
        plan.is_active = True
        plan.next_due_date = calculate_next_due_date(plan, from_date=date.today())
        plan.save(update_fields=['is_active', 'next_due_date'])
        return Response({
            'id': str(plan.id),
            'is_active': True,
            'next_due_date': str(plan.next_due_date),
        })

    @action(detail=True, methods=['get'])
    def compliance(self, request, pk=None):
        plan = self.get_object()
        today = date.today()
        monthly = []

        for i in range(11, -1, -1):
            ref = today.replace(day=1)
            if i > 0:
                ref = ref - relativedelta(months=i)
            qs = plan.generated_work_orders.filter(
                scheduled_date__year=ref.year,
                scheduled_date__month=ref.month,
            )
            total = qs.count()
            completed = qs.filter(status=WorkOrder.Status.COMPLETED).count()
            monthly.append({
                'year': ref.year,
                'month': ref.month,
                'total': total,
                'completed': completed,
                'percentage': round(completed / total * 100, 1) if total else None,
            })

        return Response({
            'plan_id': str(plan.id),
            'plan_name': plan.name,
            'monthly': monthly,
        })
