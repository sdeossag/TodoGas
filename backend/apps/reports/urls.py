from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ConsolidatedReportView, GeneratedReportViewSet

router = DefaultRouter()
router.register(r"reports", GeneratedReportViewSet, basename="reports")

urlpatterns = router.urls + [
    path("reports/consolidated/", ConsolidatedReportView.as_view(), name="reports-consolidated"),
]
