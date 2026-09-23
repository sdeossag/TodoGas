import uuid as _uuid_mod

from django.db.models import Case, IntegerField, Q, Value, When
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditLog
from apps.users import scope
from apps.users.models import User
from apps.users.permissions import IsAdmin, IsAdminOrSup

from . import integrity
from .integrity import verify_work_order
from .models import WorkOrder, WorkOrderStatusHistory
from .serializers import (
    WorkOrderCreateSerializer,
    WorkOrderDetailSerializer,
    TaskChecklistSerializer,
    TaskIdsSerializer,
    WorkOrderFromTasksSerializer,
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


# Estados terminales: la OT ya es un registro con valor probatorio y no admite
# mas cambios (RF-TR-03, RF-OT-03, RF-OT-07). El unico camino de salida seria
# una OT nueva, nunca la edicion de la cerrada.
_TERMINAL_STATUSES = (WorkOrder.Status.COMPLETED, WorkOrder.Status.CANCELLED)


def _terminal_state_response(wo):
    """403 con el motivo, o None si la OT todavia admite cambios."""
    if wo.status not in _TERMINAL_STATUSES:
        return None
    return Response(
        {
            "detail": (
                f"La OT {wo.wo_number} esta en estado {wo.status} y no admite "
                "modificaciones. Los registros de una intervencion cerrada son "
                "inmutables."
            )
        },
        status=status.HTTP_403_FORBIDDEN,
    )


class WorkOrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = WorkOrder.objects.select_related(
            "hospital",
            "location",
            "assigned_to",
            "created_by",
        ).prefetch_related(
            "tasks__asset__hospital",
            "tasks__asset__node",
            "tasks__plan_task__plan",
            "tasks__checklist_version__template",
            "tasks__checklist_response__version__fields",
            "tasks__checklist_response__field_responses",
            "status_history",
            "status_history__changed_by",
            "photos",
            "signatures",
            "reports",
        )

        # Hospital o parte del arbol (apps.users.scope). Al tecnico no se le
        # aplica: ve lo que tiene asignado, y si se le asigna una OT de fuera de
        # su alcance es porque alguien lo decidio.
        if user.role in (User.Role.ADMIN, User.Role.SUP):
            qs = scope.work_orders(qs, user)
        elif user.role == User.Role.TEC:
            qs = qs.filter(assigned_to=user)
        elif user.role == User.Role.CLI:
            # El hospital ve lo finalizado; lo que esta en curso no.
            qs = scope.work_orders(qs.filter(status=WorkOrder.Status.COMPLETED), user)
        else:
            qs = qs.none()

        params = self.request.query_params
        # Los filtros por activo pasan por las tareas: una OT puede tener varias
        # y el join repetiria la OT una vez por cada coincidencia.
        via_tareas = False

        if v := params.get("status"):
            qs = qs.filter(status=v)
        if v := params.get("task_type"):
            qs = qs.filter(task_type=v)
        if v := params.get("priority"):
            qs = qs.filter(priority=v)
        if v := params.get("asset_id"):
            qs = qs.filter(tasks__asset_id=v)
            via_tareas = True
        if v := params.get("hospital_id"):
            qs = qs.filter(hospital_id=v)
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
                | Q(tasks__asset__name__icontains=v)
                | Q(tasks__asset__code__icontains=v)
                | wo_num_q
            )
            via_tareas = True

        if via_tareas:
            qs = qs.distinct()
        return qs.annotate(priority_order=_PRIORITY_ORDER).order_by(
            "priority_order", "scheduled_date"
        )

    def get_serializer_class(self):
        if self.action == "list":
            return WorkOrderListSerializer
        if self.action == "retrieve":
            return WorkOrderDetailSerializer
        if self.action == "create":
            if self._from_tasks():
                return WorkOrderFromTasksSerializer
            return WorkOrderCreateSerializer
        if self.action == "partial_update":
            if self.request.user.role == User.Role.TEC:
                return WorkOrderTechnicianUpdateSerializer
            return WorkOrderUpdateSerializer
        return WorkOrderDetailSerializer

    def _from_tasks(self):
        return hasattr(self.request.data, "get") and "task_ids" in self.request.data

    def get_permissions(self):
        if self.action == "create":
            # Agrupar pendientes es trabajo del planificador, que en el diseno
            # es administrador o supervisor. El alta manual sigue solo para ADMIN.
            return [IsAdminOrSup()] if self._from_tasks() else [IsAdmin()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from apps.maintenance.services import TaskStateError

        try:
            wo = serializer.save()
        except TaskStateError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        datos = WorkOrderDetailSerializer(wo, context={"request": request}).data
        datos["warnings"] = getattr(serializer, "warnings", [])
        return Response(datos, status=status.HTTP_201_CREATED)

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
        if blocked := _terminal_state_response(wo):
            return blocked
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
        # Segunda via de mutacion: `assign` no pasa por partial_update, asi que
        # necesita su propio guard o el tecnico de una OT cerrada seguiria
        # siendo editable (RF-OT-06 solo permite reasignar en estados activos).
        if blocked := _terminal_state_response(wo):
            return blocked
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

    @action(detail=True, methods=["post"], url_path="regenerate-report")
    def regenerate_report(self, request, pk=None):
        """
        Vuelve a lanzar la generacion del PDF de una OT ya completada.

        El unico disparador normal es la transicion a COMPLETED. Si esa
        ejecucion falla (worker caido, WeasyPrint sin librerias nativas), la OT
        se queda sin reporte y no habia forma de recuperarla desde la interfaz.
        """
        if request.user.role != User.Role.ADMIN:
            return Response(status=status.HTTP_403_FORBIDDEN)

        wo = self.get_object()
        if wo.status != WorkOrder.Status.COMPLETED:
            return Response(
                {"detail": "Solo se puede generar el reporte de una OT completada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.reports.tasks import generate_work_order_pdf

        generate_work_order_pdf.delay(str(wo.id))

        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.CREATE,
            entity_type="GeneratedReport",
            entity_id=wo.id,
            changes={"action": "regenerate", "work_order": str(wo.id)},
            ip_address=_get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        return Response({"status": "queued"})

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

    # ── Tareas de la OT (fase 3) ──────────────────────────────────────────────

    def _detalle(self, wo, **extra):
        wo = self.get_queryset().get(pk=wo.pk)
        datos = WorkOrderDetailSerializer(wo, context={"request": self.request}).data
        datos.update(extra)
        return Response(datos)

    @action(detail=True, methods=["post"])
    def tasks(self, request, pk=None):
        """Agrega tareas pendientes a una OT que aun no empezo."""
        from apps.maintenance import services

        if request.user.role not in (User.Role.ADMIN, User.Role.SUP):
            return Response(status=status.HTTP_403_FORBIDDEN)
        wo = self.get_object()
        entrada = TaskIdsSerializer(data=request.data, context={"request": request})
        entrada.is_valid(raise_exception=True)
        try:
            avisos = services.add_tasks_to_work_order(wo, entrada.validated_data["task_ids"])
        except services.TaskStateError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return self._detalle(wo, warnings=avisos)

    @action(detail=True, methods=["post"], url_path="remove-task")
    def remove_task(self, request, pk=None):
        """
        Saca una tarea de una OT que aun no empezo; vuelve a pendientes. Es POST
        y no DELETE porque la OT no admite DELETE: habilitarlo abriria el
        borrado de OTs.
        """
        from apps.maintenance import services

        if request.user.role not in (User.Role.ADMIN, User.Role.SUP):
            return Response(status=status.HTTP_403_FORBIDDEN)
        wo = self.get_object()
        entrada = TaskIdsSerializer(
            data={"task_ids": [request.data.get("task_id")]}, context={"request": request}
        )
        entrada.is_valid(raise_exception=True)
        tarea = entrada.validated_data["task_ids"][0]
        if tarea.work_order_id != wo.id:
            return Response(
                {"task_id": "La tarea no es de esta OT."}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            services.remove_task_from_work_order(wo, tarea)
        except services.TaskStateError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return self._detalle(wo)

    @action(detail=True, methods=["post"], url_path="task-checklist")
    def task_checklist(self, request, pk=None):
        """Cambia el checklist de una tarea de la OT, mientras nadie lo respondio."""
        from apps.maintenance import services

        if request.user.role not in (User.Role.ADMIN, User.Role.SUP):
            return Response(status=status.HTTP_403_FORBIDDEN)
        wo = self.get_object()
        entrada = TaskChecklistSerializer(data=request.data, context={"work_order": wo})
        entrada.is_valid(raise_exception=True)
        services.change_task_checklist(
            entrada.validated_data["task"], entrada.validated_data["checklist_version"]
        )
        return self._detalle(wo)

    @action(detail=True, methods=["get"], url_path="offline-bundle")
    def offline_bundle(self, request, pk=None):
        """
        Todo lo que el tecnico necesita para ejecutar la OT sin red: el detalle
        con sus tareas y el checklist de cada una con sus campos y respuestas.
        La app lo guarda en SQLite al tener conexion.
        """
        from apps.checklists.models import ChecklistResponse
        from apps.checklists.serializers import ChecklistResponseSerializer

        wo = self.get_object()
        respuestas = (
            ChecklistResponse.objects.filter(task__work_order=wo)
            .select_related("version", "completed_by", "task")
            .prefetch_related("version__fields", "field_responses__field")
            .order_by("task__sort_order", "task__created_at")
        )
        return Response({
            "work_order": WorkOrderDetailSerializer(wo, context={"request": request}).data,
            "checklists": ChecklistResponseSerializer(respuestas, many=True).data,
        })


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

        # Cada acta se verifica con el algoritmo con que se firmo. Antes una
        # version distinta respondia "regenera el reporte", y regenerar
        # recalcula el hash con lo que diga la base ahora: una alteracion
        # quedaba lavada.
        resultado = verify_work_order(wo)
        report = resultado.report

        if resultado.outcome == integrity.NO_REPORT:
            return Response(
                {"detail": "No existe reporte generado para esta OT."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if resultado.outcome == integrity.NO_HASH:
            # Reporte anterior a la introduccion del hash de contenido: no se
            # puede afirmar ni negar la integridad, y decir "verificado" seria
            # peor que decir que no se sabe.
            return Response(
                {
                    "verified": None,
                    "message": (
                        "El reporte se genero antes de que existiera el hash de "
                        "contenido. Regenera el reporte para poder verificarlo."
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )

        if resultado.outcome == integrity.UNKNOWN_VERSION:
            return Response(
                {
                    "verified": None,
                    "message": (
                        f"El hash se calculo con un algoritmo desconocido "
                        f"({report.integrity_version or 'sin version'}). No se "
                        "puede verificar."
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )

        verified = resultado.verified
        return Response(
            {
                "verified": verified,
                "stored_hash": report.content_hash[:16] + "...",
                "recomputed_hash": resultado.recomputed_hash[:16] + "...",
                "algorithm_version": report.integrity_version,
                "message": (
                    "Integridad verificada" if verified else "ALERTA: El documento fue modificado"
                ),
            }
        )
