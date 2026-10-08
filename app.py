from datetime import date

from flask import Flask, render_template

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
               p.category_id, c.name AS category, s.name AS sub_type,
               ROUND(AVG(r.rating), 1) AS rating
        FROM places p
        JOIN categories c ON c.category_id = p.category_id
        LEFT JOIN sub_types s ON s.sub_type_id = p.sub_type_id
        LEFT JOIN reviews r ON r.place_id = p.place_id
        GROUP BY p.place_id
        ORDER BY rating DESC, p.name
    """)

    return render_template("index.html", categories=categories, places=places)


if __name__ == "__main__":
    app.run(debug=True)
