from django.db import connection
from rest_framework import mixins, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from accounts.permissions import IsManager
from rest_framework.response import Response

from .models import Setting
from .serializers import SettingSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return Response({"status": "ok", "database": "ok"})


class SettingViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Settings for the manager screens in the app. Managers only."""

    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    permission_classes = [IsManager]
    lookup_field = "key"
    http_method_names = ["get", "patch", "head", "options"]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


@api_view(["GET"])
@permission_classes([AllowAny])
def app_config(request):
    """What the app needs before login: is this the test version?"""
    from .services import get_setting

    return Response({"demo_mode": bool(get_setting("demo-mode"))})
