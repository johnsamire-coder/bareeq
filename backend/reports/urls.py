from django.urls import path

from . import detailed, customers, money

urlpatterns = [
    path("manage/customers/", customers.customers, name="manage-customers"),
    path("manage/customers/<int:pk>/", customers.customer_profile, name="manage-customer"),
    path("manage/customers/<int:pk>/notes/", customers.customer_note, name="manage-customer-note"),
    path("manage/reports/", money.report, name="manage-reports"),
    path("manage/reports/technicians/", detailed.technicians, name="manage-reports-technicians"),
    path("manage/reports/zones/", detailed.zones, name="manage-reports-zones"),
    path("manage/reports/retention/", detailed.retention, name="manage-reports-retention"),
    path("manage/reports/export/", detailed.export, name="manage-reports-export"),
    path("reports/download/<str:token>/", detailed.download, name="reports-download"),
]
