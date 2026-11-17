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
