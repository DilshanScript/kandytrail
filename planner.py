import math
from datetime import datetime, time, timedelta

from db import query_all
from routing import travel_from

LUNCH_FROM, LUNCH_TO = time(11, 30), time(14, 30)
END_GRACE = timedelta(minutes=40)   # trip may finish up to 40 min after the end time
MAX_WAIT = timedelta(minutes=30)    # wait at a place that is not open yet
CANDIDATES = 5                      # closest places asked from Google each step


def load_places():
    """All places with their categories and usual visit time."""
    places = query_all("""
        SELECT p.place_id, p.name, p.latitude, p.longitude, p.image_file,
               p.open_time, p.close_time, p.closed_days,
               COALESCE(v.duration_min, p.visit_duration_min, 60) AS stay_min,
               v.label AS stay_label,
               (SELECT GROUP_CONCAT(category_id) FROM place_categories
                WHERE place_id = p.place_id) AS category_ids
        FROM places p
        LEFT JOIN visit_options v ON v.place_id = p.place_id AND v.is_default = TRUE
        WHERE p.latitude IS NOT NULL AND p.longitude IS NOT NULL
    """)
    for place in places:
        place["point"] = (float(place["latitude"]), float(place["longitude"]))
        place["category_ids"] = {int(c) for c in (place["category_ids"] or "").split(",") if c}
    return places


def straight_km(a, b):
    # haversine distance, only used to pick which places to ask Google about
    lat1, lng1, lat2, lng2 = map(math.radians, (*a, *b))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2)
    return 2 * 6371 * math.asin(math.sqrt(h))


def _clock(day, value):
    # MySQL TIME comes back as a timedelta from midnight
    return datetime.combine(day, time()) + value


def visit_window(place, arrive):
    """Return (start, leave) for a visit, or None if the place is closed."""
    closed = place["closed_days"] or ""
    if arrive.strftime("%a") in closed:
        return None

    start = arrive
    if place["open_time"] is not None:
        opens = _clock(arrive.date(), place["open_time"])
        if arrive < opens:
            if opens - arrive > MAX_WAIT:
                return None
            start = opens
    leave = start + timedelta(minutes=place["stay_min"])
    if place["close_time"] is not None and leave > _clock(arrive.date(), place["close_time"]):
        return None
    return start, leave


def next_stop(here, now, pool, end, vehicle):
    """Nearest place by road that is open and fits before the end time."""
    closest = sorted(pool, key=lambda p: straight_km(here, p["point"]))[:CANDIDATES]
    legs = travel_from(here, [p["point"] for p in closest], now, vehicle)

    options = [(leg, p) for leg, p in zip(legs, closest) if leg is not None]
    for leg, place in sorted(options, key=lambda o: o[0]["min"]):
        arrive = now + timedelta(minutes=leg["min"])
        window = visit_window(place, arrive)
        if window and window[1] <= end + END_GRACE:
            return {"place": place, "km": leg["km"], "drive_min": leg["min"],
                    "arrive": arrive, "start": window[0], "leave": window[1]}
    return None


def plan_trip(start_point, depart, end, interest_ids, vehicle="car", lunch=True, dining_id=None):
    """Build a one-day plan: always go to the nearest matching place next."""
    places = load_places()
    interests = [p for p in places if p["category_ids"] & set(interest_ids)]
    dining = [p for p in places if dining_id in p["category_ids"]]

    stops, visited = [], set()
    here, now = start_point, depart
    lunch_done = not lunch or not dining

    while True:
        lunch_time = not lunch_done and LUNCH_FROM <= now.time() <= LUNCH_TO
        if not lunch_done and now.time() > LUNCH_TO:
            lunch_done = True  # missed the lunch window

        pool = [p for p in (dining if lunch_time else interests) if p["place_id"] not in visited]
        stop = next_stop(here, now, pool, end, vehicle) if pool else None

        if stop is None:
            if lunch_time:
                lunch_done = True  # no dining place fits, carry on without lunch
                continue
            break

        stop["is_lunch"] = lunch_time
        if lunch_time:
            lunch_done = True
        stops.append(stop)
        visited.add(stop["place"]["place_id"])
        here, now = stop["place"]["point"], stop["leave"]

    return {"stops": stops, "depart": depart, "finish": now, "end": end}
