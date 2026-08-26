from rest_framework.routers import DefaultRouter

from .views import MaintenancePlanViewSet

router = DefaultRouter()
router.register(r'maintenance/plans', MaintenancePlanViewSet, basename='maintenance-plans')

urlpatterns = router.urls
