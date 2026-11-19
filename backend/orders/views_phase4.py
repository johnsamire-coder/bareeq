"""Phase 4 endpoints: tracking, the live map, the express option, supervisors."""
from datetime import date

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.models import User
from accounts.permissions import IsCustomer, IsManager, IsManagerOrSupervisor, IsTechnician, limit_to_zones
from core.errors import BusinessError
from core.services import get_setting
from scheduling.availability import CAIRO, local_day_bounds
from scheduling.models import SupervisorProfile, TechnicianProfile

from . import tracking
from .booking import prepare
from .fees import express_option
from .models import Order
from .serializers import SlotsRequestSerializer


@api_view(["POST"])
@permission_classes([IsTechnician])
def technician_location(request):
    d = request.data
    return Response(tracking.report(request.user, d.get("lat"), d.get("lng"), d.get("accuracy")))


@api_view(["GET"])
@permission_classes([IsCustomer])
def order_tracking(request, pk):
    return Response(tracking.for_customer(get_object_or_404(Order, pk=pk, customer=request.user)))


@api_view(["POST"])
@permission_classes([IsCustomer])
def express_check(request):
    """Body like booking/slots: can someone come now? {available, start, fee, minutes_from_now}."""
    s = SlotsRequestSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    prep = prepare(request.user, s.validated_data["address"], s.validated_data["items"])
    opt = express_option(prep)
    if opt is None:
        return Response({"available": False})
    mins = int((opt["start"] - timezone.now()).total_seconds() // 60)
    return Response({"available": True, "start": opt["start"], "fee": opt["fee"], "minutes_from_now": max(mins, 0)})


@api_view(["GET"])
@permission_classes([IsManagerOrSupervisor])
def live_map(request):
    """Technicians' last positions and the day's jobs (a supervisor: his zones only)."""
    day = date.fromisoformat(request.query_params["date"]) if request.query_params.get("date") else \
        timezone.now().astimezone(CAIRO).date()
    start, end = local_day_bounds(day)
    orders = limit_to_zones(Order.objects.filter(scheduled_start__gte=start, scheduled_start__lt=end).exclude(
        status=Order.Status.EXPIRED).select_related("technician", "customer"), request.user)
    techs = TechnicianProfile.objects.filter(user__is_active=True).select_related("user")
    if request.user.role == User.Role.SUPERVISOR:
        techs = techs.filter(zones__in=request.user.supervisor_profile.zones.all()).distinct()
    fresh = get_setting("tracking-fresh-minutes")
    tech_rows = []
    for t in techs:
        p = tracking.last_point(t.user, fresh)
        job = tracking.active_job(t.user)
        tech_rows.append({"id": t.user_id, "name": t.user.full_name,
                          "lat": float(p.lat) if p else None, "lng": float(p.lng) if p else None,
                          "updated_at": p.recorded_at if p else None, "on_the_way_to": job.id if job else None})
    return Response({
        "date": day.isoformat(),
        "technicians": tech_rows,
        "orders": [{"id": o.id, "lat": float(o.lat), "lng": float(o.lng), "status": o.status,
                    "status_label": o.get_status_display(), "start": o.scheduled_start,
                    "technician": o.technician_id, "technician_name": o.technician.full_name if o.technician else None,
                    "customer_name": o.customer.full_name, "is_express": o.is_express} for o in orders],
    })


# ---------- supervisors (the manager adds them) ----------

def _supervisor_row(u):
    prof = getattr(u, "supervisor_profile", None)
    zones = list(prof.zones.values("id", "name")) if prof else []
    return {"id": u.id, "full_name": u.full_name, "phone": u.phone, "is_active": u.is_active, "zones": zones}


@api_view(["GET", "POST"])
@permission_classes([IsManager])
def supervisors(request):
    if request.method == "GET":
        return Response([_supervisor_row(u) for u in User.objects.filter(role=User.Role.SUPERVISOR).order_by("id")])
    from accounts.phone import normalize_phone

    d = request.data
    name = (d.get("full_name") or "").strip()
    if not name:
        raise BusinessError("name_required", "اكتب اسم المشرف.")
    phone = normalize_phone(d.get("phone") or "")
    if User.objects.filter(phone=phone).exists():
        raise BusinessError("phone_taken", "الرقم ده عليه حساب بالفعل.")
    u = User.objects.create_user(phone, name, role=User.Role.SUPERVISOR)
    prof = SupervisorProfile.objects.create(user=u)
    prof.zones.set(d.get("zones") or [])
    return Response(_supervisor_row(u), status=201)


@api_view(["PATCH"])
@permission_classes([IsManager])
def supervisor_detail(request, pk):
    u = get_object_or_404(User, pk=pk, role=User.Role.SUPERVISOR)
    prof, _ = SupervisorProfile.objects.get_or_create(user=u)
    d = request.data
    if "zones" in d:
        prof.zones.set(d["zones"] or [])
    if "is_active" in d:
        u.is_active = bool(d["is_active"])
        u.save(update_fields=["is_active"])
    if d.get("full_name"):
        u.full_name = d["full_name"].strip()[:150]
        u.save(update_fields=["full_name"])
    return Response(_supervisor_row(u))


@api_view(["GET"])
@permission_classes([IsManagerOrSupervisor])
def zone_technicians(request):
    """Technicians a supervisor may move jobs to (his zones)."""
    techs = TechnicianProfile.objects.filter(user__is_active=True).select_related("user")
    if request.user.role == User.Role.SUPERVISOR:
        techs = techs.filter(zones__in=request.user.supervisor_profile.zones.all()).distinct()
    return Response([{"id": t.user_id, "full_name": t.user.full_name} for t in techs])
