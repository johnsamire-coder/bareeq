from django.urls import path

from . import views

urlpatterns = [
    path("notifications/", views.my_notifications, name="notifications"),
    path("notifications/read-all/", views.mark_all_read, name="notifications-read-all"),
    path("notifications/<int:pk>/read/", views.mark_read, name="notification-read"),
    path("devices/", views.register_device, name="devices"),
]
