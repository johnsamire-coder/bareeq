from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("manage/ratings", views.ManagerRatingViewSet, basename="manage-rating")
router.register("manage/rating-tags", views.ManagerRatingTagViewSet, basename="manage-rating-tag")
router.register("manage/damage-reports", views.ManagerDamageViewSet, basename="manage-damage")
router.register("manage/closed-days", views.ManagerClosedDayViewSet, basename="manage-closed-day")

urlpatterns = [
    path("rating-tags/", views.rating_tags, name="rating-tags"),
    path("orders/<int:pk>/rating/", views.rate_order, name="order-rating"),
    path("ratings/<int:pk>/photos/", views.rating_photo, name="rating-photos"),
    path("orders/<int:pk>/damage-report/", views.damage_report, name="order-damage-report"),
    path("damage-reports/<int:pk>/photos/", views.damage_photo, name="damage-photos"),
    path("damage-photos/<int:pk>/file/", views.damage_photo_file, name="damage-photo-file"),
] + router.urls
