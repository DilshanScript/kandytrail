from datetime import date, datetime, timedelta

from flask import (Blueprint, abort, flash, redirect, render_template, request,
                   session, url_for)

from accounts import traveller_required
from admin import time_text
from db import execute, query_all, query_one
from planner import MANUAL_END, MAX_DAYS_AHEAD, VEHICLES

trips = Blueprint("trips", __name__, url_prefix="/trips")

FINISH_NAMES = {"start": "Back at the start point", "kandy": "Kandy city centre", "last": "At the last place"}
MAX_NOTES = 1000

# columns for a trip card, with stop count, place names and a cover photo
CARD_SQL = """
    SELECT t.plan_id, t.user_id, t.name, t.start_label, t.start_latitude, t.start_longitude, t.start_time, t.end_time, t.vehicle,
           t.finish, t.rating, t.notes, t.is_public, t.created_at, u.full_name,
           (SELECT COUNT(*) FROM saved_plan_stops s WHERE s.plan_id = t.plan_id) AS stop_count,
           (SELECT GROUP_CONCAT(p.name ORDER BY s.position SEPARATOR '|')
            FROM saved_plan_stops s JOIN places p ON p.place_id = s.place_id
            WHERE s.plan_id = t.plan_id) AS place_names,
           (SELECT p.image_file FROM saved_plan_stops s JOIN places p ON p.place_id = s.place_id
            WHERE s.plan_id = t.plan_id AND p.image_file IS NOT NULL
            ORDER BY s.position LIMIT 1) AS cover
    FROM saved_plans t
    JOIN users u ON u.user_id = t.user_id
"""


@trips.before_request
def check_csrf():
    # same token check as the admin forms
    if request.method == "POST":
        token = session.get("csrf_token")
        if not token or request.form.get("csrf_token") != token:
            abort(400)


@trips.app_template_filter("short_time")
def short_time(value):
    # MySQL TIME -> "8:00 AM"
    hour, minute = map(int, time_text(value).split(":"))
    return f"{hour % 12 or 12}:{minute:02d} {'AM' if hour < 12 else 'PM'}"


def tidy(trip):
    """Extra fields the templates need."""
    trip["places"] = trip["place_names"].split("|") if trip["place_names"] else []
    trip["vehicle_name"] = VEHICLES.get(trip["vehicle"], (trip["vehicle"].title(),))[0]
    trip["finish_name"] = FINISH_NAMES[trip["finish"]]
    trip["by"] = trip["full_name"].split()[0]
    trip["mine"] = trip["user_id"] == session.get("user_id")
    # picked by hand, so there is no end time to show
    trip["manual"] = time_text(trip["end_time"]) == MANUAL_END.strftime("%H:%M")
    return trip


def get_trip(plan_id):
    """A trip the current traveller is allowed to see, otherwise 404."""
    trip = query_one(CARD_SQL + " WHERE t.plan_id = %s", (plan_id,))
    if not trip or not (trip["is_public"] or trip["user_id"] == session.get("user_id")):
        abort(404)
    return tidy(trip)


def own_trip(plan_id):
    trip = get_trip(plan_id)
    if not trip["mine"]:
        abort(403)
    return trip


def read_trip_form():
    """Return (data, errors) from the save / edit form."""
    form = request.form
    data = {
        "name": form.get("name", "").strip(),
        "start_label": form.get("start_label", "").strip(),
        "rating": form.get("rating", type=int),
        "notes": form.get("notes", "").strip() or None,
        "is_public": form.get("is_public") == "1",
    }
    errors = []
    if not data["name"] or len(data["name"]) > 100:
        errors.append("Give your trip a name (up to 100 letters).")
    if not data["start_label"] or len(data["start_label"]) > 150:
        errors.append("Enter a name for the start point (up to 150 letters).")
    if data["rating"] is not None and not 1 <= data["rating"] <= 5:
        data["rating"] = None
    if data["notes"] and len(data["notes"]) > MAX_NOTES:
        errors.append(f"Notes can be up to {MAX_NOTES} letters.")
    return data, errors


@trips.route("/")
def trip_list():
    tab = "mine" if request.args.get("tab") == "mine" and "user_id" in session else "all"
    q = request.args.get("q", "").strip()
    sort = "top" if request.args.get("sort") == "top" else "new"

    if tab == "mine":
        where, params = ["t.user_id = %s"], [session["user_id"]]
    else:
        where, params = ["t.is_public = TRUE"], []
    if q:
        # name, start point, notes or any place in the trip
        like = f"%{q}%"
        where.append("""(t.name LIKE %s OR t.start_label LIKE %s OR t.notes LIKE %s
            OR EXISTS (SELECT 1 FROM saved_plan_stops s JOIN places p ON p.place_id = s.place_id
                       WHERE s.plan_id = t.plan_id AND p.name LIKE %s))""")
        params += [like] * 4
    order = "t.rating IS NULL, t.rating DESC, t.created_at DESC" if sort == "top" else "t.created_at DESC"

    rows = query_all(CARD_SQL + " WHERE " + " AND ".join(where) + " ORDER BY " + order, params)
    return render_template("trips.html", trips=[tidy(row) for row in rows], tab=tab, q=q, sort=sort)


@trips.route("/save", methods=["GET", "POST"])
@traveller_required
def save():
    plan = session.get("plan")
    if not plan or not plan["stops"]:
        flash("Make a trip plan first, then save it.", "error")
        return redirect(url_for("plan_wizard"))

    data, errors = {"name": "", "start_label": plan["start_label"], "rating": None,
                    "notes": None, "is_public": True}, []
    if request.method == "POST":
        data, errors = read_trip_form()
        if not errors:
            depart = datetime.fromisoformat(plan["depart"])
            end = datetime.fromisoformat(plan["end"])
            plan_id = execute("""
                INSERT INTO saved_plans (user_id, name, start_label, start_latitude, start_longitude,
                    start_time, end_time, vehicle, finish, rating, notes, is_public)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (session["user_id"], data["name"], data["start_label"], plan["start"][0], plan["start"][1],
                 depart.time(), end.time(), plan["vehicle"], plan.get("finish", "kandy"),
                 data["rating"], data["notes"], data["is_public"]))
            for position, stop in enumerate(plan["stops"], 1):
                execute("""INSERT INTO saved_plan_stops (plan_id, position, place_id, option_id, meal)
                           VALUES (%s, %s, %s, %s, %s)""",
                        (plan_id, position, stop["id"], stop["option"], stop["meal"]))
            flash("Your trip was saved.")
            return redirect(url_for("trips.details", plan_id=plan_id))

    return render_template("trip_form.html", data=data, errors=errors, plan=plan, editing=False)


@trips.route("/<int:plan_id>")
def details(plan_id):
    trip = get_trip(plan_id)
    stops = query_all("""
        SELECT s.position, s.meal, p.place_id, p.name, p.short_description, p.image_file,
               c.name AS category, st.name AS sub_type,
               COALESCE(o.label, d.label) AS stay_label,
               COALESCE(o.duration_min, d.duration_min, p.visit_duration_min) AS stay_min
        FROM saved_plan_stops s
        JOIN places p ON p.place_id = s.place_id
        JOIN categories c ON c.category_id = p.category_id
        LEFT JOIN sub_types st ON st.sub_type_id = p.sub_type_id
        LEFT JOIN visit_options o ON o.option_id = s.option_id
        LEFT JOIN visit_options d ON d.place_id = p.place_id AND d.is_default
        WHERE s.plan_id = %s
        ORDER BY s.position""", (plan_id,))
    days = [date.today() + timedelta(days=i) for i in range(7)]
    return render_template("trip_details.html", trip=trip, stops=stops, days=days,
                           last_day=date.today() + timedelta(days=MAX_DAYS_AHEAD))


@trips.route("/<int:plan_id>/use", methods=["POST"])
def use(plan_id):
    trip = get_trip(plan_id)
    try:
        day = date.fromisoformat(request.form.get("day", ""))
    except ValueError:
        day = date.today()
    if not date.today() <= day <= date.today() + timedelta(days=MAX_DAYS_AHEAD):
        day = date.today()

    stops = [{"id": row["place_id"], "option": row["option_id"], "meal": row["meal"]}
             for row in query_all("""SELECT place_id, option_id, meal FROM saved_plan_stops
                                     WHERE plan_id = %s ORDER BY position""", (plan_id,))]
    start = datetime.combine(day, datetime.strptime(time_text(trip["start_time"]), "%H:%M").time())
    end = datetime.combine(day, datetime.strptime(time_text(trip["end_time"]), "%H:%M").time())

    # load it like a new plan so it can be edited and saved again
    session["plan"] = {
        "start": [float(trip["start_latitude"]), float(trip["start_longitude"])],
        "start_label": trip["start_label"], "depart": start.isoformat(), "end": end.isoformat(),
        "vehicle": trip["vehicle"], "finish": trip["finish"], "stops": stops, "suggested": stops,
        "undo": None, "notes": [],
    }
    if trip["manual"]:
        session["plan"]["mode"] = "manual"

    return redirect(url_for("plan_result"))


@trips.route("/<int:plan_id>/edit", methods=["GET", "POST"])
@traveller_required
def edit(plan_id):
    trip = own_trip(plan_id)
    data, errors = trip, []
    if request.method == "POST":
        data, errors = read_trip_form()
        if not errors:
            execute("""UPDATE saved_plans SET name = %s, start_label = %s, rating = %s, notes = %s,
                       is_public = %s WHERE plan_id = %s""",
                    (data["name"], data["start_label"], data["rating"], data["notes"],
                     data["is_public"], plan_id))
            flash("Your trip was updated.")
            return redirect(url_for("trips.details", plan_id=plan_id))
    return render_template("trip_form.html", data=data, errors=errors, trip=trip, editing=True)


@trips.route("/<int:plan_id>/delete", methods=["POST"])
@traveller_required
def delete(plan_id):
    trip = own_trip(plan_id)
    execute("DELETE FROM saved_plans WHERE plan_id = %s", (plan_id,))
    flash(f"{trip['name']} was deleted.")
    return redirect(url_for("trips.trip_list", tab="mine"))
