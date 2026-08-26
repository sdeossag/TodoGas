from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.users.urls")),
    path("api/", include("apps.assets.urls")),
    path("api/", include("apps.work_orders.urls")),
    path("api/", include("apps.checklists.urls")),
    path("api/", include("apps.maintenance.urls")),
    path("api/", include("apps.evidence.urls")),
    path("api/", include("apps.reports.urls")),
    path("api/", include("apps.audit.urls")),
    path("api/", include("apps.inventory.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
