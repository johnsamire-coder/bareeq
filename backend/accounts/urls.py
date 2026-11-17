from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("technicians", views.TechnicianViewSet, basename="technician")
router.register("manage/heard-about-options", views.ManagerHeardAboutViewSet, basename="manage-heard-about")

urlpatterns = [
    path("auth/otp/request/", views.otp_request, name="otp-request"),
    path("auth/otp/verify/", views.otp_verify, name="otp-verify"),
    path("auth/logout/", views.logout, name="logout"),
    path("me/", views.MeView.as_view(), name="me"),
    path("terms/current/", views.current_terms, name="terms-current"),
    path("terms/status/", views.terms_status, name="terms-status"),
    path("manage/terms/", views.manager_terms, name="manage-terms"),
    path("terms/accept/", views.accept_terms, name="terms-accept"),
    path("heard-about-options/", views.HeardAboutListView.as_view(), name="heard-about-options"),
] + router.urls
