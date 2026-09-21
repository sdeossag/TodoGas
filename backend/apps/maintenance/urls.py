from rest_framework.routers import DefaultRouter

from .views import MaintenancePlanViewSet, PlanTaskViewSet, RescheduleCauseViewSet, TaskViewSet

router = DefaultRouter()
router.register(r'maintenance/plans', MaintenancePlanViewSet, basename='maintenance-plans')
router.register(r'maintenance/plan-tasks', PlanTaskViewSet, basename='plan-tasks')
router.register(r'tasks', TaskViewSet, basename='tasks')
router.register(r'reschedule-causes', RescheduleCauseViewSet, basename='reschedule-causes')

urlpatterns = router.urls
