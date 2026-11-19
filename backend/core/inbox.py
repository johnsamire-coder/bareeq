"""What is waiting for the manager, in one call (badge counts in the app)."""
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.permissions import IsManager
from core.services import get_setting


@api_view(["GET"])
@permission_classes([IsManager])
def manager_inbox(request):
    from cars.models import CustomerCar
    from feedback.models import DamageReport, Rating
    from loyalty.models import Referral
    from orders.models import Order
    from payments.models import DailyClosing, Payment
    from places.models import AreaRequest
    from scheduling.availability import CAIRO, local_day_bounds

    start, end = local_day_bounds(timezone.now().astimezone(CAIRO).date())
    return Response({
        "instapay_to_review": Payment.objects.filter(method="instapay", status="pending_review").count(),
        "refunds_due": Payment.objects.filter(status="refund_due").count(),
        "closings_to_confirm": DailyClosing.objects.filter(status="submitted").count(),
        "bad_ratings": Rating.objects.filter(stars__lte=get_setting("ratings-bad-max-stars"),
                                             handled_at__isnull=True).count(),
        "damage_reports": DamageReport.objects.filter(status="open").count(),
        "car_models_to_review": CustomerCar.objects.filter(needs_review=True, is_active=True).count(),
        "notify_me_requests": AreaRequest.objects.filter(notified_at__isnull=True).count(),
        "referrals_to_review": Referral.objects.filter(status="review").count(),
        "orders_today": Order.objects.filter(scheduled_start__gte=start, scheduled_start__lt=end)
        .exclude(status__in=["expired"]).count(),
    })
