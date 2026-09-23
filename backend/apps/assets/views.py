from django.db.models import Count, IntegerField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users import scope
from apps.users.models import User
from apps.users.permissions import IsAdmin, IsAdminOrSup, IsClient

from .models import Asset, AssetCustomField, AssetNode, Hospital
from .serializers import (
    AssetCreateUpdateSerializer,
    AssetCustomFieldSerializer,
    AssetListSerializer,
    AssetNodeCreateUpdateSerializer,
    AssetNodeSerializer,
    AssetNodeTreeSerializer,
    AssetSerializer,
    HospitalListSerializer,
    HospitalSerializer,
)
from .utils import generate_asset_qr, get_or_create_qr_url


class HospitalViewSet(viewsets.ModelViewSet):
    queryset = Hospital.objects.all()

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "toggle_active"):
            return [IsAdmin()]
        return [IsAdminOrSup()]

    def get_serializer_class(self):
        if self.action == "list":
            return HospitalListSerializer
        return HospitalSerializer

    def get_queryset(self):
        qs = scope.hospitals(Hospital.objects.all(), self.request.user)
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        return qs

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=True, methods=["post"], url_path="toggle-active")
    def toggle_active(self, request, pk=None):
        hospital = self.get_object()
        hospital.is_active = not hospital.is_active
        hospital.save(update_fields=["is_active"])
        return Response({"id": str(hospital.id), "is_active": hospital.is_active})


def _conteo_por_nodo(modelo, campo):
    """Cuantas filas de `modelo` apuntan al nodo por `campo`, como subconsulta."""
    filas = (
        modelo.objects.filter(**{campo: OuterRef("pk")})
        .order_by()
        .values(campo)
        .annotate(n=Count("pk"))
        .values("n")
    )
    return Coalesce(Subquery(filas, output_field=IntegerField()), Value(0))


class AssetNodeViewSet(viewsets.ModelViewSet):
    queryset = AssetNode.objects.select_related("hospital", "parent")
    serializer_class = AssetNodeSerializer

    def get_permissions(self):
        return [IsAdminOrSup()]

    def get_serializer_class(self):
        # Escribir con AssetNodeSerializer era imposible: sus campos `hospital`
        # y `parent` son SerializerMethodField (solo lectura), asi que el POST
        # los descartaba y el INSERT reventaba con un 500.
        if self.action in ("create", "update", "partial_update"):
            return AssetNodeCreateUpdateSerializer
        return AssetNodeSerializer

    def create(self, request, *args, **kwargs):
        # La respuesta se devuelve con el serializer de lectura, para que el
        # cliente reciba hospital/parent anidados y el `path` ya materializado,
        # igual que en un GET.
        escritura = self.get_serializer(data=request.data)
        escritura.is_valid(raise_exception=True)
        nodo = escritura.save()
        return Response(
            AssetNodeSerializer(nodo).data, status=status.HTTP_201_CREATED
        )

    def destroy(self, request, *args, **kwargs):
        nodo = self.get_object()
        # on_delete=PROTECT en assets y en los hijos: sin esto, borrar un nodo
        # con contenido salia como ProtectedError, es decir otro 500.
        if nodo.children.exists():
            return Response(
                {"detail": "No se puede eliminar: la ubicación tiene "
                           "sububicaciones. Elimínalas o muévelas primero."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if nodo.assets.exists():
            return Response(
                {"detail": "No se puede eliminar: hay activos en esta ubicación. "
                           "Muévelos antes de eliminarla."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        # Subconsultas y no dos Count() con join: contar hijos y activos a la
        # vez por join multiplica filas (hijos x activos) antes de agrupar.
        # Antes children_count lanzaba ademas una consulta por cada nodo.
        qs = AssetNode.objects.select_related("hospital", "parent").annotate(
            children_total=_conteo_por_nodo(AssetNode, "parent"),
            asset_total=_conteo_por_nodo(Asset, "node"),
        )
        qs = scope.asset_nodes(qs, self.request.user)
        hospital_id = self.request.query_params.get("hospital_id")
        if hospital_id:
            qs = qs.filter(hospital_id=hospital_id)
        return qs

    def list(self, request, *args, **kwargs):
        hospital_id = request.query_params.get("hospital_id")
        if not hospital_id:
            return Response(
                {"detail": "Se requiere el parámetro hospital_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().list(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        parcial = kwargs.pop("partial", False)
        instancia = self.get_object()
        escritura = self.get_serializer(instancia, data=request.data, partial=parcial)
        escritura.is_valid(raise_exception=True)
        self.perform_update(escritura)
        return Response(AssetNodeSerializer(escritura.instance).data)

    def perform_update(self, serializer):
        # Se compara el path y no solo el nombre: ahora que `parent` es
        # editable, mover un nodo de sitio tambien cambia la ruta de todos sus
        # descendientes, y antes esas rutas se quedaban obsoletas.
        old_path = serializer.instance.path
        instance = serializer.save()
        if old_path != instance.path:
            self._recalculate_children_paths(instance)

    def _recalculate_children_paths(self, node):
        for child in node.children.all():
            child.path = f"{node.path}/{child.name}"
            child.save(update_fields=["path"])
            self._recalculate_children_paths(child)

    @action(detail=False, methods=["get"], url_path="tree")
    def tree(self, request):
        hospital_id = request.query_params.get("hospital_id")
        if not hospital_id:
            return Response(
                {"detail": "Se requiere el parámetro hospital_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        visibles = scope.asset_nodes(
            AssetNode.objects.filter(hospital_id=hospital_id, is_active=True), request.user
        )
        # Limitado a una parte del arbol, su raiz es el nodo que se le asigno.
        user = request.user
        if user.scope_node_id and visibles.filter(pk=user.scope_node_id).exists():
            roots = visibles.filter(pk=user.scope_node_id)
        else:
            roots = visibles.filter(parent=None).order_by("sort_order", "name")
        serializer = AssetNodeTreeSerializer(roots, many=True)
        return Response(serializer.data)


class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.select_related("hospital", "node")

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        if self.action == "decommission":
            return [IsAdmin()]
        return [IsAdminOrSup()]

    def get_serializer_class(self):
        if self.action == "list":
            return AssetListSerializer
        if self.action in ("create", "update", "partial_update"):
            return AssetCreateUpdateSerializer
        return AssetSerializer

    def get_queryset(self):
        from datetime import timedelta

        from django.db.models import OuterRef, Subquery
        from django.utils import timezone

        from apps.maintenance.models import Task

        user = self.request.user
        qs = Asset.objects.select_related(
            "hospital", "node", "node__parent", "plan"
        ).prefetch_related(
            "custom_field_values__field",
        )

        # Proxima fecha de mantenimiento y ultimo mantenimiento como subconsultas
        # en lugar de tres queries por activo en el serializer (N+1). Ademas
        # `_next_due` es lo que hace filtrable maintenance_status en el servidor:
        # antes se calculaba en el cliente y por eso AssetsPage tenia que traer
        # todos los activos para poder filtrar por color.
        next_due_sq = (
            Task.objects
            .filter(Task.next_maintenance_q(), asset=OuterRef("pk"))
            .order_by("scheduled_date")
            .values("scheduled_date")[:1]
        )
        last_maint_sq = (
            Task.objects
            .filter(asset=OuterRef("pk"), status=Task.Status.DONE)
            .order_by("-completed_at")
            .values("completed_at")[:1]
        )
        qs = qs.annotate(
            _next_due=Subquery(next_due_sq),
            _last_maint=Subquery(last_maint_sq),
        )

        # Hospital o parte del arbol del usuario (apps.users.scope).
        qs = scope.assets(qs, user)

        hospital_id = self.request.query_params.get("hospital_id")
        if hospital_id:
            qs = qs.filter(hospital_id=hospital_id)

        asset_status = self.request.query_params.get("status")
        if asset_status:
            qs = qs.filter(status=asset_status)

        asset_type = self.request.query_params.get("asset_type")
        if asset_type:
            qs = qs.filter(asset_type=asset_type)

        node_id = self.request.query_params.get("node_id")
        if node_id:
            # Por defecto la ubicacion exacta, como en /activos. Al asignar un
            # plan a "todo el Piso 3" hace falta tambien su sububicacion.
            if self.request.query_params.get("include_sublocations") in ("1", "true"):
                qs = qs.filter(node_id__in=AssetNode.subtree_ids(node_id))
            else:
                qs = qs.filter(node_id=node_id)

        plan_id = self.request.query_params.get("plan_id")
        if plan_id == "none":
            qs = qs.filter(plan__isnull=True)
        elif plan_id:
            qs = qs.filter(plan_id=plan_id)

        # RF-AC-07: filtro por estado de mantenimiento (el "color" del activo).
        # Mismas fronteras que AssetListSerializer.get_maintenance_status para
        # que el filtro y lo que se pinta no puedan divergir: ambos derivan de
        # `_next_due`.
        maintenance_status = self.request.query_params.get("maintenance_status")
        if maintenance_status:
            today = timezone.localdate()
            soon = today + timedelta(days=15)
            if maintenance_status == "no_plan":
                qs = qs.filter(_next_due__isnull=True)
            elif maintenance_status == "overdue":
                qs = qs.filter(_next_due__lt=today)
            elif maintenance_status == "due_soon":
                qs = qs.filter(_next_due__gte=today, _next_due__lte=soon)
            elif maintenance_status == "on_time":
                qs = qs.filter(_next_due__gt=soon)

        search = self.request.query_params.get("search")
        if search:
            # RF-AC-05: la busqueda cubre nombre, codigo interno, numero de
            # serie, modelo, marca y nombre del hospital. Marca y hospital
            # faltaban. Los seis campos tienen indice GIN trigram sobre
            # Upper(campo), que es la forma en que Django compila icontains.
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(code__icontains=search)
                | Q(serial_number__icontains=search)
                | Q(model__icontains=search)
                | Q(manufacturer__icontains=search)
                | Q(hospital__name__icontains=search)
            )

        return qs

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Generate QR data URL in-memory (not persisted until S3 is configured in Sprint 6)
        if not instance.qr_code:
            instance.qr_code = get_or_create_qr_url(instance)
        serializer = AssetSerializer(instance)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=True, methods=["get"], url_path="tasks")
    def tasks(self, request, pk=None):
        """
        Tareas del activo: las abiertas (la proxima fecha de cada tarea de su
        plan) y el historial con las tres fechas de Fracttal, calculada,
        programada y de realizacion, enlazado a su OT y a su acta.
        """
        from apps.maintenance.models import Task
        from apps.maintenance.serializers import TaskSerializer

        asset = self.get_object()
        tareas = (
            Task.objects.filter(asset=asset)
            .select_related("asset__hospital", "asset__node", "plan_task__plan", "work_order")
            .prefetch_related("work_order__reports")
        )
        abiertas = tareas.filter(status__in=Task.OPEN_STATUSES).order_by("scheduled_date")
        historial = tareas.exclude(status__in=Task.OPEN_STATUSES).order_by(
            "-scheduled_date", "-created_at"
        )
        contexto = {"request": request, "with_reports": True}
        return Response({
            "open": TaskSerializer(abiertas, many=True, context=contexto).data,
            "history": TaskSerializer(historial, many=True, context=contexto).data,
        })

    @action(detail=True, methods=["get"], url_path="qr-label", permission_classes=[IsAdminOrSup])
    def qr_label(self, request, pk=None):
        asset = self.get_object()
        png_bytes = generate_asset_qr(asset)
        from django.http import HttpResponse
        return HttpResponse(png_bytes, content_type="image/png")

    @action(detail=True, methods=["post"], url_path="decommission", permission_classes=[IsAdmin])
    def decommission(self, request, pk=None):
        asset = self.get_object()
        asset.status = Asset.Status.DECOMMISSIONED
        asset.save(update_fields=["status"])
        return Response({"id": str(asset.id), "status": asset.status})


class AssetCustomFieldViewSet(viewsets.ModelViewSet):
    queryset = AssetCustomField.objects.all()
    serializer_class = AssetCustomFieldSerializer

    def get_permissions(self):
        return [IsAdmin()]

    def get_queryset(self):
        qs = AssetCustomField.objects.all()
        asset_type_name = self.request.query_params.get("asset_type_name")
        if asset_type_name:
            qs = qs.filter(asset_type_name=asset_type_name)
        return qs


class ClientPortalView(APIView):
    """
    GET /api/client-portal/summary/
    Resumen del hospital del usuario CLI.
    """
    permission_classes = [IsClient]

    def get(self, request):
        user = request.user
        hospital = user.hospital
        if not hospital:
            return Response(
                {'detail': 'Usuario CLI sin hospital asignado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Todo por apps.users.scope: la cuenta puede estar limitada a un piso.
        assets = scope.assets(Asset.objects.all(), user)
        total_assets = assets.count()

        status_counts = {}
        for s in Asset.Status:
            status_counts[s.value] = assets.filter(status=s).count()

        from apps.work_orders.models import WorkOrder
        recent_wos = scope.work_orders(
            WorkOrder.objects.filter(status=WorkOrder.Status.COMPLETED), user
        ).prefetch_related('tasks__asset').order_by('-completed_at')[:5]

        wo_data = [
            {
                'id': str(wo.id),
                'wo_number': wo.wo_number,
                'wo_code': wo.wo_code,
                'title': wo.title,
                'status': wo.status,
                # Una visita puede intervenir varios activos (decision D4).
                'assets': [
                    {'id': str(t.asset_id), 'name': t.asset.name}
                    for t in wo.tasks.all() if t.status != 'CANCELLED'
                ],
                'completed_at': wo.completed_at.isoformat() if wo.completed_at else None,
            }
            for wo in recent_wos
        ]

        from apps.reports.models import GeneratedReport
        reports = scope.work_orders(
            GeneratedReport.objects.filter(work_order__status=WorkOrder.Status.COMPLETED),
            user, prefix="work_order__",
        ).select_related('work_order').order_by('-generated_at')[:10]

        from django.core.files.storage import default_storage
        reports_data = []
        for r in reports:
            try:
                url = default_storage.url(r.file_url)
            except Exception:
                url = r.file_url
            reports_data.append({
                'id': str(r.id),
                'title': r.title,
                'generated_at': r.generated_at.isoformat(),
                'download_url': url,
                'file_hash': r.file_hash,
                'wo_number': r.work_order.wo_number if r.work_order else None,
                'wo_code': r.work_order.wo_code if r.work_order else None,
            })

        return Response({
            'hospital': {
                'id': str(hospital.id),
                'name': hospital.name,
                'city': hospital.city,
                'address': hospital.address,
            },
            'total_assets': total_assets,
            'assets_by_status': status_counts,
            'recent_work_orders': wo_data,
            'recent_reports': reports_data,
            # Alias historico: el APK publicado lee 'pending_reports'.
            'pending_reports': reports_data,
        })
