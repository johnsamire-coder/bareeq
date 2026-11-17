from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("manage/coupons", views.ManagerCouponViewSet, basename="manage-coupon")
urlpatterns = [path("orders/<int:pk>/coupon/", views.order_coupon, name="order-coupon")] + router.urls
