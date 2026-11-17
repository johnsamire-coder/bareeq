from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("car-brands", views.CarBrandViewSet, basename="car-brand")
router.register("car-models", views.CarModelViewSet, basename="car-model")
router.register("car-colors", views.CarColorViewSet, basename="car-color")
router.register("my-cars", views.MyCarViewSet, basename="my-car")
router.register("unlisted-cars", views.UnlistedCarViewSet, basename="unlisted-car")

urlpatterns = [path("car-options/", views.car_options, name="car-options")] + router.urls
