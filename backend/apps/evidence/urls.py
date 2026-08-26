from rest_framework.routers import DefaultRouter

from .views import PhotoViewSet, SignatureViewSet

router = DefaultRouter()
router.register(r"evidence/photos", PhotoViewSet, basename="evidence-photos")
router.register(r"evidence/signatures", SignatureViewSet, basename="evidence-signatures")

urlpatterns = router.urls
