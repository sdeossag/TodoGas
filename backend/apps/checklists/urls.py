from rest_framework.routers import DefaultRouter

from .views import ChecklistResponseViewSet, ChecklistTemplateViewSet

router = DefaultRouter()
router.register(r"checklists/templates", ChecklistTemplateViewSet, basename="checklist-templates")
router.register(r"checklists/responses", ChecklistResponseViewSet, basename="checklist-responses")

urlpatterns = router.urls
