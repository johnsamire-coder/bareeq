from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("manage/subscription-plans", views.ManagerPlanViewSet, basename="manage-subscription-plan")

urlpatterns = [
    path("subscription-plans/", views.plans, name="subscription-plans"),
    path("my-subscriptions/", views.my_subscriptions, name="my-subscriptions"),
    path("my-subscriptions/<int:pk>/renew/", views.renew, name="subscription-renew"),
    path("my-subscriptions/<int:pk>/stop-renewal/", views.stop_renewal, name="subscription-stop-renewal"),
    path("subscription-periods/<int:pk>/pay-online/", views.period_pay_online, name="period-pay-online"),
    path("subscription-periods/<int:pk>/pay-instapay/", views.period_pay_instapay, name="period-pay-instapay"),
    path("subscription-periods/<int:pk>/makeup/", views.period_makeup, name="period-makeup"),
    path("manage/subscriptions/", views.manager_subscriptions, name="manage-subscriptions"),
    path("manage/reports/subscriptions/", views.manager_report, name="manage-subscriptions-report"),
] + router.urls
