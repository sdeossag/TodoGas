import hashlib
from datetime import timedelta

from dateutil.relativedelta import relativedelta
from django.db.models import Avg, Count, ExpressionWrapper, F, Min, Q, Subquery, OuterRef
from django.db.models.fields import DurationField
from django.utils import timezone

from apps.users.models import User

from .models import WorkOrder


def calculate_compliance_percentage(month=None, year=None, hospital_id=None):
    today = timezone.now().date()
    if month is None:
        month = today.month
    if year is None:
        year = today.year

    qs = WorkOrder.objects.filter(
        task_type=WorkOrder.TaskType.PREVENTIVE,
        scheduled_date__year=year,
        scheduled_date__month=month,
    )
    if hospital_id:
        qs = qs.filter(asset__hospital_id=hospital_id)

    generated = qs.count()
    completed = (
        qs.filter(
            status=WorkOrder.Status.COMPLETED,
            completed_at__isnull=False,
        )
        .filter(completed_at__date__lte=F("scheduled_date") + timedelta(days=1))
        .count()
    )

    percentage = round((completed / generated) * 100, 1) if generated else 0.0
    return {
        "percentage": percentage,
        "completed": completed,
        "generated": generated,
        "month": f"{year}-{month:02d}",
    }


def calculate_mttr(hospital_id=None, days=30):
    since = timezone.now() - timedelta(days=days)
    qs = WorkOrder.objects.filter(
        task_type=WorkOrder.TaskType.CORRECTIVE,
        status=WorkOrder.Status.COMPLETED,
        started_at__isnull=False,
        completed_at__isnull=False,
        completed_at__gte=since,
    )
    if hospital_id:
        qs = qs.filter(asset__hospital_id=hospital_id)

    sample_size = qs.count()
    if not sample_size:
        return {"mttr_hours": 0.0, "sample_size": 0}

    duration_expr = ExpressionWrapper(
        F("completed_at") - F("started_at"),
        output_field=DurationField(),
    )
    result = qs.annotate(duration=duration_expr).aggregate(avg_duration=Avg("duration"))
    avg_td = result["avg_duration"]
    mttr_hours = round(avg_td.total_seconds() / 3600, 2) if avg_td else 0.0
    return {"mttr_hours": mttr_hours, "sample_size": sample_size}


def calculate_overdue_count(hospital_id=None):
    today = timezone.now().date()
    qs = WorkOrder.objects.filter(scheduled_date__lt=today).exclude(
        status__in=[WorkOrder.Status.COMPLETED, WorkOrder.Status.CANCELLED]
    )
    if hospital_id:
        qs = qs.filter(asset__hospital_id=hospital_id)
    count = qs.count()
    critical = qs.filter(priority=WorkOrder.Priority.HIGH).count()
    return {"count": count, "critical": critical}


def calculate_ots_by_status(hospital_id=None, days=30):
    since = timezone.now() - timedelta(days=days)
    qs = WorkOrder.objects.filter(created_at__gte=since)
    if hospital_id:
        qs = qs.filter(asset__hospital_id=hospital_id)

    result = {s.value: 0 for s in WorkOrder.Status}
    for item in qs.values("status").annotate(cnt=Count("id")):
        result[item["status"]] = item["cnt"]
    return result


def calculate_ots_by_technician(days=30):
    since = timezone.now() - timedelta(days=days)
    today = timezone.now().date()

    techs = User.objects.filter(role=User.Role.TEC, is_active=True)
    result = []
    for tech in techs:
        assigned = WorkOrder.objects.filter(assigned_to=tech, created_at__gte=since).count()
        completed = WorkOrder.objects.filter(
            assigned_to=tech,
            status=WorkOrder.Status.COMPLETED,
            completed_at__gte=since,
        ).count()
        overdue = (
            WorkOrder.objects.filter(assigned_to=tech, scheduled_date__lt=today)
            .exclude(status__in=[WorkOrder.Status.COMPLETED, WorkOrder.Status.CANCELLED])
            .count()
        )
        result.append(
            {
                "technician_id": str(tech.id),
                "technician_name": f"{tech.first_name} {tech.last_name}",
                "assigned": assigned,
                "completed": completed,
                "overdue": overdue,
            }
        )
    result.sort(key=lambda x: x["overdue"], reverse=True)
    return result


def calculate_assets_without_maintenance(days=90, hospital_id=None):
    from apps.assets.models import Asset

    since = timezone.now() - timedelta(days=days)
    today = timezone.now().date()

    assets_with_plans = Asset.objects.filter(
        maintenance_plans__is_active=True, status=Asset.Status.ACTIVE
    ).distinct()
    if hospital_id:
        assets_with_plans = assets_with_plans.filter(hospital_id=hospital_id)

    recently_maintained = WorkOrder.objects.filter(
        status=WorkOrder.Status.COMPLETED,
        completed_at__gte=since,
    ).values_list("asset_id", flat=True)

    assets_no_pm = assets_with_plans.exclude(id__in=recently_maintained).select_related("hospital")

    result = []
    for asset in assets_no_pm:
        last_wo = (
            WorkOrder.objects.filter(
                asset=asset,
                status=WorkOrder.Status.COMPLETED,
                completed_at__isnull=False,
            )
            .order_by("-completed_at")
            .first()
        )
        days_since = (
            (today - last_wo.completed_at.date()).days
            if last_wo and last_wo.completed_at
            else None
        )
        result.append(
            {
                "asset_id": str(asset.id),
                "asset_name": asset.name,
                "asset_code": asset.code,
                "hospital_name": asset.hospital.name,
                "days_since_last_pm": days_since,
            }
        )
    return result


def compute_wo_integrity_hash(work_order):
    """Same algorithm used in reports/generator.py when a WO is completed."""
    content = f"{work_order.id}{work_order.wo_number}{work_order.completed_at}"
    return hashlib.sha256(content.encode()).hexdigest()
