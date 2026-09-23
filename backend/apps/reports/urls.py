from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ConsolidatedReportView,
    GeneratedReportViewSet,
    ReportSettingsPreviewView,
    ReportSettingsView,
)

router = DefaultRouter()
router.register(r"reports", GeneratedReportViewSet, basename="reports")

urlpatterns = router.urls + [
    path("reports/consolidated/", ConsolidatedReportView.as_view(), name="reports-consolidated"),
    path("report-settings/", ReportSettingsView.as_view(), name="report-settings"),
    path("report-settings/preview/", ReportSettingsPreviewView.as_view(), name="report-settings-preview"),
]
