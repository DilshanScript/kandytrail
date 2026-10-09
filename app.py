import os
from datetime import date

from flask import Flask, abort, jsonify, render_template, request

from admin import admin
from db import query_all, query_one

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.register_blueprint(admin)


# columns needed for a place card, including all its category and type ids
CARD_COLUMNS = """p.place_id, p.name, p.short_description, p.distance_km, p.image_file,
    c.name AS category, s.name AS sub_type, ROUND(AVG(r.rating), 1) AS rating,
    (SELECT GROUP_CONCAT(category_id SEPARATOR ' ') FROM place_categories
     WHERE place_id = p.place_id) AS category_ids,
    (SELECT GROUP_CONCAT(sub_type_id SEPARATOR ' ') FROM place_sub_types
     WHERE place_id = p.place_id) AS sub_type_ids"""


@app.context_processor
def inject_today():
    return {"today": date.today()}


@app.route("/")
def home():
    categories = query_all("SELECT category_id, name FROM categories ORDER BY category_id")

    # places with category, sub-type and average rating, best rated first
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


# search text matches the name, description, keywords, or any of its types or categories
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
    # ignore a sub-type that doesn't belong to the selected category
    if sub_type_id not in [s["sub_type_id"] for s in sub_types]:
        sub_type_id = None

    # build the WHERE part from the filters that were picked
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

    # names starting with the text come first
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
        SELECT r.rating, r.comment, r.created_at, u.full_name
        FROM reviews r
        JOIN users u ON u.user_id = r.user_id
        WHERE r.place_id = %s
        ORDER BY r.created_at DESC
    """, (place_id,))

    # other places closest to this one (distance in km)
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

    return render_template("place_details.html", place=place, reviews=reviews, nearby=nearby)


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(413)
def too_large(error):
    return "Photo is too large. Please use an image under 5 MB.", 413


if __name__ == "__main__":
    app.run(debug=True)
