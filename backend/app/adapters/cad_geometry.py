"""Geometric measurements, without guessing construction scope or units."""
import math
import re

UNIT_METRES = {1: .0254, 2: .3048, 3: 1609.344, 4: .001, 5: .01, 6: 1., 7: 1000., 10: .9144, 14: .1}


def polyline_area_length(points, closed):
    area, length = 0., 0.
    pairs = list(zip(points, points[1:]))
    if closed and points:
        pairs.append((points[-1], points[0]))
    for (x1, y1, bulge), (x2, y2, _) in pairs:
        chord = math.hypot(x2 - x1, y2 - y1)
        area += (x1 * y2 - x2 * y1) / 2
        if bulge and chord:
            angle = 4 * math.atan(bulge)
            radius = chord * (1 + bulge * bulge) / (4 * abs(bulge))
            area += radius * radius * (angle - math.sin(angle)) / 2
            length += abs(angle) * radius
        else:
            length += chord
    return abs(area), length


def entity_measurements(entity, metres):
    kind = entity.dxftype()
    area, length = None, None
    if kind == "LWPOLYLINE":
        points = [(p[0], p[1], p[2]) for p in entity.get_points("xyb")]
        a, length = polyline_area_length(points, entity.closed)
        area = a if entity.closed else None
    elif kind == "POLYLINE" and entity.is_2d_polyline:
        points = [(v.dxf.location.x, v.dxf.location.y, v.dxf.get("bulge", 0)) for v in entity.vertices]
        a, length = polyline_area_length(points, entity.is_closed)
        area = a if entity.is_closed else None
    elif kind == "CIRCLE":
        area, length = math.pi * entity.dxf.radius ** 2, 2 * math.pi * entity.dxf.radius
    elif kind == "ELLIPSE" and abs(entity.dxf.end_param - entity.dxf.start_param - 2 * math.pi) < 1e-6:
        major = entity.dxf.major_axis.magnitude
        area = math.pi * major * major * entity.dxf.ratio
    elif kind == "LINE":
        length = entity.dxf.start.distance(entity.dxf.end)
    elif kind == "ARC":
        length = math.radians((entity.dxf.end_angle - entity.dxf.start_angle) % 360) * entity.dxf.radius
    results = []
    for name, value, power, unit in [("area", area, 2, "m2"), ("length", length, 1, "m")]:
        if value is not None and math.isfinite(value) and value > 1e-12:
            results.append({"type": name, "value": value * metres ** power if metres is not None else value, "unit": unit if metres is not None else f"drawing_unit^{power}", "formula": f"{kind} {name} × 单位换算系数^{power}" if metres is not None else f"{kind} 原图形单位测量", "physical_units_known": metres is not None})
    return results


def attribute_volume(attributes, metres):
    aliases = [{"LENGTH", "长", "长度"}, {"WIDTH", "宽", "宽度"}, {"HEIGHT", "高", "高度", "厚度", "THICKNESS"}]
    dimensions = []
    for keys in aliases:
        attribute = next((a for a in attributes if a["tag"].upper() in keys), None)
        if not attribute:
            return None
        match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(mm|cm|m|毫米|厘米|米)?\s*", attribute["text"], re.I)
        if not match:
            return None
        explicit = {"mm": .001, "毫米": .001, "cm": .01, "厘米": .01, "m": 1., "米": 1.}.get((match[2] or "").lower(), metres)
        if explicit is None:
            return None
        dimensions.append({"tag": attribute["tag"], "raw": attribute["text"], "metres": float(match[1]) * explicit, "handle": attribute["handle"]})
    value = math.prod(d["metres"] for d in dimensions)
    if not math.isfinite(value) or value <= 0:
        return None
    return {"type": "volume", "value": value, "unit": "m3", "formula": " × ".join(f"{d['metres']:g}m" for d in dimensions), "inputs": dimensions, "physical_units_known": True}
