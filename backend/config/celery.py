import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'generate-preventive-work-orders-daily': {
        'task': 'maintenance.generate_preventive_work_orders',
        'schedule': crontab(hour=11, minute=0),
    },
}
app.conf.timezone = 'UTC'
