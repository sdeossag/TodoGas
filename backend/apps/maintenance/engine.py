import logging
import uuid
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.utils import timezone

from .models import MaintenancePlan, MaintenancePlanExecution

logger = logging.getLogger(__name__)


def calculate_next_due_date(plan, from_date=None):
    """Returns the next due date for a plan based on its frequency."""
    if from_date is None:
        from_date = date.today()

    fu = plan.frequency_unit
    fv = plan.frequency_value

    if fu == MaintenancePlan.FrequencyUnit.DAYS:
        return from_date + timedelta(days=fv)
    elif fu == MaintenancePlan.FrequencyUnit.WEEKS:
        return from_date + timedelta(weeks=fv)
    elif fu == MaintenancePlan.FrequencyUnit.MONTHS:
        return from_date + relativedelta(months=fv)
    elif fu == MaintenancePlan.FrequencyUnit.YEARS:
        return from_date + relativedelta(years=fv)

    return from_date + timedelta(days=fv)


def get_plans_due_today():
    """Returns active plans whose next_due_date <= today and that have at least one asset."""
    today = date.today()
    return (
        MaintenancePlan.objects
        .filter(is_active=True, next_due_date__lte=today)
        .filter(assets__isnull=False)
        .prefetch_related('assets')
        .select_related('checklist_template')
        .distinct()
    )


def generate_work_orders_for_plan(plan, triggered_by=None, manual=False):
    """
    Creates one WorkOrder per asset in the plan (skips assets with active OTs).
    Returns {'created': int, 'skipped': int, 'warnings': list, 'execution_id': str}.

    `manual=True` marca el disparo desde la interfaz ("Disparar ahora"), que no
    es lo mismo que la corrida programada: ver `is_cycle_run` mas abajo.
    """
    from apps.work_orders.models import WorkOrder
    from apps.checklists.models import ChecklistTemplateVersion

    created_count = 0
    skipped_count = 0
    warnings = []
    execution = None

    today = date.today()
    due_date = plan.next_due_date or today

    # Un disparo manual ANTES del vencimiento es un mantenimiento extraordinario:
    # la OT es para hoy y el calendario no se toca. Antes se trataba igual que la
    # corrida programada, asi que adelantaba next_due_date un periodo completo y
    # la ejecucion que tocaba desaparecia sin dejar rastro.
    #
    # Si el plan ya vencia, el disparo manual SI ejecuta el ciclo: es la corrida
    # programada hecha a mano. La corrida automatica siempre entra por aqui,
    # porque get_plans_due_today() solo devuelve planes con next_due_date <= hoy.
    is_cycle_run = (
        not manual
        or plan.next_due_date is None
        or plan.next_due_date <= today
    )
    scheduled_for = due_date if is_cycle_run else today

    checklist_version = None
    if plan.checklist_template_id:
        checklist_version = (
            ChecklistTemplateVersion.objects
            .filter(template_id=plan.checklist_template_id, is_current=True)
            .first()
        )
        # El serializer ya no deja asociar una plantilla sin version publicada,
        # pero se puede despublicar despues de crear el plan, y los planes
        # anteriores a esa validacion siguen en la base. Se generan igual: no
        # crear la OT cancelaria el preventivo en silencio, que es peor que una
        # OT sin checklist. Lo que no puede pasar es que nadie se entere.
        if checklist_version is None:
            warnings.append(
                f"La plantilla '{plan.checklist_template.name}' no tiene version "
                "publicada: las OT se crean sin checklist que diligenciar."
            )

    active_statuses = [
        WorkOrder.Status.PENDING,
        WorkOrder.Status.IN_PROGRESS,
        WorkOrder.Status.IN_REVIEW,
    ]

    with transaction.atomic():
        creator = triggered_by
        if creator is None:
            from apps.users.models import User
            creator = User.objects.filter(role=User.Role.ADMIN).first()

        if creator is None:
            return {
                'created': 0,
                'skipped': 0,
                'warnings': ['No se encontró usuario administrador para crear OTs.'],
                'execution_id': None,
            }

        for asset in plan.assets.all():
            if WorkOrder.objects.filter(
                maintenance_plan=plan,
                asset=asset,
                status__in=active_statuses,
            ).exists():
                skipped_count += 1
                warnings.append(f"Activo '{asset.code}': ya tiene una OT activa para este plan.")
                continue

            title = f"[PM] {plan.name} — {asset.name}"[:500]
            wo = WorkOrder(
                asset=asset,
                task_type=plan.task_type,
                title=title,
                description=plan.description,
                classification_1=plan.classification_1,
                classification_2=plan.classification_2,
                priority=plan.priority,
                status=WorkOrder.Status.PENDING,
                maintenance_plan=plan,
                checklist_version=checklist_version,
                scheduled_date=scheduled_for,
                created_by=creator,
                estimated_duration=plan.estimated_duration,
            )
            wo.save()
            created_count += 1

        execution = MaintenancePlanExecution.objects.create(
            plan=plan,
            executed_by=triggered_by,
            work_orders_created=created_count,
            notes=f"Creadas: {created_count}, omitidas: {skipped_count}.",
        )

        plan.last_generated_at = timezone.now()
        if is_cycle_run:
            plan.next_due_date = calculate_next_due_date(plan, from_date=due_date)
            plan.save(update_fields=['last_generated_at', 'next_due_date'])
        else:
            # Extraordinario: el calendario se queda donde estaba. Se avisa,
            # porque "Disparar ahora" sin mas da a entender que consumio el ciclo.
            plan.save(update_fields=['last_generated_at'])
            warnings.append(
                "Mantenimiento extraordinario: el proximo vencimiento programado "
                f"sigue siendo el {plan.next_due_date}."
            )

    return {
        'created': created_count,
        'skipped': skipped_count,
        'warnings': warnings,
        'execution_id': str(execution.id),
    }


def run_daily_generation():
    """
    Processes all due maintenance plans and logs each execution to AuditLog.
    Returns {'plans_processed': int, 'total_created': int, 'total_skipped': int, 'errors': list}.
    """
    from apps.audit.models import AuditLog

    plans = list(get_plans_due_today())
    summary = {
        'plans_processed': 0,
        'total_created': 0,
        'total_skipped': 0,
        'errors': [],
    }

    for plan in plans:
        try:
            result = generate_work_orders_for_plan(plan)
            summary['plans_processed'] += 1
            summary['total_created'] += result['created']
            summary['total_skipped'] += result['skipped']

            if result['execution_id']:
                AuditLog.objects.create(
                    user=None,
                    action=AuditLog.Action.CREATE,
                    entity_type='MaintenancePlanExecution',
                    entity_id=uuid.UUID(result['execution_id']),
                    changes={
                        'plan': str(plan.id),
                        'created': result['created'],
                        'skipped': result['skipped'],
                        'warnings': result['warnings'],
                    },
                )
            logger.info(
                "[engine] Plan '%s': %d OTs creadas, %d omitidas.",
                plan.name, result['created'], result['skipped'],
            )
        except Exception as exc:
            summary['errors'].append({'plan': str(plan.id), 'error': str(exc)})
            logger.error("[engine] Error en plan '%s': %s", plan.name, exc, exc_info=True)

    return summary
