from datetime import date

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.db.models import Count, Min, Prefetch, Q
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.assets.models import Asset, AssetNode
from apps.users.permissions import IsAdmin, IsAdminOrSup
from apps.users import scope

from . import services
from .models import MaintenancePlan, PlanTask, RescheduleCause, Task
from .serializers import (
    AssetIdsSerializer,
    BulkCancelInputSerializer,
    BulkRescheduleInputSerializer,
    CancelInputSerializer,
    EventOccurrenceSerializer,
    MaintenancePlanCreateUpdateSerializer,
    MaintenancePlanDetailSerializer,
    MaintenancePlanListSerializer,
    PlanTaskSerializer,
    RescheduleCauseSerializer,
    RescheduleInputSerializer,
    TaskRescheduleSerializer,
    TaskSerializer,
)

_ABIERTAS = Q(occurrences__status__in=Task.OPEN_STATUSES)
_HECHAS = Q(occurrences__status=Task.Status.DONE)


def _error(exc):
    return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


def _plan_tasks_con_conteos():
    return (
        PlanTask.objects.select_related("plan", "checklist_template")
        .annotate(
            open_total=Count("occurrences", filter=_ABIERTAS),
            done_total=Count("occurrences", filter=_HECHAS),
        )
        .order_by("sort_order", "name")
    )


def _sync_plan(plan, user):
    for plan_task in plan.tasks.filter(is_active=True, trigger=PlanTask.Trigger.DATE):
        services.sync_plan_task(plan_task, user)


# ── Planes de tareas ──────────────────────────────────────────────────────────

class MaintenancePlanViewSet(viewsets.ModelViewSet):

    def get_queryset(self):
        hoy = timezone.localdate()
        de_tarea_activa = Q(tasks__is_active=True)
        oc = "tasks__occurrences__"
        pendiente = Q(**{f"{oc}status": Task.Status.PENDING})
        este_mes = Q(**{f"{oc}scheduled_date__year": hoy.year, f"{oc}scheduled_date__month": hoy.month})
        qs = (
            MaintenancePlan.objects.select_related("restrict_to_hospital")
            .prefetch_related(Prefetch("tasks", queryset=_plan_tasks_con_conteos()))
            .annotate(
                assets_total=Count("assets", distinct=True),
                next_due=Min(
                    f"{oc}scheduled_date",
                    filter=de_tarea_activa & Q(**{f"{oc}status__in": Task.OPEN_STATUSES}),
                ),
                pending_total=Count("tasks__occurrences", distinct=True, filter=de_tarea_activa & pendiente),
                overdue_total=Count(
                    "tasks__occurrences", distinct=True,
                    filter=de_tarea_activa & pendiente & Q(**{f"{oc}scheduled_date__lt": hoy}),
                ),
                month_total=Count(
                    "tasks__occurrences", distinct=True,
                    filter=este_mes & Q(**{f"{oc}status__in": [
                        Task.Status.PENDING, Task.Status.SCHEDULED, Task.Status.DONE,
                    ]}),
                ),
                month_done=Count(
                    "tasks__occurrences", distinct=True,
                    filter=este_mes & Q(**{f"{oc}status": Task.Status.DONE}),
                ),
            )
        )
        activo = self.request.query_params.get("is_active")
        if activo in ("true", "false"):
            qs = qs.filter(is_active=activo == "true")
        busqueda = self.request.query_params.get("search")
        if busqueda:
            qs = qs.filter(name__icontains=busqueda)
        # Con agregados Django ignora Meta.ordering: sin esto la paginacion
        # podria repetir o saltarse planes entre paginas.
        return qs.order_by("name")

    def get_permissions(self):
        if self.action in ("list", "retrieve", "compliance"):
            return [IsAdminOrSup()]
        if self.action in (
            "create", "update", "partial_update", "pause", "resume",
            "assign_assets", "remove_assets",
        ):
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return MaintenancePlanCreateUpdateSerializer
        if self.action == "retrieve":
            return MaintenancePlanDetailSerializer
        return MaintenancePlanListSerializer

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def perform_update(self, serializer):
        estaba_activo = serializer.instance.is_active
        plan = serializer.save()
        if plan.is_active and not estaba_activo:
            _sync_plan(plan, self.request.user)

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        plan = self.get_object()
        plan.is_active = False
        plan.save(update_fields=["is_active", "updated_at"])
        return Response({"id": str(plan.id), "is_active": False})

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        plan = self.get_object()
        plan.is_active = True
        plan.save(update_fields=["is_active", "updated_at"])
        # Al reanudar, cada activo del plan vuelve a tener su pendiente. Las
        # que quedaron abiertas durante la pausa conservan su fecha: si ya
        # vencieron, aparecen vencidas, que es lo cierto.
        _sync_plan(plan, request.user)
        return Response({"id": str(plan.id), "is_active": True})

    @action(detail=True, methods=["post"], url_path="assign-assets")
    def assign_assets(self, request, pk=None):
        """
        Asigna el plan a varios activos a la vez (D7). Un activo que tenia otro
        plan se cambia a este y su nueva pendiente hereda la fecha de la que se
        anula, como al pasar de "3 TOMAS" a "4 TOMAS".
        """
        plan = self.get_object()
        entrada = AssetIdsSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        activos = entrada.validated_data["asset_ids"]

        if plan.restrict_to_hospital_id:
            ajenos = [a.code for a in activos if a.hospital_id != plan.restrict_to_hospital_id]
            if ajenos:
                raise ValidationError({"asset_ids": (
                    f"El plan es solo para {plan.restrict_to_hospital.name}. "
                    f"No son de ese hospital: {', '.join(ajenos[:10])}."
                )})

        asignados, cambiados, sin_generar = 0, [], []
        with transaction.atomic():
            for asset in activos:
                if asset.plan_id == plan.id:
                    continue
                anterior = asset.plan.name if asset.plan_id else None
                heredada = services.set_asset_plan(asset, plan, request.user)
                if anterior:
                    cambiados.append({"code": asset.code, "from_plan": anterior, "kept_date": heredada})
                asignados += 1
                if asset.status != Asset.Status.ACTIVE:
                    sin_generar.append(asset.code)
        return Response({
            "assigned": asignados,
            "moved": cambiados,
            "inactive": sin_generar,
        })

    @action(detail=True, methods=["post"], url_path="remove-assets")
    def remove_assets(self, request, pk=None):
        """Quita el plan a esos activos: sus pendientes del plan se anulan."""
        plan = self.get_object()
        entrada = AssetIdsSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        quitados = 0
        with transaction.atomic():
            for asset in entrada.validated_data["asset_ids"]:
                if asset.plan_id == plan.id:
                    services.set_asset_plan(asset, None, request.user)
                    quitados += 1
        return Response({"removed": quitados})

    @action(detail=True, methods=["get"])
    def compliance(self, request, pk=None):
        plan = self.get_object()
        today = date.today()
        monthly = []

        for i in range(11, -1, -1):
            ref = today.replace(day=1)
            if i > 0:
                ref = ref - relativedelta(months=i)
            # Por tarea de activo, no por OT: una OT puede llevar varias.
            qs = Task.objects.filter(
                plan_task__plan=plan,
                scheduled_date__year=ref.year,
                scheduled_date__month=ref.month,
            ).exclude(status=Task.Status.CANCELLED)
            total = qs.count()
            completed = qs.filter(status=Task.Status.DONE).count()
            monthly.append({
                "year": ref.year,
                "month": ref.month,
                "total": total,
                "completed": completed,
                "percentage": round(completed / total * 100, 1) if total else None,
            })

        return Response({
            "plan_id": str(plan.id),
            "plan_name": plan.name,
            "monthly": monthly,
        })


# ── Tareas del plan ───────────────────────────────────────────────────────────

class PlanTaskViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
    mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet,
):
    """
    Tareas de un plan (?plan_id=). Crear una abre la pendiente de cada activo
    del plan; desactivarla anula sus pendientes; reactivarla las vuelve a abrir.
    """

    serializer_class = PlanTaskSerializer
    pagination_class = None

    def get_queryset(self):
        qs = _plan_tasks_con_conteos()
        plan_id = self.request.query_params.get("plan_id")
        if plan_id:
            qs = qs.filter(plan_id=plan_id)
        return qs

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAdminOrSup()]
        return [IsAdmin()]

    def destroy(self, request, *args, **kwargs):
        tarea = self.get_object()
        if tarea.occurrences.exists():
            return Response(
                {"detail": (
                    "Esta tarea ya tiene ocurrencias registradas en los activos. "
                    "Desactivala en lugar de eliminarla: se conserva su historial."
                )},
                status=status.HTTP_409_CONFLICT,
            )
        tarea.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="create-occurrence")
    def create_occurrence(self, request, pk=None):
        """Tarea por evento (acta de entrega, prueba anual): la crea el planificador."""
        plan_task = self.get_object()
        entrada = EventOccurrenceSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            tarea = services.create_event_task(
                plan_task,
                entrada.validated_data["asset"],
                entrada.validated_data["scheduled_date"],
                request.user,
            )
        except services.TaskStateError as exc:
            return _error(exc)
        return Response(TaskSerializer(tarea).data, status=status.HTTP_201_CREATED)


# ── Tareas ────────────────────────────────────────────────────────────────────

def _fecha(params, nombre):
    valor = params.get(nombre)
    if not valor:
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise ValidationError({nombre: "Fecha invalida; usa AAAA-MM-DD."}) from None


class TaskViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Tareas pendientes y su historial. Es la lista que el planificador agrupa en
    OTs, como la primera columna del kanban de Fracttal.
    """

    serializer_class = TaskSerializer
    permission_classes = [IsAdminOrSup]

    def get_queryset(self):
        qs = Task.objects.select_related(
            "asset__hospital", "asset__node", "plan_task__plan", "work_order",
        )
        # Hospital o parte del arbol del planificador (apps.users.scope).
        qs = scope.assets(qs, self.request.user, prefix="asset__")
        p = self.request.query_params

        estados = [s for s in p.get("status", "").split(",") if s]
        if estados:
            qs = qs.filter(status__in=estados)
        if p.get("include_inactive") not in ("1", "true"):
            # Las pendientes de un plan pausado o de una tarea desactivada no
            # son trabajo por planificar.
            qs = qs.exclude(
                Q(status=Task.Status.PENDING)
                & (Q(plan_task__is_active=False) | Q(plan_task__plan__is_active=False))
            )

        if p.get("hospital_id"):
            qs = qs.filter(asset__hospital_id=p["hospital_id"])
        if p.get("node_id"):
            qs = qs.filter(asset__node_id__in=AssetNode.subtree_ids(p["node_id"]))
        if p.get("plan_id"):
            qs = qs.filter(plan_task__plan_id=p["plan_id"])
        if p.get("plan_task_id"):
            qs = qs.filter(plan_task_id=p["plan_task_id"])
        if p.get("asset_id"):
            qs = qs.filter(asset_id=p["asset_id"])

        desde, hasta = _fecha(p, "due_after"), _fecha(p, "due_before")
        if desde:
            qs = qs.filter(scheduled_date__gte=desde)
        if hasta:
            qs = qs.filter(scheduled_date__lte=hasta)
        if p.get("overdue") in ("1", "true"):
            qs = qs.filter(
                status__in=Task.OPEN_STATUSES, scheduled_date__lt=timezone.localdate()
            )

        busqueda = p.get("search")
        if busqueda:
            qs = qs.filter(
                Q(asset__code__icontains=busqueda)
                | Q(asset__name__icontains=busqueda)
                | Q(title__icontains=busqueda)
            )
        return qs.order_by("scheduled_date", "asset__code", "id")

    def _responder(self, tarea):
        return Response(TaskSerializer(tarea, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"])
    def reschedule(self, request, pk=None):
        tarea = self.get_object()
        entrada = RescheduleInputSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        try:
            services.reschedule_task(
                tarea, datos["scheduled_date"], datos["cause_id"], request.user, datos["note"]
            )
        except services.TaskStateError as exc:
            return _error(exc)
        return self._responder(tarea)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        tarea = self.get_object()
        entrada = CancelInputSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            services.cancel_task(tarea, entrada.validated_data["note"])
        except services.TaskStateError as exc:
            return _error(exc)
        return self._responder(tarea)

    @action(detail=True, methods=["get"])
    def reschedules(self, request, pk=None):
        """Historial de reprogramaciones: los "Registros" de Fracttal."""
        tarea = self.get_object()
        filas = tarea.reschedules.select_related("cause", "changed_by").order_by("changed_at")
        return Response(TaskRescheduleSerializer(filas, many=True).data)

    @action(detail=False, methods=["post"], url_path="reschedule", url_name="bulk-reschedule")
    def bulk_reschedule(self, request):
        entrada = BulkRescheduleInputSerializer(data=request.data, context={"request": request})
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        try:
            movidas = services.reschedule_tasks(
                datos["task_ids"], datos["scheduled_date"], datos["cause_id"],
                request.user, datos["note"],
            )
        except services.TaskStateError as exc:
            return _error(exc)
        return Response({"rescheduled": movidas})

    @action(detail=False, methods=["post"], url_path="cancel", url_name="bulk-cancel")
    def bulk_cancel(self, request):
        entrada = BulkCancelInputSerializer(data=request.data, context={"request": request})
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        try:
            anuladas = services.cancel_tasks(datos["task_ids"], datos["note"])
        except services.TaskStateError as exc:
            return _error(exc)
        return Response({"cancelled": anuladas})


class RescheduleCauseViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Catalogo de causas de reprogramacion (las 10 del cliente en Fracttal)."""

    serializer_class = RescheduleCauseSerializer
    permission_classes = [IsAdminOrSup]
    pagination_class = None
    queryset = RescheduleCause.objects.filter(is_active=True).order_by("sort_order", "name")
