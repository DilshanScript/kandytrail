import math
import os
import secrets
from functools import wraps

from flask import (Blueprint, abort, current_app, flash, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

from db import execute, query_all, query_one

admin = Blueprint("admin", __name__, url_prefix="/admin")

# Kandy city centre, used for distance_km
KANDY_LAT, KANDY_LNG = 7.2906, 80.6337
IMAGE_TYPES = {"jpg", "jpeg", "png", "webp"}
TEXT_FIELDS = ["name", "short_description", "description", "keywords", "opening_hours",
               "entry_fee", "travel_tips", "contact"]


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)
    return wrapper


@admin.before_request
def check_csrf():
    # every admin form sends this token so other sites can't post to us
    if request.method == "POST":
        token = session.get("csrf_token")
        if not token or request.form.get("csrf_token") != token:
            abort(400)


@admin.app_context_processor
def inject_csrf():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return {"csrf_token": session["csrf_token"]}


def distance_from_kandy(lat, lng):
    # haversine formula, result in km
    r = 6371
    d_lat = math.radians(lat - KANDY_LAT)
    d_lng = math.radians(lng - KANDY_LNG)
    a = (math.sin(d_lat / 2) ** 2 + math.cos(math.radians(KANDY_LAT))
         * math.cos(math.radians(lat)) * math.sin(d_lng / 2) ** 2)
    return round(2 * r * math.asin(math.sqrt(a)), 1)


def read_place_form():
    """Return (data, errors) from the submitted place form."""
    form = request.form
    data = {field: form.get(field, "").strip() or None for field in TEXT_FIELDS}
    errors = []

    if not data["name"]:
        errors.append("Name is required.")
    if not data["short_description"]:
        errors.append("Short description is required.")

    # all ticked categories, the first ticked one is the main category
    valid_categories = {row["category_id"] for row in query_all("SELECT category_id FROM categories")}
    data["category_ids"] = [c for c in form.getlist("category_ids", type=int) if c in valid_categories]
    if not data["category_ids"]:
        errors.append("Please choose at least one category.")
    main = form.get("main_category_id", type=int)
    data["category_id"] = main if main in data["category_ids"] else (data["category_ids"] or [None])[0]

    # keep only types that belong to the ticked categories
    types = query_all("SELECT sub_type_id, category_id FROM sub_types")
    allowed = {t["sub_type_id"]: t["category_id"] for t in types if t["category_id"] in data["category_ids"]}
    data["sub_type_ids"] = [t for t in form.getlist("sub_type_ids", type=int) if t in allowed]
    main_types = [t for t in data["sub_type_ids"] if allowed[t] == data["category_id"]]
    data["sub_type_id"] = (main_types or data["sub_type_ids"] or [None])[0]

    data["visit_duration_min"] = form.get("visit_duration_min", type=int)
    if data["visit_duration_min"] is not None and not 5 <= data["visit_duration_min"] <= 720:
        errors.append("Time needed must be between 5 and 720 minutes.")

    data["latitude"] = form.get("latitude", type=float)
    data["longitude"] = form.get("longitude", type=float)
    data["distance_km"] = None
    if data["latitude"] is None or data["longitude"] is None:
        errors.append("Please pick the location on the map.")
    else:
        data["distance_km"] = distance_from_kandy(data["latitude"], data["longitude"])
        if data["distance_km"] > 25:
            errors.append(f"This location is {data['distance_km']} km from Kandy. Places must be within 25 km.")

    photo = request.files.get("photo")
    if photo and photo.filename:
        ext = photo.filename.rsplit(".", 1)[-1].lower()
        if ext not in IMAGE_TYPES:
            errors.append("Photo must be a JPG, PNG or WEBP image.")

    return data, errors


def save_photo(place_id, old_file=None):
    photo = request.files.get("photo")
    if not photo or not photo.filename:
        return old_file

    filename = f"{place_id}-{secure_filename(photo.filename)}".lower()
    folder = os.path.join(current_app.static_folder, "images", "places")
    os.makedirs(folder, exist_ok=True)
    photo.save(os.path.join(folder, filename))
    remove_photo(old_file, keep=filename)
    return filename


def remove_photo(filename, keep=None):
    if filename and filename != keep:
        path = os.path.join(current_app.static_folder, "images", "places", filename)
        if os.path.exists(path):
            os.remove(path)


def save_links(place_id, data):
    execute("DELETE FROM place_categories WHERE place_id = %s", (place_id,))
    execute("DELETE FROM place_sub_types WHERE place_id = %s", (place_id,))
    for category_id in data["category_ids"]:
        execute("INSERT INTO place_categories (place_id, category_id) VALUES (%s, %s)",
                (place_id, category_id))
    for sub_type_id in data["sub_type_ids"]:
        execute("INSERT INTO place_sub_types (place_id, sub_type_id) VALUES (%s, %s)",
                (place_id, sub_type_id))


def keyword_suggestions():
    # the most used keywords across all places
    counts = {}
    for row in query_all("SELECT keywords FROM places WHERE keywords IS NOT NULL"):
        for word in row["keywords"].split(","):
            word = word.strip().lower()
            if word:
                counts[word] = counts.get(word, 0) + 1
    return sorted(counts, key=lambda w: (-counts[w], w))[:20]


def form_options():
    categories = query_all("SELECT category_id, name FROM categories ORDER BY category_id")
    sub_types = query_all("SELECT sub_type_id, category_id, name FROM sub_types ORDER BY sub_type_id")
    return categories, sub_types


@admin.route("/login", methods=["GET", "POST"])
def login():
    if "admin_id" in session:
        return redirect(url_for("admin.dashboard"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = query_one("SELECT admin_id, username, password_hash FROM admins WHERE username = %s",
                         (username,))
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["admin_id"] = user["admin_id"]
            session["admin_name"] = user["username"]
            next_page = request.args.get("next", "")
            # only follow links inside the admin area
            if not next_page.startswith("/admin"):
                next_page = url_for("admin.dashboard")
            return redirect(next_page)
        error = "Wrong username or password."

    return render_template("admin/login.html", error=error)


@admin.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("home"))


@admin.route("/")
@login_required
def dashboard():
    places = query_all("""
        SELECT p.place_id, p.name, p.distance_km, p.image_file, p.updated_at,
               GROUP_CONCAT(c.name ORDER BY c.category_id = p.category_id DESC, c.category_id
                            SEPARATOR ', ') AS categories,
               GROUP_CONCAT(c.category_id SEPARATOR ' ') AS category_ids,
               s.name AS sub_type
        FROM places p
        JOIN place_categories pc ON pc.place_id = p.place_id
        JOIN categories c ON c.category_id = pc.category_id
        LEFT JOIN sub_types s ON s.sub_type_id = p.sub_type_id
        GROUP BY p.place_id
        ORDER BY p.updated_at DESC
    """)
    stats = query_one("""
        SELECT (SELECT COUNT(*) FROM places) AS places,
               (SELECT COUNT(*) FROM reviews) AS reviews,
               (SELECT COUNT(*) FROM users) AS users
    """)
    categories = query_all("SELECT category_id, name FROM categories ORDER BY category_id")
    return render_template("admin/dashboard.html", places=places, stats=stats, categories=categories)


@admin.route("/places/new", methods=["GET", "POST"])
@login_required
def new_place():
    categories, sub_types = form_options()
    place = {}

    if request.method == "POST":
        place, errors = read_place_form()
        if not errors:
            place_id = execute("""
                INSERT INTO places (name, category_id, sub_type_id, short_description, description,
                    keywords, latitude, longitude, distance_km, opening_hours, visit_duration_min,
                    entry_fee, travel_tips, contact)
                VALUES (%(name)s, %(category_id)s, %(sub_type_id)s, %(short_description)s,
                    %(description)s, %(keywords)s, %(latitude)s, %(longitude)s, %(distance_km)s,
                    %(opening_hours)s, %(visit_duration_min)s, %(entry_fee)s, %(travel_tips)s,
                    %(contact)s)
            """, place)
            save_links(place_id, place)
            image = save_photo(place_id)
            if image:
                execute("UPDATE places SET image_file = %s WHERE place_id = %s", (image, place_id))
            flash(f"{place['name']} was added.")
            return redirect(url_for("admin.dashboard"))
        for error in errors:
            flash(error, "error")

    return render_template("admin/place_form.html", place=place, categories=categories,
                           sub_types=sub_types, keywords=keyword_suggestions(), editing=False)


@admin.route("/places/<int:place_id>/edit", methods=["GET", "POST"])
@login_required
def edit_place(place_id):
    current = query_one("SELECT * FROM places WHERE place_id = %s", (place_id,))
    if current is None:
        abort(404)
    categories, sub_types = form_options()
    place = current
    place["category_ids"] = [r["category_id"] for r in query_all(
        "SELECT category_id FROM place_categories WHERE place_id = %s", (place_id,))]
    place["sub_type_ids"] = [r["sub_type_id"] for r in query_all(
        "SELECT sub_type_id FROM place_sub_types WHERE place_id = %s", (place_id,))]

    if request.method == "POST":
        place, errors = read_place_form()
        place["place_id"] = place_id
        place["image_file"] = current["image_file"]
        if not errors:
            place["image_file"] = save_photo(place_id, current["image_file"])
            execute("""
                UPDATE places SET name = %(name)s, category_id = %(category_id)s,
                    sub_type_id = %(sub_type_id)s, short_description = %(short_description)s,
                    description = %(description)s, keywords = %(keywords)s,
                    latitude = %(latitude)s, longitude = %(longitude)s,
                    distance_km = %(distance_km)s, opening_hours = %(opening_hours)s,
                    visit_duration_min = %(visit_duration_min)s, entry_fee = %(entry_fee)s,
                    travel_tips = %(travel_tips)s, contact = %(contact)s,
                    image_file = %(image_file)s
                WHERE place_id = %(place_id)s
            """, place)
            save_links(place_id, place)
            flash(f"{place['name']} was updated.")
            return redirect(url_for("admin.dashboard"))
        for error in errors:
            flash(error, "error")

    return render_template("admin/place_form.html", place=place, categories=categories,
                           sub_types=sub_types, keywords=keyword_suggestions(), editing=True)


@admin.route("/places/<int:place_id>/delete", methods=["POST"])
@login_required
def delete_place(place_id):
    place = query_one("SELECT name, image_file FROM places WHERE place_id = %s", (place_id,))
    if place is None:
        abort(404)
    execute("DELETE FROM places WHERE place_id = %s", (place_id,))
    remove_photo(place["image_file"])
    flash(f"{place['name']} was deleted.")
    return redirect(url_for("admin.dashboard"))
