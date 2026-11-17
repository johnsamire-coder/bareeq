from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("zones", views.ZoneViewSet, basename="zone")
router.register("my-addresses", views.MyAddressViewSet, basename="my-address")
router.register("area-requests", views.AreaRequestViewSet, basename="area-request")

urlpatterns = [path("zones-locate/", views.locate, name="zones-locate")] + router.urls
