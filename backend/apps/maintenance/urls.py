from rest_framework.routers import DefaultRouter

from .views import (
    MaintenancePlanViewSet,
    PlanTaskViewSet,
    RescheduleCauseViewSet,
    TaskTypeCatalogViewSet,
    TaskViewSet,
)

router = DefaultRouter()
router.register(r'maintenance/plans', MaintenancePlanViewSet, basename='maintenance-plans')
router.register(r'maintenance/plan-tasks', PlanTaskViewSet, basename='plan-tasks')
router.register(r'tasks', TaskViewSet, basename='tasks')
router.register(r'reschedule-causes', RescheduleCauseViewSet, basename='reschedule-causes')
router.register(r'task-types', TaskTypeCatalogViewSet, basename='task-types')

urlpatterns = router.urls
