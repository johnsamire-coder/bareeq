from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("manage/technician-schedules", views.TechnicianProfileViewSet, basename="technician-schedule")
router.register("manage/technician-shifts", views.WeeklyShiftViewSet, basename="technician-shift")
router.register("manage/technician-days-off", views.DayOffViewSet, basename="technician-day-off")
urlpatterns = router.urls
