from django.urls import path

from . import views

urlpatterns = [
    path("my-rewards/", views.my_rewards, name="my-rewards"),
    path("orders/<int:pk>/refund-to-wallet/", views.order_refund_to_wallet, name="order-refund-to-wallet"),
    path("manage/referrals/", views.manager_referrals, name="manage-referrals"),
    path("manage/referrals/<int:pk>/<str:decision>/", views.manager_referral_decide, name="manage-referral-decide"),
    path("manage/reports/wallet/", views.manager_wallet_report, name="manage-wallet-report"),
]
