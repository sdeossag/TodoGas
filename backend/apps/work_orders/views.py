import uuid as _uuid_mod

from django.db.models import Case, IntegerField, Q, Value, When
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditLog
from apps.users.models import User
from apps.users.permissions import IsAdmin, IsAdminOrSup

from .dashboard import compute_wo_integrity_hash
from .models import WorkOrder, WorkOrderStatusHistory
from .serializers import (
    WorkOrderCreateSerializer,
    WorkOrderDetailSerializer,
    WorkOrderListSerializer,
    WorkOrderStatusHistorySerializer,
    WorkOrderTechnicianUpdateSerializer,
    WorkOrderUpdateSerializer,
)
from .transitions import apply_transition

_PRIORITY_ORDER = Case(
    When(priority=WorkOrder.Priority.HIGH, then=Value(0)),
    When(priority=WorkOrder.Priority.MEDIUM, then=Value(1)),
    When(priority=WorkOrder.Priority.LOW, then=Value(2)),
    output_field=IntegerField(),
)


def _get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class WorkOrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = WorkOrder.objects.select_related(
            "asset",
            "asset__hospital",
            "asset__node",
            "assigned_to",
            "created_by",
            "maintenance_plan",
            "checklist_version",
            "checklist_version__template",
        ).prefetch_related(
            "status_history",
            "status_history__changed_by",
            "photos",
            "signatures",
            "reports",
        )

        if user.role in (User.Role.ADMIN, User.Role.SUP):
            pass
        elif user.role == User.Role.TEC:
            qs = qs.filter(assigned_to=user)
        elif user.role == User.Role.CLI:
            qs = qs.filter(
                status=WorkOrder.Status.COMPLETED,
                asset__hospital=user.hospital,
            )
        else:
            qs = qs.none()

        params = self.request.query_params

        if v := params.get("status"):
            qs = qs.filter(status=v)
        if v := params.get("task_type"):
            qs = qs.filter(task_type=v)
        if v := params.get("priority"):
            qs = qs.filter(priority=v)
        if v := params.get("asset_id"):
            qs = qs.filter(asset_id=v)
        if v := params.get("hospital_id"):
            qs = qs.filter(asset__hospital_id=v)
        if v := params.get("assigned_to_id"):
            qs = qs.filter(assigned_to_id=v)
        if v := params.get("scheduled_date_from"):
            qs = qs.filter(scheduled_date__gte=v)
        if v := params.get("scheduled_date_to"):
            qs = qs.filter(scheduled_date__lte=v)
        if params.get("is_overdue", "").lower() in ("true", "1"):
            today = timezone.now().date()
            qs = qs.filter(scheduled_date__lt=today).exclude(
                status__in=[WorkOrder.Status.COMPLETED, WorkOrder.Status.CANCELLED]
            )
        if v := params.get("search"):
            wo_num_q = Q()
            try:
                wo_num_q = Q(wo_number=int(v))
            except ValueError:
                pass
            qs = qs.filter(
                Q(title__icontains=v)
                | Q(asset__name__icontains=v)
                | Q(asset__code__icontains=v)
                | wo_num_q
            )

        return qs.annotate(priority_order=_PRIORITY_ORDER).order_by(
            "priority_order", "scheduled_date"
        )

    def get_serializer_class(self):
        if self.action == "list":
            return WorkOrderListSerializer
        if self.action == "retrieve":
            return WorkOrderDetailSerializer
        if self.action == "create":
            return WorkOrderCreateSerializer
        if self.action == "partial_update":
            if self.request.user.role == User.Role.TEC:
                return WorkOrderTechnicianUpdateSerializer
            return WorkOrderUpdateSerializer
        return WorkOrderDetailSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsAdmin()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        wo = serializer.save()
        return Response(
            WorkOrderDetailSerializer(wo, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        user = request.user
        if user.role not in (User.Role.ADMIN, User.Role.SUP, User.Role.TEC):
            return Response(status=status.HTTP_403_FORBIDDEN)
        wo = self.get_object()
        if user.role == User.Role.TEC and wo.assigned_to_id != user.id:
            return Response(
                {"detail": "Solo puedes editar tus propias OTs."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().partial_update(request, *args, **kwargs)

    # DELETE always returns 405 (http_method_names excludes 'delete', so this
    # is a safety net in case the router exposes the URL anyway)
    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        wo = self.get_object()
        new_status = request.data.get("new_status")
        if not new_status:
            return Response(
                {"detail": "Se requiere 'new_status'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        comment = request.data.get("comment", "")
        wo = apply_transition(wo, new_status, request.user, comment)
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.STATUS_CHANGE,
            entity_type="WorkOrder",
            entity_id=wo.id,
            changes={"new_status": new_status, "comment": comment},
            ip_address=_get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        return Response(
            WorkOrderDetailSerializer(wo, context={"request": request}).data
        )

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        if request.user.role != User.Role.ADMIN:
            return Response(status=status.HTTP_403_FORBIDDEN)
        wo = self.get_object()
        assigned_to_id = request.data.get("assigned_to")
        if not assigned_to_id:
            return Response(
                {"detail": "Se requiere 'assigned_to'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            tech = User.objects.get(id=assigned_to_id, role=User.Role.TEC)
        except User.DoesNotExist:
            return Response(
                {"detail": "Usuario no encontrado o no tiene rol TEC."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        old_assignee_id = str(wo.assigned_to_id) if wo.assigned_to_id else None
        wo.assigned_to = tech
        wo.save(update_fields=["assigned_to", "updated_at"])
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.UPDATE,
            entity_type="WorkOrder",
            entity_id=wo.id,
            changes={"assigned_to": {"from": old_assignee_id, "to": str(tech.id)}},
            ip_address=_get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        from apps.notifications.service import send_assignment_notification
        send_assignment_notification(wo)
        return Response(
            WorkOrderDetailSerializer(wo, context={"request": request}).data
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        if request.user.role != User.Role.ADMIN:
            return Response(status=status.HTTP_403_FORBIDDEN)
        wo = self.get_object()
        comment = request.data.get("comment", "").strip()
        if not comment:
            return Response(
                {"detail": "Se requiere un comentario para cancelar una OT."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        wo = apply_transition(wo, WorkOrder.Status.CANCELLED, request.user, comment)
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.STATUS_CHANGE,
            entity_type="WorkOrder",
            entity_id=wo.id,
            changes={"new_status": WorkOrder.Status.CANCELLED, "comment": comment},
            ip_address=_get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        return Response(
            WorkOrderDetailSerializer(wo, context={"request": request}).data
        )


class WorkOrderStatusHistoryViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET /api/work-orders/{work_order_pk}/history/
    Solo ADMIN y SUP pueden consultar el historial.
    """

    serializer_class = WorkOrderStatusHistorySerializer
    permission_classes = [IsAdminOrSup]

    def get_queryset(self):
        return WorkOrderStatusHistory.objects.filter(
            work_order_id=self.kwargs["work_order_pk"]
        ).select_related("changed_by")


class IntegrityCheckView(APIView):
    """
    GET /api/work-orders/{pk}/integrity/
    Solo ADMIN. Verifica que el documento de una OT COMPLETED no fue alterado.
    """

    permission_classes = [IsAdmin]

    def get(self, request, pk):
        try:
            wo = WorkOrder.objects.get(pk=pk)
        except WorkOrder.DoesNotExist:
            return Response({"detail": "No encontrada."}, status=status.HTTP_404_NOT_FOUND)

        if wo.status != WorkOrder.Status.COMPLETED:
            return Response(
                {"detail": "La OT no está COMPLETED."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.reports.models import GeneratedReport

        report = (
            GeneratedReport.objects.filter(work_order=wo)
            .order_by("-generated_at")
            .first()
        )
        if not report:
            return Response(
                {"detail": "No existe reporte generado para esta OT."},
                status=status.HTTP_404_NOT_FOUND,
            )

        recomputed = compute_wo_integrity_hash(wo)
        stored_hash = report.file_hash
        verified = recomputed == stored_hash

        return Response(
            {
                "verified": verified,
                "stored_hash": stored_hash[:16] + "...",
                "message": (
                    "Integridad verificada" if verified else "ALERTA: El documento fue modificado"
                ),
            }
        )
