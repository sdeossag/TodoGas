
from dateutil.relativedelta import relativedelta
from django.core.cache import cache
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import TienePermiso
from apps.users.models import User

from .dashboard import (
    calculate_assets_status,
    calculate_assets_without_maintenance,
    calculate_compliance_percentage,
    calculate_mttr,
    calculate_open_findings,
    calculate_ots_by_kind,
    calculate_ots_by_status,
    calculate_ots_by_technician,
    calculate_overdue_count,
    calculate_pending_by_month,
)


def _hospital_del_tablero(request):
    """
    El hospital que pide el tablero, o el del usuario si esta limitado a uno
    (apps.users.scope): un supervisor de una clinica no ve los indicadores de
    todas. Los indicadores van por hospital, no por piso.
    """
    user = request.user
    if user.role != User.Role.ADMIN and user.hospital_id:
        return str(user.hospital_id)
    return request.query_params.get("hospital_id") or None


class DashboardView(APIView):
    """GET /api/dashboard/ — todos los KPIs en un solo request."""

    permission_classes = [TienePermiso("reportes.ver")]

    def get(self, request):
        hospital_id = _hospital_del_tablero(request)
        days = int(request.query_params.get("days", 30))

        cache_key = f"dashboard_{hospital_id}_{days}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        data = {
            "compliance": calculate_compliance_percentage(hospital_id=hospital_id),
            "mttr": calculate_mttr(hospital_id=hospital_id, days=days),
            "overdue": calculate_overdue_count(hospital_id=hospital_id),
            "ots_by_status": calculate_ots_by_status(hospital_id=hospital_id, days=days),
            "ots_by_kind": calculate_ots_by_kind(hospital_id=hospital_id, days=days),
            "ots_by_technician": calculate_ots_by_technician(days=days),
            "pending_by_month": calculate_pending_by_month(hospital_id=hospital_id),
            "open_findings": calculate_open_findings(hospital_id=hospital_id),
            "assets_without_maintenance": calculate_assets_without_maintenance(
                hospital_id=hospital_id
            )[:10],
        }

        cache.set(cache_key, data, timeout=300)
        return Response(data)


class DashboardComplianceHistoryView(APIView):
    """GET /api/dashboard/compliance-history/ — cumplimiento mes a mes."""

    permission_classes = [TienePermiso("reportes.ver")]

    def get(self, request):
        hospital_id = _hospital_del_tablero(request)
        months = int(request.query_params.get("months", 12))

        today = timezone.now().date()
        result = []
        for i in range(months - 1, -1, -1):
            ref = today.replace(day=1) - relativedelta(months=i)
            kpi = calculate_compliance_percentage(
                month=ref.month, year=ref.year, hospital_id=hospital_id
            )
            result.append(kpi)

        return Response(result)


class DashboardAssetsStatusView(APIView):
    """GET /api/dashboard/assets-status/ — conteo de activos por estado de mantenimiento."""

    permission_classes = [TienePermiso("reportes.ver")]

    def get(self, request):
        return Response(calculate_assets_status(hospital_id=_hospital_del_tablero(request)))
