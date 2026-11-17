from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core import views

router = DefaultRouter()
router.register("settings", views.SettingViewSet, basename="setting")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", views.health, name="health"),
    path("api/", include(router.urls)),
    path("api/", include("accounts.urls")),
    path("api/", include("cars.urls")),
    path("api/", include("places.urls")),
    path("api/", include("services.urls")),
    path("api/", include("scheduling.urls")),
    path("api/", include("orders.urls")),
]
