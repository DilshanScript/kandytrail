from datetime import date

from flask import Flask, jsonify, render_template, request

from db import query_all

app = Flask(__name__)


@app.context_processor
def inject_today():
    return {"today": date.today()}


@app.route("/")
def home():
    categories = query_all("SELECT category_id, name FROM categories ORDER BY category_id")

    # places with category, sub-type and average rating, best rated first
    places = query_all("""
        SELECT p.place_id, p.name, p.short_description, p.distance_km, p.image_file,
               p.category_id, p.sub_type_id, c.name AS category, s.name AS sub_type,
               ROUND(AVG(r.rating), 1) AS rating
        FROM places p
        JOIN categories c ON c.category_id = p.category_id
        LEFT JOIN sub_types s ON s.sub_type_id = p.sub_type_id
        LEFT JOIN reviews r ON r.place_id = p.place_id
        GROUP BY p.place_id
        ORDER BY rating DESC, p.name
    """)

    sub_types = query_all("SELECT sub_type_id, category_id, name FROM sub_types ORDER BY sub_type_id")
    return render_template("index.html", categories=categories, sub_types=sub_types, places=places)


# search text matches the name, description, keywords, sub-type or category
SEARCH_SQL = """(p.name LIKE %s OR p.short_description LIKE %s OR p.keywords LIKE %s
    OR s.name LIKE %s OR c.name LIKE %s)"""


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
        conditions.append("p.category_id = %s")
        params.append(category_id)
    if sub_type_id:
        conditions.append("p.sub_type_id = %s")
        params.append(sub_type_id)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    results = query_all(f"""
        SELECT p.place_id, p.name, p.short_description, p.distance_km, p.image_file,
               p.category_id, p.sub_type_id, c.name AS category, s.name AS sub_type,
               ROUND(AVG(r.rating), 1) AS rating
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
        SELECT p.name, COALESCE(s.name, c.name) AS type
        FROM places p
        JOIN categories c ON c.category_id = p.category_id
        LEFT JOIN sub_types s ON s.sub_type_id = p.sub_type_id
        WHERE {SEARCH_SQL}
        ORDER BY p.name LIKE %s DESC, p.name
        LIMIT 6
    """, [f"%{q}%"] * 5 + [f"{q}%"])
    return jsonify(rows)

if __name__ == "__main__":
    app.run(debug=True)
