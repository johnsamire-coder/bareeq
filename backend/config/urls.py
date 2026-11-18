from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from rest_framework.routers import DefaultRouter

from core import views
from core.inbox import manager_inbox

router = DefaultRouter()
router.register("settings", views.SettingViewSet, basename="setting")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", views.health, name="health"),
    path("api/app-config/", views.app_config, name="app-config"),
    path("api/manage/inbox/", manager_inbox, name="manager-inbox"),
    path("api/", include(router.urls)),
    path("api/", include("accounts.urls")),
    path("api/", include("cars.urls")),
    path("api/", include("places.urls")),
    path("api/", include("services.urls")),
    path("api/", include("scheduling.urls")),
    path("api/", include("payments.urls")),
    path("api/", include("notifications.urls")),
    path("api/", include("feedback.urls")),
    path("api/", include("coupons.urls")),
    path("api/", include("reports.urls")),
    path("api/", include("orders.urls")),
]

if settings.APP_WEB_DIR:
    # The browser version of the app at "/" (test link only; never on the real server).
    _web = Path(settings.APP_WEB_DIR)
    urlpatterns += [
        path("", serve, {"document_root": _web, "path": "index.html"}),
        re_path(r"^(?!api/|admin/)(?P<path>.+)$", serve, {"document_root": _web}),
    ]
