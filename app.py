import os
from datetime import date, datetime, time, timedelta
from urllib.parse import urlencode

from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for

from accounts import accounts
from admin import admin, hours_text, time_text
from db import query_all, query_one
from planner import (KANDY, MANUAL_END, MAX_DAYS_AHEAD, VEHICLES, best_order, build_timeline, load_options, load_places,
                     manual_choices, plan_trip, straight_km)
from routing import RoutingError
from traveller import traveller
from trips import trips

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")
app.config["MAX_CONTENT_LENGTH"] = 80 * 1024 * 1024
app.permanent_session_lifetime = timedelta(days=30)
app.register_blueprint(admin)
app.register_blueprint(accounts)
app.register_blueprint(trips)
app.register_blueprint(traveller)


CARD_COLUMNS = """p.place_id, p.name, p.short_description, p.distance_km, p.image_file,
    c.name AS category, s.name AS sub_type, ROUND(AVG(r.rating), 1) AS rating,
    (SELECT GROUP_CONCAT(category_id SEPARATOR ' ') FROM place_categories
     WHERE place_id = p.place_id) AS category_ids,
    (SELECT GROUP_CONCAT(sub_type_id SEPARATOR ' ') FROM place_sub_types
     WHERE place_id = p.place_id) AS sub_type_ids"""


@app.context_processor
def inject_today():
    return {"today": date.today()}


@app.template_filter("duration")
def duration(minutes):
    hours, mins = divmod(int(minutes), 60)
    if not hours:
        return f"{mins} min"
    return f"{hours} hr {mins} min" if mins else f"{hours} hr"


@app.template_global()
def icon_url(name):
    folder = os.path.join(app.static_folder, "images", "icons")
    file = f"{name}.png" if os.path.exists(os.path.join(folder, f"{name}.png")) else f"{name}.svg"
    return url_for("static", filename=f"images/icons/{file}")


@app.template_filter("clock")
def clock(moment):
    return moment.strftime("%I:%M %p").lstrip("0")


@app.route("/")
def home():
    categories = query_all("SELECT category_id, name FROM categories ORDER BY category_id")

    places = query_all(f"""
        SELECT {CARD_COLUMNS}
        FROM places p
        JOIN categories c ON c.category_id = p.category_id
        LEFT JOIN sub_types s ON s.sub_type_id = p.sub_type_id
        LEFT JOIN reviews r ON r.place_id = p.place_id
        GROUP BY p.place_id
        ORDER BY rating DESC, p.name
    """)

    sub_types = query_all("SELECT sub_type_id, category_id, name FROM sub_types ORDER BY sub_type_id")
    return render_template("index.html", categories=categories, sub_types=sub_types, places=places)


SEARCH_SQL = """(p.name LIKE %s OR p.short_description LIKE %s OR p.keywords LIKE %s
    OR EXISTS (SELECT 1 FROM place_sub_types ps JOIN sub_types st ON st.sub_type_id = ps.sub_type_id
               WHERE ps.place_id = p.place_id AND st.name LIKE %s)
    OR EXISTS (SELECT 1 FROM place_categories pc JOIN categories ct ON ct.category_id = pc.category_id
               WHERE pc.place_id = p.place_id AND ct.name LIKE %s))"""


@app.route("/places")
def places():
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category", type=int)
    sub_type_id = request.args.get("sub_type", type=int)

    categories = query_all("SELECT category_id, name FROM categories ORDER BY category_id")
    sub_types = []
    if category_id:
        sub_types = query_all(
            "SELECT sub_type_id, name FROM sub_types WHERE category_id = %s ORDER BY sub_type_id",
            (category_id,))
    if sub_type_id not in [s["sub_type_id"] for s in sub_types]:
        sub_type_id = None

    conditions = []
    params = []
    if q:
        conditions.append(SEARCH_SQL)
        params += [f"%{q}%"] * 5
    if category_id:
        conditions.append("EXISTS (SELECT 1 FROM place_categories WHERE place_id = p.place_id AND category_id = %s)")
        params.append(category_id)
    if sub_type_id:
        conditions.append("EXISTS (SELECT 1 FROM place_sub_types WHERE place_id = p.place_id AND sub_type_id = %s)")
        params.append(sub_type_id)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    results = query_all(f"""
        SELECT {CARD_COLUMNS}
        FROM places p
        JOIN categories c ON c.category_id = p.category_id
        LEFT JOIN sub_types s ON s.sub_type_id = p.sub_type_id
        LEFT JOIN reviews r ON r.place_id = p.place_id
        {where}
        GROUP BY p.place_id
        ORDER BY p.name
    """, params)

    return render_template("places.html", places=results, categories=categories,
                           sub_types=sub_types, q=q, category_id=category_id,
                           sub_type_id=sub_type_id)


@app.route("/api/suggest")
def suggest():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])

    rows = query_all(f"""
        SELECT p.place_id, p.name, COALESCE(s.name, c.name) AS type
        FROM places p
        JOIN categories c ON c.category_id = p.category_id
        LEFT JOIN sub_types s ON s.sub_type_id = p.sub_type_id
        WHERE {SEARCH_SQL}
        ORDER BY p.name LIKE %s DESC, p.name
        LIMIT 6
    """, [f"%{q}%"] * 5 + [f"{q}%"])
    return jsonify(rows)


@app.route("/places/<int:place_id>")
def place_details(place_id):
    place = query_one("""
        SELECT p.*, c.name AS category, s.name AS sub_type,
               ROUND(AVG(r.rating), 1) AS rating, COUNT(r.review_id) AS review_count
        FROM places p
        JOIN categories c ON c.category_id = p.category_id
        LEFT JOIN sub_types s ON s.sub_type_id = p.sub_type_id
        LEFT JOIN reviews r ON r.place_id = p.place_id
        WHERE p.place_id = %s
        GROUP BY p.place_id
    """, (place_id,))
    if place is None:
        abort(404)

    place["categories"] = query_all("""
        SELECT c.name FROM place_categories pc
        JOIN categories c ON c.category_id = pc.category_id
        WHERE pc.place_id = %s ORDER BY c.category_id = %s DESC, c.category_id
    """, (place_id, place["category_id"]))
    place["sub_types"] = query_all("""
        SELECT s.name FROM place_sub_types ps
        JOIN sub_types s ON s.sub_type_id = ps.sub_type_id
        WHERE ps.place_id = %s ORDER BY s.sub_type_id = %s DESC, s.sub_type_id
    """, (place_id, place["sub_type_id"]))

    reviews = query_all("""
        SELECT r.user_id, r.rating, r.comment, r.created_at, u.full_name
        FROM reviews r
        JOIN users u ON u.user_id = r.user_id
        WHERE r.place_id = %s
        ORDER BY r.user_id = %s DESC, r.created_at DESC
    """, (place_id, session.get("user_id", 0)))
    my_review = next((r for r in reviews if r["user_id"] == session.get("user_id")), None)

    nearby = []
    if place["latitude"] is not None:
        nearby = query_all("""
            SELECT p.place_id, p.name, p.image_file, c.name AS category,
                   COALESCE(s.name, c.name) AS type,
                   ROUND(ST_Distance_Sphere(POINT(p.longitude, p.latitude), POINT(%s, %s)) / 1000, 1) AS km
            FROM places p
            JOIN categories c ON c.category_id = p.category_id
            LEFT JOIN sub_types s ON s.sub_type_id = p.sub_type_id
            WHERE p.place_id != %s AND p.latitude IS NOT NULL
            ORDER BY km
            LIMIT 3
        """, (place["longitude"], place["latitude"], place_id))

    photos = [place["image_file"]] if place["image_file"] else []
    photos += [r["file_name"] for r in query_all(
        "SELECT file_name FROM place_photos WHERE place_id = %s ORDER BY photo_id", (place_id,))]

    return render_template("place_details.html", place=place, reviews=reviews,
                           my_review=my_review, nearby=nearby, photos=photos,
                           maps_key=os.getenv("GOOGLE_MAPS_KEY", ""))


@app.route("/about")
def about():
    counts = query_one("""SELECT (SELECT COUNT(*) FROM places) AS places,
                                 (SELECT COUNT(*) FROM categories) AS categories,
                                 (SELECT COUNT(*) FROM saved_plans WHERE is_public) AS trips""")
    categories = query_all("SELECT category_id, name FROM categories ORDER BY category_id")
    return render_template("about.html", counts=counts, categories=categories)


@app.route("/contact")
def contact():
    return render_template("contact.html", email=CONTACT_EMAIL)


@app.route("/saved")
def saved_places():
    if "user_id" not in session:
        return redirect(url_for("accounts.login", next=url_for("saved_places")))
    places = query_all(f"""
        SELECT {CARD_COLUMNS}
        FROM saved_places sp
        JOIN places p ON p.place_id = sp.place_id
        JOIN categories c ON c.category_id = p.category_id
        LEFT JOIN sub_types s ON s.sub_type_id = p.sub_type_id
        LEFT JOIN reviews r ON r.place_id = p.place_id
        WHERE sp.user_id = %s
        GROUP BY p.place_id, sp.saved_at
        ORDER BY sp.saved_at DESC
    """, (session["user_id"],))
    return render_template("saved_places.html", places=places)


WALK_KM = 0.8
CONTACT_EMAIL = "kandytrail@example.com"
NEAREST = 5
LEG_COLORS = ["#009AFF", "#7C4DFF", "#00B894", "#FF8A00", "#E84393", "#1E88E5"]


@app.route("/plan")
def plan_wizard():
    categories = query_all("SELECT category_id, name FROM categories ORDER BY category_id")
    sub_types = query_all("SELECT sub_type_id, category_id, name FROM sub_types ORDER BY sub_type_id")
    days = [date.today() + timedelta(days=i) for i in range(7)]
    return render_template("plan_wizard.html", categories=categories, sub_types=sub_types,
                           days=days, vehicles=VEHICLES,
                           last_day=date.today() + timedelta(days=MAX_DAYS_AHEAD),
                           mode="manual" if request.args.get("mode") == "manual" else "auto",
                           maps_key=os.getenv("GOOGLE_MAPS_KEY", ""))


FINISH = {"start": "Back at your start point", "kandy": "Kandy city centre", "last": "At the last place"}


def add_walk_tips(plan):
    for before, stop in zip(plan["stops"], plan["stops"][1:]):
        km = straight_km(before["place"]["point"], stop["place"]["point"])
        if km <= WALK_KM:
            stop["walk"] = {"from": before["place"]["name"],
                            "min": max(1, round(km * 1.3 / 4.5 * 60))}


def directions_url(points, travel):
    query = {"api": 1, "origin": "%f,%f" % points[0], "destination": "%f,%f" % points[-1], "travelmode": travel}
    if len(points) > 2:
        query["waypoints"] = "|".join("%f,%f" % p for p in points[1:-1])
    return "https://www.google.com/maps/dir/?" + urlencode(query)


def add_directions(plan):
    points = [plan["start"]] + [stop["place"]["point"] for stop in plan["stops"]]
    if plan["end_point"]:
        points.append(plan["end_point"])
    for i, stop in enumerate(plan["stops"]):
        stop["directions"] = directions_url(points[i:i + 2], "driving")
    if plan["back"]:
        plan["back"]["directions"] = directions_url(points[-2:], "driving")
    plan["trip_links"] = [directions_url(points[i:i + 11], "driving") for i in range(0, len(points) - 1, 10)]


def map_data(plan):
    pins = [{"lat": plan["start"][0], "lng": plan["start"][1], "name": plan["start_label"], "label": "S"}]
    for number, stop in enumerate(plan["stops"], 1):
        pins.append({"lat": stop["place"]["point"][0], "lng": stop["place"]["point"][1],
                     "name": stop["place"]["name"], "label": str(number),
                     "time": f"{clock(stop['arrive'])} - {clock(stop['leave'])}",
                     "image": url_for("static", filename="images/places/" + stop["place"]["image_file"])
                     if stop["place"].get("image_file") else None})
    if plan["end_point"]:
        pins.append({"lat": plan["end_point"][0], "lng": plan["end_point"][1], "name": plan["end_label"],
                     "label": "E", "time": clock(plan["finish"])})
    legs = [{"line": line, "color": LEG_COLORS[i % len(LEG_COLORS)]} for i, line in enumerate(plan["lines"])]
    return {"pins": pins, "legs": legs}


@app.route("/plan", methods=["POST"])
def plan_create():
    form = request.form
    lat = form.get("start_lat", type=float)
    lng = form.get("start_lng", type=float)
    vehicle = form.get("vehicle")
    interests = form.getlist("interests", type=int)
    finish = form.get("finish", "start")
    manual = form.get("mode") == "manual"

    try:
        day = date.fromisoformat(form.get("day", ""))
        depart = datetime.combine(day, time.fromisoformat(form.get("start_time", "")))
        end = datetime.combine(day, time.fromisoformat(form.get("end_time", "")))
    except ValueError:
        return render_template("plan_result.html", error="Please choose a date, start time and end time.")
    if not date.today() <= day <= date.today() + timedelta(days=MAX_DAYS_AHEAD):
        return render_template("plan_result.html", error="Please choose a date within the next 3 months.")
    if manual:
        end, finish = datetime.combine(day, MANUAL_END), "last"

    if lat is None or lng is None:
        error = "Please choose where you will start."
    elif not interests and not manual:
        error = "Please pick at least one interest."
    elif vehicle not in VEHICLES:
        error = "Please choose how you will travel."
    elif finish not in FINISH:
        error = "Please choose where your trip ends."
    elif end - depart < timedelta(hours=2) and not manual:
        error = "Your trip needs at least 2 hours between the start and end time."
    else:
        error = None
    if error:
        return render_template("plan_result.html", error=error)

    if manual:
        session["plan"] = {
            "start": [lat, lng], "start_label": form.get("start_label") or "Your start point",
            "depart": depart.isoformat(), "end": end.isoformat(), "vehicle": vehicle, "finish": finish,
            "stops": [], "suggested": [], "undo": None, "notes": [], "mode": "manual",
        }
        return redirect(url_for("plan_build"))

    end_point = {"start": (lat, lng), "kandy": KANDY, "last": None}[finish]
    picked = set(form.getlist("sub_types", type=int))
    sub_types = {}
    for row in query_all("SELECT sub_type_id, category_id FROM sub_types"):
        if row["sub_type_id"] in picked:
            sub_types.setdefault(row["category_id"], set()).add(row["sub_type_id"])

    dining = query_one("SELECT category_id FROM categories WHERE name = 'Dining'")
    try:
        plan = plan_trip((lat, lng), depart, end, interests, vehicle,
                         lunch=form.get("lunch") == "yes",
                         breakfast=form.get("breakfast") == "yes",
                         dining_id=dining["category_id"] if dining else None,
                         end_point=end_point, sub_type_ids=sub_types)
    except RoutingError:
        return render_template("plan_result.html",
                               error="Travel times are not available right now.")

    stops = [{"id": stop["place"]["place_id"], "option": None, "meal": stop["meal"]} for stop in plan["stops"]]
    session["plan"] = {
        "start": [lat, lng], "start_label": form.get("start_label") or "Your start point",
        "depart": depart.isoformat(), "end": end.isoformat(), "vehicle": vehicle, "finish": finish,
        "stops": stops, "suggested": stops, "undo": None, "notes": plan["notes"],
    }
    return redirect(url_for("plan_result"))


def end_of(saved):
    finish = saved.get("finish", "kandy")
    point = {"start": tuple(saved["start"]), "kandy": KANDY, "last": None}[finish]
    label = saved["start_label"] if finish == "start" else FINISH[finish]
    return point, label


def plan_places(saved):
    places = {p["place_id"]: p for p in load_places()}
    options = load_options([stop["id"] for stop in saved["stops"]])
    stops = []
    for stop in saved["stops"]:
        place = places.get(stop["id"])
        if place is None:
            continue
        place = dict(place, options=options.get(stop["id"], []))
        for option in place["options"]:
            if option["option_id"] == stop["option"]:
                place["stay_min"], place["stay_label"] = option["duration_min"], option["label"]
        stops.append({"place": place, "meal": stop["meal"], "option": stop["option"]})
    return stops, places


@app.route("/plan/result")
def plan_result():
    saved = session.get("plan")
    if not saved:
        return redirect(url_for("plan_wizard"))

    if saved.get("mode") == "manual" and not saved["stops"]:
        return redirect(url_for("plan_build"))

    stops, places = plan_places(saved)
    end_point, end_label = end_of(saved)
    plan = build_timeline(tuple(saved["start"]), datetime.fromisoformat(saved["depart"]),
                          saved["vehicle"], stops, end_point)
    plan["start"] = tuple(saved["start"])
    plan["start_label"] = saved["start_label"]
    plan["end_point"], plan["end_label"] = end_point, end_label
    plan["finish_type"] = saved.get("finish", "kandy")
    plan["end"] = datetime.fromisoformat(saved["end"])
    plan["vehicle"] = VEHICLES[saved["vehicle"]]
    plan["vehicle_key"] = saved["vehicle"]
    back = plan["back"] or {"drive_min": 0, "km": 0}
    plan["drive_min"] = sum(stop["drive_min"] for stop in plan["stops"]) + back["drive_min"]
    plan["km"] = round(sum(stop["km"] for stop in plan["stops"]) + back["km"], 1)
    plan["late_min"] = round((plan["finish"] - plan["end"]).total_seconds() / 60)
    for number, stop in enumerate(plan["stops"]):
        stop["color"] = LEG_COLORS[number % len(LEG_COLORS)]
        place = stop["place"]
        stop["hours"] = hours_text(time_text(place["open_time"]), time_text(place["close_time"]), place["closed_days"])
    if plan["back"]:
        plan["back"]["color"] = LEG_COLORS[len(plan["stops"]) % len(LEG_COLORS)]
    add_walk_tips(plan)
    add_directions(plan)

    in_plan = {stop["id"] for stop in saved["stops"]}
    categories = {c["category_id"]: c["name"] for c in query_all("SELECT category_id, name FROM categories")}
    extra = [p for p in places.values() if p["place_id"] not in in_plan]
    for place in extra:
        place["category_names"] = ", ".join(categories[c] for c in sorted(place["category_ids"]) if c in categories)
    extra.sort(key=lambda p: p["name"])
    gaps = [plan["start"]] + [stop["place"]["point"] for stop in plan["stops"]]

    return render_template("plan_result.html", plan=plan, map=map_data(plan) if plan["stops"] else None,
                           extra=extra, gaps=gaps, notes=saved.get("notes", []), editing=request.args.get("edit") == "1",
                           can_undo=bool(saved["undo"]), changed=saved["stops"] != saved["suggested"],
                           manual=saved.get("mode") == "manual", maps_key=os.getenv("GOOGLE_MAPS_KEY", ""))


@app.route("/plan/build")
def plan_build():
    saved = session.get("plan")
    if not saved:
        return redirect(url_for("plan_wizard", mode="manual"))

    stops, places = plan_places(saved)
    depart = datetime.fromisoformat(saved["depart"])
    plan = build_timeline(tuple(saved["start"]), depart, saved["vehicle"], stops, None)

    if plan["stops"]:
        here, now = plan["stops"][-1]["place"]["point"], plan["stops"][-1]["leave"]
        here_label = plan["stops"][-1]["place"]["name"]
    else:
        here, now, here_label = tuple(saved["start"]), depart, saved["start_label"]
    in_plan = {stop["id"] for stop in saved["stops"]}
    choices = manual_choices(here, now, saved["vehicle"],
                             [p for p in places.values() if p["place_id"] not in in_plan], NEAREST)
    nearest = sorted(choices[:NEAREST], key=lambda c: c["drive_min"])

    category_rows = query_all("SELECT category_id, name FROM categories ORDER BY category_id")
    type_rows = query_all("SELECT sub_type_id, category_id, name FROM sub_types ORDER BY sub_type_id")
    categories = {c["category_id"]: c["name"] for c in category_rows}
    types = {t["sub_type_id"]: t["name"] for t in type_rows}
    options = load_options([c["place"]["place_id"] for c in choices])
    day_start = datetime.combine(depart.date(), time())
    to_min = lambda moment: round((moment - day_start).total_seconds() / 60)

    data = []
    for choice in choices:
        place = choice["place"]
        names = [types[t] for t in sorted(place["sub_type_ids"]) if t in types]
        data.append({
            "id": place["place_id"], "name": place["name"],
            "types": ", ".join(names or [categories[c] for c in sorted(place["category_ids"]) if c in categories]),
            "image": url_for("static", filename="images/places/" + place["image_file"]) if place["image_file"] else None,
            "lat": place["point"][0], "lng": place["point"][1],
            "categories": sorted(place["category_ids"]), "subTypes": sorted(place["sub_type_ids"]),
            "km": choice["km"], "drive": choice["drive_min"], "road": choice["road"],
            "arrive": to_min(choice["arrive"]), "start": to_min(choice["start"]),
            "closes": to_min(day_start + place["close_time"]) if place["close_time"] is not None else None,
            "problem": choice["problem"],
            "hours": hours_text(time_text(place["open_time"]), time_text(place["close_time"]), place["closed_days"]),
            "options": [{"id": o["option_id"], "label": o["label"], "min": o["duration_min"], "default": bool(o["is_default"])}
                        for o in options.get(place["place_id"], [])]
                       or [{"id": None, "label": "Visit", "min": place["stay_min"], "default": True}],
        })

    map_pins = [{"lat": saved["start"][0], "lng": saved["start"][1], "name": saved["start_label"], "label": "S"}]
    for number, stop in enumerate(plan["stops"], 1):
        map_pins.append({"lat": stop["place"]["point"][0], "lng": stop["place"]["point"][1],
                         "name": stop["place"]["name"], "label": str(number)})
    letters = "ABCDE"
    build_map = {"pins": map_pins, "lines": plan["lines"],
                 "next": [{"id": c["place"]["place_id"], "label": letters[i]} for i, c in enumerate(nearest)]}

    drive = sum(stop["drive_min"] for stop in plan["stops"])
    return render_template("plan_build.html", plan=plan, saved=saved, nearest=nearest, letters=letters,
                           places=data, build_map=build_map, categories=category_rows, sub_types=type_rows, here_label=here_label, now=now,
                           drive_min=drive, vehicle=VEHICLES[saved["vehicle"]],
                           can_undo=bool(saved["undo"]), maps_key=os.getenv("GOOGLE_MAPS_KEY", ""))


def best_spot(stops, place, start, end_point):
    points = [start] + [stop["point"] for stop in stops] + [end_point or (stops[-1]["point"] if stops else start)]
    extra = [straight_km(a, place) + straight_km(place, b) - straight_km(a, b)
             for a, b in zip(points, points[1:])]
    return extra.index(min(extra))


@app.route("/plan/edit", methods=["POST"])
def plan_edit():
    saved = session.get("plan")
    if not saved:
        return redirect(url_for("plan_wizard"))
    stops = [dict(stop) for stop in saved["stops"]]
    action = request.form.get("action")
    index = request.form.get("index", type=int)
    valid = index is not None and 0 <= index < len(stops)

    if action == "undo" and saved["undo"] is not None:
        saved["stops"], saved["undo"] = saved["undo"], None
    elif action == "reset":
        saved["undo"], saved["stops"] = saved["stops"], saved["suggested"]
    else:
        if action == "up" and valid and index > 0:
            stops[index - 1], stops[index] = stops[index], stops[index - 1]
        elif action == "down" and valid and index < len(stops) - 1:
            stops[index + 1], stops[index] = stops[index], stops[index + 1]
        elif action == "remove" and valid:
            stops.pop(index)
        elif action == "stay" and valid:
            stops[index]["option"] = request.form.get("option", type=int)
        elif action == "add":
            place_id = request.form.get("place_id", type=int)
            places = {p["place_id"]: p for p in load_places()}
            if place_id in places and place_id not in [stop["id"] for stop in stops]:
                spot = request.form.get("position", type=int)
                if spot is None or not 0 <= spot <= len(stops):
                    spot = best_spot([places[stop["id"]] for stop in stops if stop["id"] in places],
                                     places[place_id]["point"], tuple(saved["start"]), end_of(saved)[0])
                stops.insert(spot, {"id": place_id, "option": request.form.get("option", type=int), "meal": None})
                index = spot
        elif action == "best":
            full, _ = plan_places(saved)
            ordered = best_order(tuple(saved["start"]), full, end_of(saved)[0],
                                 datetime.fromisoformat(saved["depart"]))
            stops = [{"id": s["place"]["place_id"], "option": s["option"], "meal": s["meal"]} for s in ordered]
        saved["undo"], saved["stops"] = saved["stops"], stops

    session["plan"] = saved
    if request.form.get("back") == "build":
        return redirect(url_for("plan_build") + "#places")
    focus = {"up": -1, "down": 1, "stay": 0, "add": 0}.get(action)
    anchor = f"#stop-{index + focus + 1}" if focus is not None and index is not None else ""
    return redirect(url_for("plan_result", edit=1) + anchor)


@app.after_request
def no_cache_pages(response):
    if response.mimetype == "text/html":
        response.headers["Cache-Control"] = "no-store"
    return response


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(413)
def too_large(error):
    return "Photos are too large. Please upload fewer or smaller images.", 413


if __name__ == "__main__":
    app.run(debug=True)
