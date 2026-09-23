from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.users import scope
from apps.users.permissions import IsAdmin, IsAdminOrSup, IsAdminOrSupOrClient

from .contracts import hoy, hospitales_sin_contrato, renovado, resumen
from .models import Contract
from .serializers_contracts import ContractSerializer


class ContractViewSet(viewsets.ModelViewSet):
    """
    /api/contracts/ — contratos de mantenimiento y garantias.

    Los carga y corrige el administrador (es la capa comercial). El supervisor
    y la cuenta del hospital los consultan, cada uno en su alcance; el
    hospital tambien descarga el documento (decision del 2026-09-23).

    Filtros: hospital_id, kind, status (ACTIVE incluye los por vencer,
    EXPIRING, EXPIRED, UPCOMING), asset_id, search.
    """

    serializer_class = ContractSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAdminOrSupOrClient()]
        if self.action == "summary":
            return [IsAdminOrSup()]
        return [IsAdmin()]

    def get_queryset(self):
        qs = scope.contracts(
            Contract.objects.select_related("hospital", "node", "created_by").prefetch_related("assets"),
            self.request.user,
        )
        p = self.request.query_params
        if p.get("hospital_id"):
            qs = qs.filter(hospital_id=p["hospital_id"])
        if p.get("kind"):
            qs = qs.filter(kind=p["kind"])
        if p.get("asset_id"):
            qs = qs.filter(asset_links__asset_id=p["asset_id"])
        if p.get("search"):
            qs = qs.filter(Q(name__icontains=p["search"]) | Q(description__icontains=p["search"]))
        estado = p.get("status")
        if estado:
            dia = hoy()
            aviso = dia + timedelta(days=Contract.EXPIRING_DAYS)
            qs = {
                "ACTIVE": qs.filter(Contract.active_q(dia)),
                "EXPIRING": qs.filter(Contract.active_q(dia), end_date__lte=aviso),
                "EXPIRED": qs.filter(end_date__lt=dia),
                "UPCOMING": qs.filter(start_date__gt=dia),
            }.get(estado, qs)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_destroy(self, instance):
        # ContractAsset protege al contrato: se sueltan los equipos primero.
        with transaction.atomic():
            instance.asset_links.all().delete()
            instance.delete()

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """
        Para el tablero: lo que vence en 60 dias, lo vencido en los ultimos 30
        sin renovar, y los hospitales activos sin contrato vigente.
        """
        dia = hoy()
        base = scope.contracts(Contract.objects.select_related("hospital"), request.user)
        por_vencer = base.filter(
            Contract.active_q(dia), end_date__lte=dia + timedelta(days=Contract.EXPIRING_DAYS),
        ).order_by("end_date")
        vencidos = base.filter(
            end_date__lt=dia, end_date__gte=dia - timedelta(days=30),
        ).order_by("-end_date")

        def fila(c):
            return {**resumen(c, dia), "hospital_id": str(c.hospital_id), "hospital_name": c.hospital.name}

        sin_contrato = scope.hospitals(hospitales_sin_contrato(dia), request.user)
        return Response({
            "expiring": [fila(c) for c in por_vencer],
            "recently_expired": [fila(c) for c in vencidos if not renovado(c)],
            "hospitals_without_contract": [
                {"id": str(h.id), "name": h.name} for h in sin_contrato.order_by("name")
            ],
        })
