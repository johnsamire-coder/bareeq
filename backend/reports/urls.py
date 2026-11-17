from django.urls import path

from . import customers, money

urlpatterns = [
    path("manage/customers/", customers.customers, name="manage-customers"),
    path("manage/customers/<int:pk>/", customers.customer_profile, name="manage-customer"),
    path("manage/customers/<int:pk>/notes/", customers.customer_note, name="manage-customer-note"),
    path("manage/reports/", money.report, name="manage-reports"),
]
