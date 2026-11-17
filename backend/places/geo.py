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


def _segments_cross(p1, p2, q1, q2):
    """True when segment p1-p2 crosses segment q1-q2 (points are [lat, lng])."""
    def orient(a, b, c):
        v = (b[1] - a[1]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[1] - a[1])
        return 0 if abs(v) < 1e-15 else (1 if v > 0 else -1)

    def on_segment(a, b, c):
        return min(a[0], b[0]) <= c[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= c[1] <= max(a[1], b[1])

    o1, o2, o3, o4 = orient(p1, p2, q1), orient(p1, p2, q2), orient(q1, q2, p1), orient(q1, q2, p2)
    if o1 != o2 and o3 != o4:
        return True
    return ((o1 == 0 and on_segment(p1, p2, q1)) or (o2 == 0 and on_segment(p1, p2, q2))
            or (o3 == 0 and on_segment(q1, q2, p1)) or (o4 == 0 and on_segment(q1, q2, p2)))


def polygons_overlap(a, b):
    """True when two zone shapes share any area (edges cross, or one is inside the other)."""
    n, m = len(a), len(b)
    for i in range(n):
        for j in range(m):
            if _segments_cross(a[i], a[(i + 1) % n], b[j], b[(j + 1) % m]):
                return True
    return point_in_polygon(a[0][0], a[0][1], b) or point_in_polygon(b[0][0], b[0][1], a)
