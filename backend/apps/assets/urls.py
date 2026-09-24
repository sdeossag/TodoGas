from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AssetCustomFieldViewSet,
    AssetNodeViewSet,
    AssetViewSet,
    ClientPortalView,
    HospitalViewSet,
)
from .views_contracts import ContractViewSet
from .views_meters import MeterReadingViewSet, MeterUnitViewSet, MeterViewSet

router = DefaultRouter()
router.register(r"hospitals", HospitalViewSet, basename="hospitals")
router.register(r"asset-nodes", AssetNodeViewSet, basename="asset-nodes")
router.register(r"assets", AssetViewSet, basename="assets")
router.register(r"contracts", ContractViewSet, basename="contracts")
router.register(r"meter-units", MeterUnitViewSet, basename="meter-units")
router.register(r"meters", MeterViewSet, basename="meters")
router.register(r"meter-readings", MeterReadingViewSet, basename="meter-readings")
router.register(r"asset-custom-fields", AssetCustomFieldViewSet, basename="asset-custom-fields")

urlpatterns = router.urls + [
    path("client-portal/summary/", ClientPortalView.as_view(), name="client-portal-summary"),
]
