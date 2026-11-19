from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views_phase4 as v4
from . import views
from . import views_lifecycle as lc

router = DefaultRouter()
router.register("orders", views.MyOrderViewSet, basename="order")
router.register("manage/orders", views.ManagerOrderViewSet, basename="manage-order")
router.register("technician/jobs", lc.TechnicianJobViewSet, basename="technician-job")
router.register("manage/customer-charges", lc.ManagerChargeViewSet, basename="manage-charge")

urlpatterns = [
    path("booking/slots/", views.slots, name="booking-slots"),
    path("booking/express/", v4.express_check, name="booking-express"),
    path("technician/location/", v4.technician_location, name="technician-location"),
    path("orders/<int:pk>/tracking/", v4.order_tracking, name="order-tracking"),
    path("manage/live-map/", v4.live_map, name="manage-live-map"),
    path("manage/supervisors/", v4.supervisors, name="manage-supervisors"),
    path("manage/supervisors/<int:pk>/", v4.supervisor_detail, name="manage-supervisor"),
    path("manage/zone-technicians/", v4.zone_technicians, name="manage-zone-technicians"),
    path("my-charges/", lc.my_charges, name="my-charges"),
    path("order-photos/<int:pk>/file/", lc.photo_file, name="order-photo-file"),
] + router.urls
