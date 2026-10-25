import os
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
GOOGLE_KEY = os.getenv("GOOGLE_MAPS_KEY", "")
SRI_LANKA = timezone(timedelta(hours=5, minutes=30))

VEHICLE_FACTOR = {"car": 1.0, "van": 1.0, "bike": 1.0, "tuktuk": 1.2, "bus": 1.3}


class RoutingError(Exception):
    pass


def _latlng(point):
    return {"location": {"latLng": {"latitude": float(point[0]),
                                    "longitude": float(point[1])}}}


def _compute(points, depart, fields):
    if not GOOGLE_KEY:
        raise RoutingError("GOOGLE_MAPS_KEY is missing in .env")
    body = {
        "origin": _latlng(points[0]),
        "destination": _latlng(points[-1]),
        "intermediates": [_latlng(p) for p in points[1:-1]],
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
    }
    if depart:
        depart = depart.replace(tzinfo=SRI_LANKA) if depart.tzinfo is None else depart
        if depart > datetime.now(SRI_LANKA):
            body["departureTime"] = depart.isoformat()
    headers = {"X-Goog-Api-Key": GOOGLE_KEY, "X-Goog-FieldMask": fields}
    try:
        res = requests.post(ROUTES_URL, json=body, headers=headers, timeout=15)
    except requests.RequestException:
        raise RoutingError("Could not reach Google routes")
    if res.status_code != 200:
        raise RoutingError(f"Google routes error {res.status_code}: {res.text[:200]}")
    routes = res.json().get("routes")
    if not routes:
        return None
    return routes[0]


def _minutes(duration, vehicle):
    return round(int(duration.rstrip("s")) / 60 * VEHICLE_FACTOR.get(vehicle, 1.0))


def travel_from(origin, destinations, depart, vehicle="car"):
    results = []
    for dest in destinations:
        route = _compute([origin, dest], depart, "routes.distanceMeters,routes.duration")
        if route is None:
            results.append(None)
        else:
            results.append({"km": round(route.get("distanceMeters", 0) / 1000, 1),
                            "min": _minutes(route["duration"], vehicle)})
    return results


def route_line(points, depart=None, vehicle="car"):
    route = _compute(points, depart, "routes.polyline.encodedPolyline,routes.legs.polyline.encodedPolyline,"
                                     "routes.legs.distanceMeters,routes.legs.duration")
    if route is None:
        raise RoutingError("No road route found between these places")
    legs = [{"km": round(leg.get("distanceMeters", 0) / 1000, 1),
             "min": _minutes(leg["duration"], vehicle)} for leg in route["legs"]]
    leg_lines = [_decode(leg["polyline"]["encodedPolyline"]) for leg in route["legs"]]
    return {"line": _decode(route["polyline"]["encodedPolyline"]), "legs": legs, "leg_lines": leg_lines}


def _decode(encoded):
    points, index, lat, lng = [], 0, 0, 0
    while index < len(encoded):
        for axis in (0, 1):
            shift, value = 0, 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                value |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            change = ~(value >> 1) if value & 1 else value >> 1
            if axis == 0:
                lat += change
            else:
                lng += change
        points.append([lat / 1e5, lng / 1e5])
    return points
