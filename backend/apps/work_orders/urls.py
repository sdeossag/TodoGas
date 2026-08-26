from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import IntegrityCheckView, WorkOrderStatusHistoryViewSet, WorkOrderViewSet
from .views_dashboard import (
    DashboardAssetsStatusView,
    DashboardComplianceHistoryView,
    DashboardView,
)

router = DefaultRouter()
router.register(r"work-orders", WorkOrderViewSet, basename="work-orders")

# Nested history endpoint: GET /api/work-orders/{work_order_pk}/history/
_history_list = WorkOrderStatusHistoryViewSet.as_view({"get": "list"})
_history_detail = WorkOrderStatusHistoryViewSet.as_view({"get": "retrieve"})

urlpatterns = router.urls + [
    path(
        "work-orders/<uuid:work_order_pk>/history/",
        _history_list,
        name="work-order-history-list",
    ),
    path(
        "work-orders/<uuid:work_order_pk>/history/<uuid:pk>/",
        _history_detail,
        name="work-order-history-detail",
    ),
    path(
        "work-orders/<uuid:pk>/integrity/",
        IntegrityCheckView.as_view(),
        name="work-order-integrity",
    ),
    # Dashboard endpoints
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path(
        "dashboard/compliance-history/",
        DashboardComplianceHistoryView.as_view(),
        name="dashboard-compliance-history",
    ),
    path(
        "dashboard/assets-status/",
        DashboardAssetsStatusView.as_view(),
        name="dashboard-assets-status",
    ),
]
