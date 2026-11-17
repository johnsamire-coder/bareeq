def find_zone(lat, lng):
    """The active zone containing the point, or None. Overlaps: lowest sort_order wins."""
    from .models import Zone

    for zone in Zone.objects.filter(is_active=True):
        if zone.contains(lat, lng):
            return zone
    return None


def recompute_address_zones():
    from .models import Address, Zone

    zones = list(Zone.objects.filter(is_active=True))
    for addr in Address.objects.filter(is_active=True).only("id", "lat", "lng", "zone_id"):
        zone_id = next((z.id for z in zones if z.contains(addr.lat, addr.lng)), None)
        if zone_id != addr.zone_id:
            Address.objects.filter(pk=addr.pk).update(zone_id=zone_id)


def notify_newly_covered():
    """'Notify me' requests now inside an active zone: tell the customer once."""
    from django.utils import timezone

    from notifications.events import area_now_covered

    from .models import AreaRequest

    for req in AreaRequest.objects.filter(notified_at__isnull=True).select_related("customer"):
        zone = find_zone(req.lat, req.lng)
        if zone is not None:
            area_now_covered(req, zone)
            AreaRequest.objects.filter(pk=req.pk).update(notified_at=timezone.now())
