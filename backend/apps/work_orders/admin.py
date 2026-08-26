from django.contrib import admin

from .models import WorkOrder, WorkOrderStatusHistory

admin.site.register(WorkOrder)
admin.site.register(WorkOrderStatusHistory)
