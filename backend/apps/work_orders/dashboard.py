from datetime import timedelta

from dateutil.relativedelta import relativedelta
from django.db.models import Avg, Count, ExpressionWrapper, F, Q, Subquery, OuterRef
from django.db.models.fields import DurationField
from django.utils import timezone

from apps.users.models import User

from .models import WorkOrder


def calculate_compliance_percentage(month=None, year=None, hospital_id=None):
    today = timezone.localdate()
    if month is None:
        month = today.month
    if year is None:
        year = today.year

    from apps.maintenance.task_types import codes_counting_as

    # Los tipos que el catalogo marca como preventivos (Cambio de filtros, Calibracion...).
    qs = WorkOrder.objects.filter(
        task_type__in=codes_counting_as("PREVENTIVE"),
        scheduled_date__year=year,
        scheduled_date__month=month,
    )
    if hospital_id:
        qs = qs.filter(hospital_id=hospital_id)

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
    from apps.maintenance.task_types import codes_counting_as

    qs = WorkOrder.objects.filter(
        task_type__in=codes_counting_as("CORRECTIVE"),
        status=WorkOrder.Status.COMPLETED,
        started_at__isnull=False,
        completed_at__isnull=False,
        completed_at__gte=since,
    )
    if hospital_id:
        qs = qs.filter(hospital_id=hospital_id)

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
    today = timezone.localdate()
    qs = WorkOrder.objects.filter(scheduled_date__lt=today).exclude(
        status__in=[WorkOrder.Status.COMPLETED, WorkOrder.Status.CANCELLED]
    )
    if hospital_id:
        qs = qs.filter(hospital_id=hospital_id)
    count = qs.count()
    critical = qs.filter(priority=WorkOrder.Priority.HIGH).count()
    return {"count": count, "critical": critical}


def calculate_ots_by_status(hospital_id=None, days=30):
    since = timezone.now() - timedelta(days=days)
    qs = WorkOrder.objects.filter(created_at__gte=since)
    if hospital_id:
        qs = qs.filter(hospital_id=hospital_id)

    result = {s.value: 0 for s in WorkOrder.Status}
    for item in qs.values("status").annotate(cnt=Count("id")):
        result[item["status"]] = item["cnt"]
    return result


def calculate_ots_by_technician(days=30):
    since = timezone.now() - timedelta(days=days)
    today = timezone.localdate()
    abiertas = ~Q(assigned_work_orders__status__in=[
        WorkOrder.Status.COMPLETED, WorkOrder.Status.CANCELLED,
    ])

    # Una sola consulta: con tres conteos por tecnico el costo crecia con la
    # plantilla. distinct porque los tres conteos recorren el mismo join.
    techs = User.objects.filter(role=User.Role.TEC, is_active=True).annotate(
        assigned=Count(
            "assigned_work_orders",
            filter=Q(assigned_work_orders__created_at__gte=since),
            distinct=True,
        ),
        completed=Count(
            "assigned_work_orders",
            filter=Q(
                assigned_work_orders__status=WorkOrder.Status.COMPLETED,
                assigned_work_orders__completed_at__gte=since,
            ),
            distinct=True,
        ),
        overdue=Count(
            "assigned_work_orders",
            filter=Q(assigned_work_orders__scheduled_date__lt=today) & abiertas,
            distinct=True,
        ),
    )
    result = [
        {
            "technician_id": str(tech.id),
            "technician_name": f"{tech.first_name} {tech.last_name}",
            "assigned": tech.assigned,
            "completed": tech.completed,
            "overdue": tech.overdue,
        }
        for tech in techs
    ]
    result.sort(key=lambda x: x["overdue"], reverse=True)
    return result


def calculate_assets_without_maintenance(days=90, hospital_id=None):
    from apps.assets.models import Asset

    since = timezone.now() - timedelta(days=days)
    today = timezone.localdate()

    from apps.maintenance.models import Task

    assets_with_plans = Asset.objects.equipment().filter(
        plan__is_active=True, status=Asset.Status.ACTIVE
    )
    if hospital_id:
        assets_with_plans = assets_with_plans.filter(hospital_id=hospital_id)

    # El mantenimiento se cuenta por tarea hecha sobre el activo, no por OT:
    # una OT puede cubrir varios activos.
    recently_maintained = Task.objects.filter(
        status=Task.Status.DONE,
        completed_at__gte=since,
    ).values_list("asset_id", flat=True)

    last_done = (
        Task.objects.filter(asset=OuterRef("pk"), status=Task.Status.DONE)
        .order_by("-completed_at")
        .values("completed_at")[:1]
    )
    assets_no_pm = (
        assets_with_plans.exclude(id__in=recently_maintained)
        .select_related("hospital")
        .annotate(_last_done=Subquery(last_done))
    )

    result = []
    for asset in assets_no_pm:
        days_since = (
            (today - timezone.localdate(asset._last_done)).days
            if asset._last_done
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


def calculate_assets_status(hospital_id=None):
    """
    Estado de los activos en servicio segun la tarea abierta mas proxima de su
    plan: al dia, por vencer (hasta 30 dias), vencido y sin protocolo (sin plan
    activo). Las mismas fronteras que el listado de activos al que lleva el clic.
    """
    from apps.assets.models import Asset
    from apps.maintenance.models import Task

    today = timezone.localdate()
    soon = today + timedelta(days=30)

    proxima = (
        Task.objects.filter(Task.next_maintenance_q(), asset=OuterRef("pk"))
        .order_by("scheduled_date")
        .values("scheduled_date")[:1]
    )
    assets = Asset.objects.equipment().filter(status=Asset.Status.ACTIVE)
    if hospital_id:
        assets = assets.filter(hospital_id=hospital_id)

    con_plan = Q(plan__isnull=False, plan__is_active=True)
    return assets.annotate(_next_due=Subquery(proxima)).aggregate(
        total=Count("id"),
        no_plan=Count("id", filter=~con_plan),
        overdue=Count("id", filter=con_plan & Q(_next_due__lt=today)),
        due_soon=Count("id", filter=con_plan & Q(_next_due__gte=today, _next_due__lte=soon)),
        on_time=Count(
            "id", filter=con_plan & (Q(_next_due__gt=soon) | Q(_next_due__isnull=True))
        ),
    )


def calculate_pending_by_month(hospital_id=None, months=6):
    """
    Tareas abiertas (pendientes y programadas) por mes, desde el actual, mas las
    vencidas aparte. Como la planificacion de Fracttal. Las pendientes de un plan
    en pausa no son trabajo por planificar (igual que Tareas pendientes).
    """
    from django.db.models.functions import TruncMonth

    from apps.maintenance.models import Task

    today = timezone.localdate()
    first = today.replace(day=1)
    limit = first + relativedelta(months=months)

    qs = Task.objects.filter(status__in=Task.OPEN_STATUSES).exclude(
        Q(status=Task.Status.PENDING)
        & (Q(plan_task__is_active=False) | Q(plan_task__plan__is_active=False))
    )
    if hospital_id:
        qs = qs.filter(asset__hospital_id=hospital_id)

    overdue = qs.filter(scheduled_date__lt=today).count()
    counts = {
        row["m"]: row["n"]
        for row in qs.filter(scheduled_date__gte=today, scheduled_date__lt=limit)
        .annotate(m=TruncMonth("scheduled_date"))
        .values("m")
        .annotate(n=Count("id"))
    }
    result = []
    for i in range(months):
        ref = first + relativedelta(months=i)
        result.append({"month": ref.strftime("%Y-%m"), "count": counts.get(ref, 0)})
    return {"overdue": overdue, "months": result}


def calculate_ots_by_kind(hospital_id=None, days=30):
    """
    OTs del periodo por lo que el catalogo de tipos dice que cuentan:
    preventivo, correctivo u otro. Las canceladas no son trabajo hecho ni por hacer.
    """
    from apps.maintenance.models import TaskTypeCatalog

    since = timezone.now() - timedelta(days=days)
    qs = WorkOrder.objects.filter(created_at__gte=since).exclude(
        status=WorkOrder.Status.CANCELLED
    )
    if hospital_id:
        qs = qs.filter(hospital_id=hospital_id)

    como = dict(TaskTypeCatalog.objects.values_list("code", "counts_as"))
    result = {"PREVENTIVE": 0, "CORRECTIVE": 0, "OTHER": 0}
    for row in qs.values("task_type").annotate(n=Count("id")):
        kind = como.get(row["task_type"], "OTHER")
        result[kind if kind in result else "OTHER"] += row["n"]
    return result


def calculate_open_findings(hospital_id=None):
    """Hallazgos pendientes de decision del planificador, por severidad."""
    from .models import Finding

    qs = Finding.objects.filter(status=Finding.Status.PENDING)
    if hospital_id:
        qs = qs.filter(work_order__hospital_id=hospital_id)

    by_severity = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for row in qs.values("severity").annotate(n=Count("id")):
        by_severity[row["severity"]] = row["n"]
    return {
        "total": sum(by_severity.values()),
        "by_severity": by_severity,
        "out_of_service": qs.filter(out_of_service=True).count(),
    }
