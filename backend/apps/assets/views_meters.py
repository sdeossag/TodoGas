from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users import scope
from apps.users.permissions import IsAdmin, IsAdminOrSup

from .meters import recompute_accumulated, record_manual
from .models import Meter, MeterReading, MeterUnit
from .serializers_meters import (
    MeterReadingSerializer,
    MeterSerializer,
    MeterUnitSerializer,
)


class MeterUnitViewSet(viewsets.ModelViewSet):
    """
    /api/meter-units/ — unidades de medidor (las seis del cliente). Todos las
    leen; el administrador las agrega o corrige. No se borran: se desactivan.
    """

    serializer_class = MeterUnitSerializer
    pagination_class = None
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsAdmin()]

    def get_queryset(self):
        qs = MeterUnit.objects.order_by("sort_order", "name")
        if self.request.query_params.get("active") in ("1", "true"):
            qs = qs.filter(is_active=True)
        return qs


class MeterViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                   viewsets.GenericViewSet):
    """
    /api/meters/?asset_id= — medidores de un equipo con su ultima lectura y
    como van sus activadores. Se crean solos con la primera lectura del
    checklist; el supervisor puede agregar uno para registrar a mano.
    """

    serializer_class = MeterSerializer
    pagination_class = None

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsAdminOrSup()]

    def get_queryset(self):
        qs = scope.assets(
            Meter.objects.select_related("asset", "unit"), self.request.user, prefix="asset__",
        )
        if asset_id := self.request.query_params.get("asset_id"):
            qs = qs.filter(asset_id=asset_id)
        return qs.order_by("unit__sort_order", "unit__name")


class MeterReadingViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin,
                          viewsets.GenericViewSet):
    """
    /api/meter-readings/?meter_id= | ?asset_id= — historial de lecturas.
    POST registra una lectura a mano (administrador o supervisor). Solo se
    borran las manuales: las del checklist se corrigen en la respuesta.
    """

    serializer_class = MeterReadingSerializer

    def get_permissions(self):
        if self.action == "list":
            return [IsAuthenticated()]
        return [IsAdminOrSup()]

    def get_queryset(self):
        qs = scope.assets(
            MeterReading.objects.select_related("meter__unit", "recorded_by", "task__work_order"),
            self.request.user, prefix="meter__asset__",
        )
        p = self.request.query_params
        if p.get("meter_id"):
            qs = qs.filter(meter_id=p["meter_id"])
        if p.get("asset_id"):
            qs = qs.filter(meter__asset_id=p["asset_id"])
        return qs.order_by("-read_at", "-created_at")

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        lectura = record_manual(
            d["meter"], d["value"], d.get("read_at"),
            user=request.user, is_reset=d.get("is_reset", False), note=d.get("note", ""),
        )
        return Response(self.get_serializer(lectura).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        lectura = self.get_object()
        if lectura.source != MeterReading.Source.MANUAL:
            return Response(
                {"detail": "Esta lectura viene del checklist: se corrige en la respuesta de la OT."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if lectura.triggered_tasks.exists():
            return Response(
                {"detail": "Esta lectura abrio una tarea; no se puede borrar."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        meter = lectura.meter
        lectura.delete()
        recompute_accumulated(meter)
        return Response(status=status.HTTP_204_NO_CONTENT)
