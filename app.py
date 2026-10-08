from flask import Flask, render_template

from db import query_all

app = Flask(__name__)


@app.route("/")
def home():
    categories = query_all("SELECT category_id, name FROM categories ORDER BY category_id")

    # places with their category and sub-type names
    places = query_all("""
        SELECT p.place_id, p.name, p.short_description, p.distance_km,
               c.name AS category, s.name AS sub_type
        FROM places p
        JOIN categories c ON c.category_id = p.category_id
        LEFT JOIN sub_types s ON s.sub_type_id = p.sub_type_id
        ORDER BY p.name
    """)

    return render_template("index.html", categories=categories, places=places)


if __name__ == "__main__":
    app.run(debug=True)
