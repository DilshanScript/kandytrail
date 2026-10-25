import math
import os
import secrets
from datetime import datetime
from functools import wraps

from flask import (Blueprint, abort, current_app, flash, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

from db import execute, query_all, query_one

admin = Blueprint("admin", __name__, url_prefix="/admin")

KANDY_LAT, KANDY_LNG = 7.2906, 80.6337
IMAGE_TYPES = {"jpg", "jpeg", "png", "webp"}
TEXT_FIELDS = ["name", "short_description", "description", "keywords",
               "entry_fee", "travel_tips", "contact", "transport"]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
FACILITIES = ["Parking", "Toilets", "Restaurant", "Drinking water", "Wheelchair access", "Shops", "Guide service"]
MIN_PHOTOS = 5
MAX_PHOTOS = 12
PHOTO_LIMIT = 5 * 1024 * 1024


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)
    return wrapper


@admin.before_request
def check_csrf():
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
    r = 6371
    d_lat = math.radians(lat - KANDY_LAT)
    d_lng = math.radians(lng - KANDY_LNG)
    a = (math.sin(d_lat / 2) ** 2 + math.cos(math.radians(KANDY_LAT))
         * math.cos(math.radians(lat)) * math.sin(d_lng / 2) ** 2)
    return round(2 * r * math.asin(math.sqrt(a)), 1)


def time_text(value):
    if value is None or isinstance(value, str):
        return value
    minutes = int(value.total_seconds()) // 60
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def valid_time(text):
    try:
        datetime.strptime(text, "%H:%M")
        return True
    except ValueError:
        return False


def nice_time(text):
    hour, minute = map(int, text.split(":"))
    return f"{hour % 12 or 12}:{minute:02d}{'am' if hour < 12 else 'pm'}"


def hours_text(open_time, close_time, closed_days):
    if open_time:
        text = f"{nice_time(open_time)} - {nice_time(close_time)}"
    else:
        text = "Open all day"
    if closed_days:
        return f"{text}, closed on {closed_days.replace(',', ', ')}"
    return text if not open_time else f"Daily {text}"


def read_visit_options(form, errors):
    default = form.get("default_option", type=int, default=0)
    options, bad_row = [], False
    for i, (label, mins) in enumerate(zip(form.getlist("option_label"), form.getlist("option_minutes"))):
        label, mins = label.strip(), mins.strip()
        label = label[:1].upper() + label[1:]
        if not label and not mins:
            continue
        if not label or not mins.isdigit() or not 5 <= int(mins) <= 720:
            bad_row = True
        else:
            mins = int(mins)
        options.append({"label": label[:80], "duration_min": mins, "is_default": i == default})

    if bad_row:
        errors.append("Each way to visit needs a name and 5 to 720 minutes.")
    elif not options:
        errors.append("Add at least one way to visit.")
    if options and not any(o["is_default"] for o in options):
        options[0]["is_default"] = True
    return options


def read_place_form():
    form = request.form
    data = {field: form.get(field, "").strip() or None for field in TEXT_FIELDS}
    errors = []

    if not data["name"]:
        errors.append("Name is required.")
    if not data["short_description"]:
        errors.append("Short description is required.")

    valid_categories = {row["category_id"] for row in query_all("SELECT category_id FROM categories")}
    data["category_ids"] = [c for c in form.getlist("category_ids", type=int) if c in valid_categories]
    if not data["category_ids"]:
        errors.append("Please choose at least one category.")
    main = form.get("main_category_id", type=int)
    data["category_id"] = main if main in data["category_ids"] else (data["category_ids"] or [None])[0]

    types = query_all("SELECT sub_type_id, category_id FROM sub_types")
    allowed = {t["sub_type_id"]: t["category_id"] for t in types if t["category_id"] in data["category_ids"]}
    data["sub_type_ids"] = [t for t in form.getlist("sub_type_ids", type=int) if t in allowed]
    main_types = [t for t in data["sub_type_ids"] if allowed[t] == data["category_id"]]
    data["sub_type_id"] = (main_types or data["sub_type_ids"] or [None])[0]

    data["options"] = read_visit_options(form, errors)
    data["visit_duration_min"] = next((o["duration_min"] for o in data["options"] if o["is_default"]), None)

    data["open_time"] = form.get("open_time", "").strip() or None
    data["close_time"] = form.get("close_time", "").strip() or None
    if form.get("open_all_day"):
        data["open_time"] = data["close_time"] = None
    elif not (data["open_time"] and data["close_time"]):
        errors.append("Give both opening and closing time, or tick Open all day.")
    elif not (valid_time(data["open_time"]) and valid_time(data["close_time"])):
        errors.append("Opening times must look like 08:30.")
    elif data["close_time"] <= data["open_time"]:
        errors.append("Closing time must be after opening time.")
    data["closed_days"] = ",".join(d for d in DAYS if d in form.getlist("closed_days")) or None
    data["facilities"] = ",".join(f for f in FACILITIES if f in form.getlist("facilities")) or None
    if not errors:
        data["opening_hours"] = hours_text(data["open_time"], data["close_time"], data["closed_days"])

    data["latitude"] = form.get("latitude", type=float)
    data["longitude"] = form.get("longitude", type=float)
    data["distance_km"] = None
    if data["latitude"] is None or data["longitude"] is None:
        errors.append("Please pick the location on the map.")
    else:
        data["distance_km"] = distance_from_kandy(data["latitude"], data["longitude"])
        if data["distance_km"] > 25:
            errors.append(f"This location is {data['distance_km']} km from Kandy. Places must be within 25 km.")

    uploads = [request.files.get("photo")] + request.files.getlist("photos")
    for photo in uploads:
        if photo and photo.filename:
            ext = photo.filename.rsplit(".", 1)[-1].lower()
            if ext not in IMAGE_TYPES:
                errors.append(f"{photo.filename} must be a JPG, PNG or WEBP image.")
            elif file_size(photo) > PHOTO_LIMIT:
                errors.append(f"{photo.filename} is larger than 5 MB.")

    return data, errors


def file_size(upload):
    upload.stream.seek(0, os.SEEK_END)
    size = upload.stream.tell()
    upload.stream.seek(0)
    return size


def new_gallery_files():
    return [photo for photo in request.files.getlist("photos") if photo and photo.filename]


def gallery(place_id):
    return query_all("SELECT photo_id, file_name FROM place_photos WHERE place_id = %s ORDER BY photo_id",
                     (place_id,))


def check_photo_count(errors, total):
    if total < MIN_PHOTOS:
        errors.append(f"Please add at least {MIN_PHOTOS} photos. This place has {total}.")
    elif total > MAX_PHOTOS:
        errors.append(f"A place can have up to {MAX_PHOTOS} photos. This place would have {total}.")


def save_gallery(place_id, remove_ids=()):
    for photo in gallery(place_id):
        if photo["photo_id"] in remove_ids:
            execute("DELETE FROM place_photos WHERE photo_id = %s", (photo["photo_id"],))
            remove_photo(photo["file_name"])

    folder = os.path.join(current_app.static_folder, "images", "places")
    os.makedirs(folder, exist_ok=True)
    for photo in new_gallery_files():
        ext = photo.filename.rsplit(".", 1)[-1].lower()
        filename = f"{place_id}-{secrets.token_hex(4)}.{ext}"
        photo.save(os.path.join(folder, filename))
        execute("INSERT INTO place_photos (place_id, file_name) VALUES (%s, %s)", (place_id, filename))


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


def save_visit_options(place_id, options):
    execute("DELETE FROM visit_options WHERE place_id = %s", (place_id,))
    for option in options:
        execute("""INSERT INTO visit_options (place_id, label, duration_min, is_default)
                   VALUES (%s, %s, %s, %s)""",
                (place_id, option["label"], option["duration_min"], option["is_default"]))


def keyword_suggestions():
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
            session["admin_id"] = user["admin_id"]
            session["admin_name"] = user["username"]
            next_page = request.args.get("next", "")
            if not next_page.startswith("/admin"):
                next_page = url_for("admin.dashboard")
            return redirect(next_page)
        error = "Wrong username or password."

    return render_template("admin/login.html", error=error)


@admin.route("/logout", methods=["POST"])
def logout():
    session.pop("admin_id", None)
    session.pop("admin_name", None)
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
        main = request.files.get("photo")
        check_photo_count(errors, (1 if main and main.filename else 0) + len(new_gallery_files()))
        if not errors:
            options = place.pop("options")
            place_id = execute("""
                INSERT INTO places (name, category_id, sub_type_id, short_description, description,
                    keywords, latitude, longitude, distance_km, opening_hours, open_time, close_time,
                    closed_days, visit_duration_min, entry_fee, travel_tips, contact, facilities, transport)
                VALUES (%(name)s, %(category_id)s, %(sub_type_id)s, %(short_description)s,
                    %(description)s, %(keywords)s, %(latitude)s, %(longitude)s, %(distance_km)s,
                    %(opening_hours)s, %(open_time)s, %(close_time)s, %(closed_days)s,
                    %(visit_duration_min)s, %(entry_fee)s, %(travel_tips)s, %(contact)s, %(facilities)s, %(transport)s)
            """, place)
            save_links(place_id, place)
            save_visit_options(place_id, options)
            image = save_photo(place_id)
            if image:
                execute("UPDATE places SET image_file = %s WHERE place_id = %s", (image, place_id))
            save_gallery(place_id)
            flash(f"{place['name']} was added.")
            return redirect(url_for("admin.dashboard"))
        for error in errors:
            flash(error, "error")

    return render_template("admin/place_form.html", place=place, categories=categories,
                           sub_types=sub_types, keywords=keyword_suggestions(), editing=False, facilities=FACILITIES,
                           maps_key=os.getenv("GOOGLE_MAPS_KEY", ""))


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
    place["options"] = query_all("""SELECT label, duration_min, is_default FROM visit_options
                                    WHERE place_id = %s ORDER BY option_id""", (place_id,))
    place["open_time"] = time_text(place["open_time"])
    place["close_time"] = time_text(place["close_time"])
    place["photos"] = gallery(place_id)

    if request.method == "POST":
        photos = place["photos"]
        place, errors = read_place_form()
        place["place_id"] = place_id
        place["image_file"] = current["image_file"]
        remove_ids = {int(value) for value in request.form.getlist("remove_photo") if value.isdigit()}
        main = request.files.get("photo")
        has_main = bool(current["image_file"] or (main and main.filename))
        kept = len([photo for photo in photos if photo["photo_id"] not in remove_ids])
        check_photo_count(errors, int(has_main) + kept + len(new_gallery_files()))
        if not errors:
            options = place.pop("options")
            place["image_file"] = save_photo(place_id, current["image_file"])
            execute("""
                UPDATE places SET name = %(name)s, category_id = %(category_id)s,
                    sub_type_id = %(sub_type_id)s, short_description = %(short_description)s,
                    description = %(description)s, keywords = %(keywords)s,
                    latitude = %(latitude)s, longitude = %(longitude)s,
                    distance_km = %(distance_km)s, opening_hours = %(opening_hours)s,
                    open_time = %(open_time)s, close_time = %(close_time)s,
                    closed_days = %(closed_days)s, visit_duration_min = %(visit_duration_min)s, entry_fee = %(entry_fee)s,
                    travel_tips = %(travel_tips)s, contact = %(contact)s,
                    facilities = %(facilities)s, transport = %(transport)s,
                    image_file = %(image_file)s
                WHERE place_id = %(place_id)s
            """, place)
            save_links(place_id, place)
            save_visit_options(place_id, options)
            save_gallery(place_id, remove_ids)
            flash(f"{place['name']} was updated.")
            return redirect(url_for("admin.dashboard"))
        place["photos"] = photos
        for error in errors:
            flash(error, "error")

    return render_template("admin/place_form.html", place=place, categories=categories,
                           sub_types=sub_types, keywords=keyword_suggestions(), editing=True, facilities=FACILITIES,
                           maps_key=os.getenv("GOOGLE_MAPS_KEY", ""))


@admin.route("/places/<int:place_id>/delete", methods=["POST"])
@login_required
def delete_place(place_id):
    place = query_one("SELECT name, image_file FROM places WHERE place_id = %s", (place_id,))
    if place is None:
        abort(404)
    photos = gallery(place_id)
    execute("DELETE FROM places WHERE place_id = %s", (place_id,))
    remove_photo(place["image_file"])
    for photo in photos:
        remove_photo(photo["file_name"])
    flash(f"{place['name']} was deleted.")
    return redirect(url_for("admin.dashboard"))


@admin.route("/reviews")
@login_required
def reviews():
    q = request.args.get("q", "").strip()
    stars = request.args.get("stars", type=int)
    where, params = [], []
    if q:
        like = f"%{q}%"
        where.append("(p.name LIKE %s OR u.full_name LIKE %s OR r.comment LIKE %s)")
        params += [like] * 3
    if stars in range(1, 6):
        where.append("r.rating = %s")
        params.append(stars)
    rows = query_all("""
        SELECT r.review_id, r.place_id, r.rating, r.comment, r.created_at,
               p.name AS place_name, p.image_file, u.full_name, u.email
        FROM reviews r
        JOIN places p ON p.place_id = r.place_id
        JOIN users u ON u.user_id = r.user_id
        """ + (" WHERE " + " AND ".join(where) if where else "") + """
        ORDER BY r.created_at DESC, r.review_id DESC""", params)
    return render_template("admin/reviews.html", reviews=rows, q=q, stars=stars)


@admin.route("/reviews/<int:review_id>/delete", methods=["POST"])
@login_required
def delete_review(review_id):
    review = query_one("""SELECT u.full_name, p.name FROM reviews r JOIN users u ON u.user_id = r.user_id
                          JOIN places p ON p.place_id = r.place_id WHERE r.review_id = %s""", (review_id,))
    if review is None:
        abort(404)
    execute("DELETE FROM reviews WHERE review_id = %s", (review_id,))
    flash(f"{review['full_name']}'s review of {review['name']} was deleted.")
    return redirect(request.referrer or url_for("admin.reviews"))
