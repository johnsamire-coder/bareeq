from rest_framework import mixins, viewsets

from accounts.permissions import IsManager

from .models import DayOff, TechnicianProfile, WeeklyShift
from .serializers import DayOffSerializer, TechnicianProfileSerializer, WeeklyShiftSerializer


class TechnicianProfileViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin,
                               viewsets.GenericViewSet):
    """Zones covered and start point. (The technician account itself is added from /api/technicians/.)"""

    permission_classes = [IsManager]
    serializer_class = TechnicianProfileSerializer
    queryset = TechnicianProfile.objects.select_related("user").prefetch_related("zones", "shifts")
    http_method_names = ["get", "patch", "head", "options"]


class WeeklyShiftViewSet(viewsets.ModelViewSet):
    """Working hours per weekday. Deleting a weekday = weekly day off. GET ?technician=<profile id>."""

    permission_classes = [IsManager]
    serializer_class = WeeklyShiftSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = WeeklyShift.objects.all()
        t = self.request.query_params.get("technician")
        return qs.filter(technician=t) if t else qs


class DayOffViewSet(viewsets.ModelViewSet):
    permission_classes = [IsManager]
    serializer_class = DayOffSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        qs = DayOff.objects.all()
        t = self.request.query_params.get("technician")
        return qs.filter(technician=t) if t else qs
