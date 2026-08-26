from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import User
from apps.users.permissions import IsAdmin, IsAdminOrSup, IsClient

from .models import Asset, AssetCustomField, AssetNode, Hospital
from .serializers import (
    AssetCreateUpdateSerializer,
    AssetCustomFieldSerializer,
    AssetListSerializer,
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
        qs = Hospital.objects.all()
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


class AssetNodeViewSet(viewsets.ModelViewSet):
    queryset = AssetNode.objects.select_related("hospital", "parent")
    serializer_class = AssetNodeSerializer

    def get_permissions(self):
        return [IsAdminOrSup()]

    def get_queryset(self):
        qs = AssetNode.objects.select_related("hospital", "parent")
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

    def perform_update(self, serializer):
        old_name = serializer.instance.name
        instance = serializer.save()
        if old_name != instance.name:
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
        roots = AssetNode.objects.filter(
            hospital_id=hospital_id,
            parent=None,
            is_active=True,
        ).order_by("sort_order", "name")
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
        user = self.request.user
        qs = Asset.objects.select_related(
            "hospital", "node", "node__parent"
        ).prefetch_related(
            "custom_field_values__field",
            "maintenance_plans",
            "work_orders",
        )

        if user.role == User.Role.CLI:
            qs = qs.filter(hospital=user.hospital)

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
            qs = qs.filter(node_id=node_id)

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(code__icontains=search)
                | Q(serial_number__icontains=search)
                | Q(model__icontains=search)
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

        assets = Asset.objects.filter(hospital=hospital)
        total_assets = assets.count()

        status_counts = {}
        for s in Asset.Status:
            status_counts[s.value] = assets.filter(status=s).count()

        from apps.work_orders.models import WorkOrder
        recent_wos = WorkOrder.objects.filter(
            asset__hospital=hospital,
            status=WorkOrder.Status.COMPLETED,
        ).order_by('-completed_at')[:5]

        wo_data = [
            {
                'id': str(wo.id),
                'wo_number': wo.wo_number,
                'title': wo.title,
                'asset_name': wo.asset.name,
                'completed_at': wo.completed_at.isoformat() if wo.completed_at else None,
            }
            for wo in recent_wos
        ]

        from apps.reports.models import GeneratedReport
        reports = GeneratedReport.objects.filter(
            work_order__asset__hospital=hospital
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
                'generated_at': r.generated_at.isoformat(),
                'download_url': url,
                'wo_number': r.work_order.wo_number if r.work_order else None,
            })

        return Response({
            'hospital': {
                'id': str(hospital.id),
                'name': hospital.name,
                'city': hospital.city,
            },
            'total_assets': total_assets,
            'assets_by_status': status_counts,
            'recent_work_orders': wo_data,
            'pending_reports': reports_data,
        })
