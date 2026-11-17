from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views
from . import views_lifecycle as lc

router = DefaultRouter()
router.register("orders", views.MyOrderViewSet, basename="order")
router.register("manage/orders", views.ManagerOrderViewSet, basename="manage-order")
router.register("technician/jobs", lc.TechnicianJobViewSet, basename="technician-job")
router.register("manage/customer-charges", lc.ManagerChargeViewSet, basename="manage-charge")

urlpatterns = [
    path("booking/slots/", views.slots, name="booking-slots"),
    path("my-charges/", lc.my_charges, name="my-charges"),
    path("order-photos/<int:pk>/file/", lc.photo_file, name="order-photo-file"),
] + router.urls
