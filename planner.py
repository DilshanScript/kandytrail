import math
from datetime import datetime, time, timedelta

from db import query_all
from routing import VEHICLE_FACTOR, RoutingError, route_line, travel_from

KANDY = (7.2931, 80.6350)

VEHICLES = {
    "car": "Car",
    "van": "Van",
    "bike": "Motorbike",
    "tuktuk": "Tuk-tuk",
    "bus": "Bus",
}
MAX_DAYS_AHEAD = 90
MANUAL_END = time(23, 59)
BREAKFAST_BY = time(10, 30)
LUNCH_FROM, LUNCH_TO = time(11, 30), time(14, 30)
END_GRACE = timedelta(minutes=40)
MAX_WAIT = timedelta(minutes=30)
CANDIDATES = 5


def load_places():
    places = query_all("""
        SELECT p.place_id, p.name, p.latitude, p.longitude, p.image_file,
               p.open_time, p.close_time, p.closed_days, p.opening_hours,
               COALESCE(v.duration_min, p.visit_duration_min, 60) AS stay_min,
               v.label AS stay_label,
               (SELECT GROUP_CONCAT(category_id) FROM place_categories
                WHERE place_id = p.place_id) AS category_ids,
               (SELECT GROUP_CONCAT(sub_type_id) FROM place_sub_types
                WHERE place_id = p.place_id) AS sub_type_ids
        FROM places p
        LEFT JOIN visit_options v ON v.place_id = p.place_id AND v.is_default = TRUE
        WHERE p.latitude IS NOT NULL AND p.longitude IS NOT NULL
    """)
    for place in places:
        place["point"] = (float(place["latitude"]), float(place["longitude"]))
        place["category_ids"] = {int(c) for c in (place["category_ids"] or "").split(",") if c}
        place["sub_type_ids"] = {int(s) for s in (place["sub_type_ids"] or "").split(",") if s}
    return places


def load_options(place_ids):
    if not place_ids:
        return {}
    marks = ", ".join(["%s"] * len(place_ids))
    rows = query_all(f"""
        SELECT option_id, place_id, label, duration_min, is_default FROM visit_options
        WHERE place_id IN ({marks}) ORDER BY place_id, duration_min
    """, list(place_ids))
    options = {}
    for row in rows:
        options.setdefault(row["place_id"], []).append(row)
    return options


def straight_km(a, b):
    lat1, lng1, lat2, lng2 = map(math.radians, (*a, *b))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2)
    return 2 * 6371 * math.asin(math.sqrt(h))


def guess_min(a, b):
    return straight_km(a, b) * 1.4 / 30 * 60


def _clock(day, value):
    return datetime.combine(day, time()) + value


def visit_window(place, arrive):
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


def next_stop(here, now, pool, vehicle, fits, end_point=None):
    closest = sorted(pool, key=lambda p: straight_km(here, p["point"]))[:CANDIDATES]
    try:
        legs = travel_from(here, [p["point"] for p in closest], now, vehicle)
    except RoutingError:
        factor = VEHICLE_FACTOR.get(vehicle, 1.0)
        legs = [{"km": round(straight_km(here, p["point"]) * 1.4, 1),
                 "min": round(guess_min(here, p["point"]) * factor)} for p in closest]

    options = []
    for leg, place in zip(legs, closest):
        if leg is None:
            continue
        arrive = now + timedelta(minutes=leg["min"])
        window = visit_window(place, arrive)
        if window and fits(place, window[1]):
            away = 0
            if end_point:
                away = max(0, guess_min(place["point"], end_point) - guess_min(here, end_point))
            options.append((leg["min"] + away / 2, leg, place, arrive, window))
    if not options:
        return None
    _, leg, place, arrive, (start, leave) = min(options, key=lambda o: o[0])
    return {"place": place, "km": leg["km"], "drive_min": leg["min"],
            "arrive": arrive, "start": start, "leave": leave}


def matches(place, interest_ids, sub_type_ids):
    for category in place["category_ids"] & set(interest_ids):
        picked = sub_type_ids.get(category)
        if not picked or place["sub_type_ids"] & picked:
            return True
    return False


def plan_trip(start_point, depart, end, interest_ids, vehicle="car", lunch=True, dining_id=None,
              breakfast=False, end_point=KANDY, sub_type_ids=None):
    places = load_places()
    dining = [p for p in places if dining_id in p["category_ids"]]
    interests = [p for p in places if matches(p, interest_ids, sub_type_ids or {})]
    if lunch:
        interests = [p for p in interests if dining_id not in p["category_ids"]]

    stops, visited = [], set()
    here, now = start_point, depart
    lunch_done = not lunch or not dining

    def back_in_time(place, leave):
        drive = guess_min(place["point"], end_point) if end_point else 0
        return leave + timedelta(minutes=drive) <= end + END_GRACE

    def before_lunch(place, leave):
        if lunch_done:
            return back_in_time(place, leave)
        to_food = min(guess_min(place["point"], d["point"]) for d in dining if d["place_id"] not in visited)
        lunch_at = leave + timedelta(minutes=to_food)
        return back_in_time(place, leave) and lunch_at.time() <= LUNCH_TO

    breakfast_due = breakfast and bool(dining) and depart.time() < BREAKFAST_BY
    wanted_lunch = not lunch_done

    while True:
        if breakfast_due and now.time() > BREAKFAST_BY:
            breakfast_due = False
        if breakfast_due:
            food = [d for d in dining if d["place_id"] not in visited]
            stop = next_stop(here, now, food, vehicle, back_in_time, end_point)
            if stop:
                stop["meal"] = "breakfast"
                stops.append(stop)
                visited.add(stop["place"]["place_id"])
                here, now = stop["place"]["point"], stop["leave"]
                breakfast_due = False
                continue

        if not lunch_done and (now.time() > LUNCH_TO
                               or all(d["place_id"] in visited for d in dining)):
            lunch_done = True

        pool = [p for p in interests if p["place_id"] not in visited]
        stop = next_stop(here, now, pool, vehicle, before_lunch, end_point) if pool else None
        meal = None

        if stop is None and not lunch_done and now.time() < time(11, 0):
            stop = next_stop(here, now, pool, vehicle, back_in_time, end_point) if pool else None

        if stop is None and not lunch_done:
            food = [d for d in dining if d["place_id"] not in visited]
            stop = next_stop(here, now, food, vehicle, back_in_time, end_point)
            meal = "lunch" if stop else None
            lunch_done = True
            if stop is None:
                continue

        if stop is None:
            break
        stop["meal"] = meal
        stops.append(stop)
        visited.add(stop["place"]["place_id"])
        here, now = stop["place"]["point"], stop["leave"]

    notes = []
    if breakfast and not any(s["meal"] == "breakfast" for s in stops):
        notes.append("No breakfast place open before 10:30 AM.")
    if wanted_lunch and not any(s["meal"] == "lunch" for s in stops):
        notes.append("No lunch stop between 11:30 AM and 2:30 PM.")
    return {"stops": stops, "depart": depart, "end": end, "notes": notes}


def stop_window(place, arrive):
    if arrive.strftime("%a") in (place["closed_days"] or ""):
        leave = arrive + timedelta(minutes=place["stay_min"])
        return arrive, leave, f"Closed on {arrive.strftime('%A')}s"
    start, problem = arrive, None
    if place["open_time"] is not None:
        opens = _clock(arrive.date(), place["open_time"])
        if arrive < opens:
            start = opens
            if opens - arrive > MAX_WAIT:
                problem = f"Opens at {opens.strftime('%I:%M %p').lstrip('0')}"
    leave = start + timedelta(minutes=place["stay_min"])
    if place["close_time"] is not None:
        closes = _clock(arrive.date(), place["close_time"])
        if start >= closes:
            problem = f"Closed on arrival (closes {closes.strftime('%I:%M %p').lstrip('0')})"
        elif leave > closes:
            problem = f"Closes at {closes.strftime('%I:%M %p').lstrip('0')}, before your visit ends"
    return start, leave, problem


def build_timeline(start_point, depart, vehicle, stops, end_point=KANDY):
    points = [start_point] + [stop["place"]["point"] for stop in stops] + ([end_point] if end_point else [])
    try:
        route = route_line(points, depart, vehicle)
        legs, lines, estimated = route["legs"], route["leg_lines"], False
    except RoutingError:
        legs = [{"km": round(straight_km(a, b) * 1.4, 1), "min": round(guess_min(a, b))}
                for a, b in zip(points, points[1:])]
        lines, estimated = [None] * len(legs), True

    if len(points) < 2:
        legs, lines = [], []
    now, timeline = depart, []
    for stop, leg in zip(stops, legs):
        arrive = now + timedelta(minutes=leg["min"])
        start, leave, problem = stop_window(stop["place"], arrive)
        if stop["meal"] == "lunch" and not LUNCH_FROM <= start.time() <= LUNCH_TO:
            problem = problem or f"Lunch at {start.strftime('%I:%M %p').lstrip('0')}, outside 11:30 AM - 2:30 PM"
        elif stop["meal"] == "breakfast" and start.time() > time(11, 0):
            problem = problem or "Quite late for breakfast"
        timeline.append({**stop, "km": leg["km"], "drive_min": leg["min"],
                         "arrive": arrive, "start": start, "leave": leave, "problem": problem})
        now = leave
    back = {"km": legs[-1]["km"], "drive_min": legs[-1]["min"], "leave": now} if end_point and legs else None
    finish = now + timedelta(minutes=back["drive_min"]) if back else now
    return {"stops": timeline, "depart": depart, "finish": finish, "back": back,
            "lines": lines, "estimated": estimated}


def manual_choices(here, now, vehicle, places, near=5):
    factor = VEHICLE_FACTOR.get(vehicle, 1.0)
    places = sorted(places, key=lambda p: straight_km(here, p["point"]))
    legs = [None] * len(places)
    try:
        legs[:near] = travel_from(here, [p["point"] for p in places[:near]], now, vehicle)
    except RoutingError:
        pass

    choices = []
    for place, leg in zip(places, legs):
        if leg:
            km, drive = leg["km"], leg["min"]
        else:
            km = round(straight_km(here, place["point"]) * 1.4, 1)
            drive = max(1, round(guess_min(here, place["point"]) * factor))
        arrive = now + timedelta(minutes=drive)
        start, _, problem = stop_window(dict(place, stay_min=1), arrive)
        choices.append({"place": place, "km": km, "drive_min": drive, "road": bool(leg),
                        "arrive": arrive, "start": start, "problem": problem})
    return choices


def best_order(start_point, stops, end_point, depart):
    first = [s for s in stops if s["meal"] == "breakfast"][:1]
    lunch = [s for s in stops if s["meal"] == "lunch"][:1]
    rest = [s for s in stops if s not in first and s not in lunch]

    def drive(order):
        points = [start_point] + [s["place"]["point"] for s in order] + ([end_point] if end_point else [])
        return sum(guess_min(a, b) for a, b in zip(points, points[1:]))

    here = first[0]["place"]["point"] if first else start_point
    order = []
    while rest:
        nearest = min(rest, key=lambda s: straight_km(here, s["place"]["point"]))
        order.append(nearest)
        rest.remove(nearest)
        here = nearest["place"]["point"]

    improved = True
    while improved:
        improved = False
        for i in range(len(order) - 1):
            for j in range(i + 1, len(order)):
                trial = order[:i] + order[i:j + 1][::-1] + order[j + 1:]
                if drive(first + trial) < drive(first + order) - 0.5:
                    order, improved = trial, True

    if lunch:
        target = datetime.combine(depart.date(), time(13, 30))
        def lunch_gap(i):
            timeline = first + order[:i] + lunch
            now, here = depart, start_point
            for s in timeline:
                now += timedelta(minutes=guess_min(here, s["place"]["point"]))
                now += timedelta(minutes=s["place"]["stay_min"]) if s is not lunch[0] else timedelta()
                here = s["place"]["point"]
            return abs((now - target).total_seconds()) + drive(first + order[:i] + lunch + order[i:]) * 30
        best = min(range(len(order) + 1), key=lunch_gap)
        order = order[:best] + lunch + order[best:]
    return first + order
