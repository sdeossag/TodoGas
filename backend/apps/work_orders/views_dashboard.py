from datetime import timedelta

from dateutil.relativedelta import relativedelta
from django.core.cache import cache
from django.db.models import Min, Q, Subquery, OuterRef
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdminOrSup

from .dashboard import (
    calculate_assets_without_maintenance,
    calculate_compliance_percentage,
    calculate_mttr,
    calculate_ots_by_status,
    calculate_ots_by_technician,
    calculate_overdue_count,
)


class DashboardView(APIView):
    """GET /api/dashboard/ — todos los KPIs en un solo request."""

    permission_classes = [IsAdminOrSup]

    def get(self, request):
        hospital_id = request.query_params.get("hospital_id") or None
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
            "ots_by_technician": calculate_ots_by_technician(days=days),
            "assets_without_maintenance": calculate_assets_without_maintenance(
                hospital_id=hospital_id
            )[:10],
        }

        cache.set(cache_key, data, timeout=300)
        return Response(data)


class DashboardComplianceHistoryView(APIView):
    """GET /api/dashboard/compliance-history/ — cumplimiento mes a mes."""

    permission_classes = [IsAdminOrSup]

    def get(self, request):
        hospital_id = request.query_params.get("hospital_id") or None
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

    permission_classes = [IsAdminOrSup]

    def get(self, request):
        from apps.assets.models import Asset
        from apps.maintenance.models import MaintenancePlan

        hospital_id = request.query_params.get("hospital_id") or None
        today = timezone.now().date()
        due_soon_threshold = today + timedelta(days=30)

        assets = Asset.objects.filter(status=Asset.Status.ACTIVE)
        if hospital_id:
            assets = assets.filter(hospital_id=hospital_id)

        total = assets.count()

        assets_with_active_plan_ids = (
            Asset.objects.filter(maintenance_plans__is_active=True)
            .values_list("id", flat=True)
            .distinct()
        )
        no_plan = assets.exclude(id__in=assets_with_active_plan_ids).count()

        min_due_subq = (
            MaintenancePlan.objects.filter(assets=OuterRef("pk"), is_active=True)
            .values("assets")
            .annotate(min_due=Min("next_due_date"))
            .values("min_due")[:1]
        )

        with_plan = (
            assets.filter(id__in=assets_with_active_plan_ids)
            .annotate(next_pm_date=Subquery(min_due_subq))
        )

        overdue = with_plan.filter(next_pm_date__lt=today).count()
        due_soon = with_plan.filter(
            next_pm_date__gte=today, next_pm_date__lte=due_soon_threshold
        ).count()
        on_time = with_plan.filter(
            Q(next_pm_date__gt=due_soon_threshold) | Q(next_pm_date__isnull=True)
        ).count()

        return Response(
            {
                "on_time": on_time,
                "due_soon": due_soon,
                "overdue": overdue,
                "no_plan": no_plan,
                "total": total,
            }
        )
