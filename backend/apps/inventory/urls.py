from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import InventoryItemViewSet, StockAlertView, StockMovementViewSet

router = DefaultRouter()
router.register(r'inventory/items', InventoryItemViewSet, basename='inventory-items')
router.register(r'inventory/movements', StockMovementViewSet, basename='inventory-movements')

urlpatterns = router.urls + [
    path('inventory/alerts/', StockAlertView.as_view(), name='inventory-alerts'),
]
