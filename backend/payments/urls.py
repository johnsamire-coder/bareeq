from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("manage/payments", views.ManagerPaymentViewSet, basename="manage-payment")
router.register("manage/invoices", views.ManagerInvoiceViewSet, basename="manage-invoice")
router.register("manage/daily-closings", views.ManagerClosingViewSet, basename="manage-closing")
router.register("manage/materials", views.ManagerMaterialViewSet, basename="manage-material")

urlpatterns = [
    path("payment-info/", views.payment_info, name="payment-info"),
    path("my-wallet/", views.my_wallet, name="my-wallet"),
    path("my-invoices/", views.my_invoices, name="my-invoices"),
    path("payment-proofs/<int:pk>/file/", views.proof_file, name="payment-proof-file"),
    path("technician/materials/", views.technician_materials, name="technician-materials"),
    path("technician/jobs/<int:pk>/materials/", views.technician_job_materials, name="technician-job-materials"),
    path("technician/closing/", views.technician_closing, name="technician-closing"),
    path("manage/wallets/credit/", views.manager_wallet_credit, name="manage-wallet-credit"),
    path("manage/wallets/<int:customer_id>/", views.manager_customer_wallet, name="manage-wallet"),
    path("manage/orders/<int:pk>/money/", views.manager_order_money, name="manage-order-money"),
] + router.urls
