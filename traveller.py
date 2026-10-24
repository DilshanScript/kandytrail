from flask import (Blueprint, abort, flash, jsonify, redirect, request, session,
                   url_for)

from accounts import traveller_required
from db import execute, query_all, query_one

traveller = Blueprint("traveller", __name__)

MAX_COMMENT = 1000


@traveller.before_request
def check_csrf():
    # same token check as the admin forms
    if request.method == "POST":
        token = session.get("csrf_token")
        if not token or request.form.get("csrf_token") != token:
            abort(400)


@traveller.app_context_processor
def inject_saved_places():
    # ids of places the signed-in traveller saved, for the bookmark buttons
    if "user_id" not in session:
        return {"saved_places": set()}
    rows = query_all("SELECT place_id FROM saved_places WHERE user_id = %s", (session["user_id"],))
    return {"saved_places": {row["place_id"] for row in rows}}


def place_or_404(place_id):
    place = query_one("SELECT place_id, name FROM places WHERE place_id = %s", (place_id,))
    if place is None:
        abort(404)
    return place


@traveller.route("/places/<int:place_id>/save", methods=["POST"])
def toggle_save(place_id):
    if "user_id" not in session:
        # the page sends the traveller to sign in
        return jsonify(login=url_for("accounts.login", next=request.form.get("next", "/"))), 401
    place_or_404(place_id)
    key = (session["user_id"], place_id)
    if query_one("SELECT 1 FROM saved_places WHERE user_id = %s AND place_id = %s", key):
        execute("DELETE FROM saved_places WHERE user_id = %s AND place_id = %s", key)
        return jsonify(saved=False)
    execute("INSERT INTO saved_places (user_id, place_id) VALUES (%s, %s)", key)
    return jsonify(saved=True)


@traveller.route("/places/<int:place_id>/review", methods=["POST"])
@traveller_required
def save_review(place_id):
    place = place_or_404(place_id)
    rating = request.form.get("rating", type=int)
    comment = request.form.get("comment", "").strip() or None

    if rating is None or not 1 <= rating <= 5:
        flash("Pick 1 to 5 stars for your review.", "error")
    elif comment and len(comment) > MAX_COMMENT:
        flash(f"Reviews can be up to {MAX_COMMENT} letters.", "error")
    else:
        # one review per traveller, writing again replaces it
        execute("""INSERT INTO reviews (user_id, place_id, rating, comment) VALUES (%s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE rating = VALUES(rating), comment = VALUES(comment),
                                           created_at = CURRENT_TIMESTAMP""",
                (session["user_id"], place_id, rating, comment))
        flash(f"Thanks for reviewing {place['name']}!")
    return redirect(url_for("place_details", place_id=place_id) + "#reviews")


@traveller.route("/places/<int:place_id>/review/delete", methods=["POST"])
@traveller_required
def delete_review(place_id):
    execute("DELETE FROM reviews WHERE user_id = %s AND place_id = %s", (session["user_id"], place_id))
    flash("Your review was deleted.")
    return redirect(url_for("place_details", place_id=place_id) + "#reviews")
