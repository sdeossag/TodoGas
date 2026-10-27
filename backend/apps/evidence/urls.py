from django.urls import path
from rest_framework.routers import DefaultRouter

from .firma_guardada import MySignatureView
from .views import PhotoViewSet, SignatureViewSet

router = DefaultRouter()
router.register(r"evidence/photos", PhotoViewSet, basename="evidence-photos")
router.register(r"evidence/signatures", SignatureViewSet, basename="evidence-signatures")

urlpatterns = [
    path("evidence/my-signature/", MySignatureView.as_view(), name="evidence-my-signature"),
    *router.urls,
]
