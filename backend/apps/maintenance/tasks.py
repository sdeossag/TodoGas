import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name='maintenance.generate_preventive_work_orders')
def generate_preventive_work_orders():
    from .engine import run_daily_generation
    summary = run_daily_generation()
    logger.info("[task] Generación diaria completada: %s", summary)
    return summary
