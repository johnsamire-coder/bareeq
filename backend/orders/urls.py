from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("orders", views.MyOrderViewSet, basename="order")
router.register("manage/orders", views.ManagerOrderViewSet, basename="manage-order")

urlpatterns = [path("booking/slots/", views.slots, name="booking-slots")] + router.urls
