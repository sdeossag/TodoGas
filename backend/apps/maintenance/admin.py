from django.contrib import admin

from .models import MaintenancePlan, MaintenancePlanExecution

admin.site.register(MaintenancePlan)
admin.site.register(MaintenancePlanExecution)
