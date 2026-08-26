from django.contrib import admin

from .models import GeneratedReport, ReportSendLog

admin.site.register(GeneratedReport)
admin.site.register(ReportSendLog)
