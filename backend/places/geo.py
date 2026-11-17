"""Small map math, no external services.

A polygon is a list of [lat, lng] points (at least 3). It does not need to
repeat the first point at the end.
"""
from decimal import Decimal


class InvalidPolygon(ValueError):
    pass


def validate_polygon(polygon):
    if not isinstance(polygon, list) or len(polygon) < 3:
        raise InvalidPolygon("المنطقة لازم يكون ليها 3 نقط على الأقل.")
    clean = []
    for p in polygon:
        if not isinstance(p, (list, tuple)) or len(p) != 2:
            raise InvalidPolygon("كل نقطة لازم تبقى [خط العرض، خط الطول].")
        lat, lng = p
        if isinstance(lat, bool) or isinstance(lng, bool) or not all(isinstance(v, (int, float, Decimal)) for v in p):
            raise InvalidPolygon("الإحداثيات لازم تبقى أرقام.")
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            raise InvalidPolygon("إحداثيات برا الحدود.")
        clean.append([float(lat), float(lng)])
    if clean[0] == clean[-1]:
        clean = clean[:-1]
    if len(clean) < 3:
        raise InvalidPolygon("المنطقة لازم يكون ليها 3 نقط على الأقل.")
    return clean


def point_in_polygon(lat, lng, polygon):
    """Ray casting. Points exactly on an edge may count either way; fine for
    zones whose edges run along streets, not through houses."""
    x, y = float(lng), float(lat)
    inside = False
    n = len(polygon)
    for i in range(n):
        y1, x1 = polygon[i]
        y2, x2 = polygon[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            x_cross = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < x_cross:
                inside = not inside
    return inside
