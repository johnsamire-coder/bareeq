from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import DeviceToken, Notification
from .serializers import DeviceSerializer, NotificationSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_notifications(request):
    qs = Notification.objects.filter(user=request.user)
    return Response({"unread": qs.filter(read_at__isnull=True).count(),
                     "results": NotificationSerializer(qs[:100], many=True).data})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_read(request, pk):
    n = get_object_or_404(Notification, pk=pk, user=request.user)
    if n.read_at is None:
        n.read_at = timezone.now()
        n.save(update_fields=["read_at"])
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_all_read(request):
    Notification.objects.filter(user=request.user, read_at__isnull=True).update(read_at=timezone.now())
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def register_device(request):
    s = DeviceSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    _, created = DeviceToken.objects.update_or_create(
        token=s.validated_data["token"],
        defaults={"user": request.user, "platform": s.validated_data["platform"], "last_seen": timezone.now()},
    )
    return Response({"ok": True}, status=201 if created else 200)
