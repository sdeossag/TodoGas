from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AssetCustomFieldViewSet,
    AssetNodeViewSet,
    AssetViewSet,
    ClientPortalView,
    HospitalViewSet,
)

router = DefaultRouter()
router.register(r"hospitals", HospitalViewSet, basename="hospitals")
router.register(r"asset-nodes", AssetNodeViewSet, basename="asset-nodes")
router.register(r"assets", AssetViewSet, basename="assets")
router.register(r"asset-custom-fields", AssetCustomFieldViewSet, basename="asset-custom-fields")

urlpatterns = router.urls + [
    path("client-portal/summary/", ClientPortalView.as_view(), name="client-portal-summary"),
]
