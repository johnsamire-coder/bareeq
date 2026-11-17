from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("manage/services", views.ManageServiceViewSet, basename="manage-service")
router.register("manage/service-prices", views.ManagePriceViewSet, basename="manage-price")
router.register("manage/service-durations", views.ManageDurationViewSet, basename="manage-duration")
router.register("manage/bundles", views.ManageBundleViewSet, basename="manage-bundle")
router.register("manage/oil-types", views.ManageOilTypeViewSet, basename="manage-oil-type")

urlpatterns = [
    path("services/catalog/", views.catalog, name="services-catalog"),
    path("services/quote/", views.quote, name="services-quote"),
] + router.urls
