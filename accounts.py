import re
from functools import wraps
from urllib.parse import urlparse

from flask import (Blueprint, abort, flash, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from db import execute, query_all, query_one

accounts = Blueprint("accounts", __name__)

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 8


def traveller_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in first.")
            back = request.full_path.rstrip("?")
            if request.method != "GET":
                page = urlparse(request.referrer or "/")
                back = page.path + ("?" + page.query if page.query else "")
            return redirect(url_for("accounts.login", next=back))
        return view(*args, **kwargs)
    return wrapper


@accounts.before_request
def check_csrf():
    if request.method == "POST":
        token = session.get("csrf_token")
        if not token or request.form.get("csrf_token") != token:
            abort(400)


def next_page():
    page = request.args.get("next", "")
    if not page.startswith("/") or page.startswith("//"):
        return url_for("home")
    return page


def sign_in(user, remember):
    session["user_id"] = user["user_id"]
    session["user_name"] = user["full_name"]
    session.permanent = remember


@accounts.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(next_page())

    errors = []
    if request.method == "POST":
        name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not name or len(name) > 100:
            errors.append("Enter your name (up to 100 letters).")
        if not EMAIL_PATTERN.match(email) or len(email) > 150:
            errors.append("Enter a valid email address.")
        if len(password) < MIN_PASSWORD:
            errors.append(f"Password needs at least {MIN_PASSWORD} characters.")
        elif password != confirm:
            errors.append("The two passwords don't match.")
        if not errors and query_one("SELECT user_id FROM users WHERE email = %s", (email,)):
            errors.append("An account with this email already exists. Try signing in.")

        if not errors:
            user_id = execute(
                "INSERT INTO users (full_name, email, password_hash) VALUES (%s, %s, %s)",
                (name, email, generate_password_hash(password)))
            sign_in({"user_id": user_id, "full_name": name}, remember=False)
            flash(f"Welcome to KandyTrail, {name}!")
            return redirect(next_page())

    return render_template("account/register.html", errors=errors)


@accounts.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(next_page())

    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = query_one("SELECT user_id, full_name, password_hash FROM users WHERE email = %s",
                         (email,))
        if user and check_password_hash(user["password_hash"], password):
            sign_in(user, remember=bool(request.form.get("remember")))
            flash(f"Welcome back, {user['full_name']}!")
            return redirect(next_page())
        error = "Wrong email or password."

    return render_template("account/login.html", error=error)


@accounts.route("/logout", methods=["POST"])
def logout():
    for key in ("user_id", "user_name", "plan", "account_errors"):
        session.pop(key, None)
    session.permanent = False
    flash("You have signed out.")
    return redirect(url_for("home"))


@accounts.route("/account")
@traveller_required
def account():
    user_id = session["user_id"]
    user = query_one("SELECT full_name, email, created_at FROM users WHERE user_id = %s", (user_id,))
    counts = query_one("""
        SELECT (SELECT COUNT(*) FROM saved_plans WHERE user_id = %s) AS trips,
               (SELECT COUNT(*) FROM saved_places WHERE user_id = %s) AS places,
               (SELECT COUNT(*) FROM reviews WHERE user_id = %s) AS reviews""", (user_id,) * 3)
    reviews = query_all("""
        SELECT r.place_id, r.rating, r.comment, r.created_at, p.name, p.image_file
        FROM reviews r JOIN places p ON p.place_id = r.place_id
        WHERE r.user_id = %s ORDER BY r.created_at DESC""", (user_id,))
    return render_template("account/account.html", user=user, counts=counts, reviews=reviews,
                           errors=session.pop("account_errors", {}))


@accounts.route("/account/details", methods=["POST"])
@traveller_required
def update_details():
    name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    errors = []
    if not name or len(name) > 100:
        errors.append("Enter your name (up to 100 letters).")
    if not EMAIL_PATTERN.match(email) or len(email) > 150:
        errors.append("Enter a valid email address.")
    elif query_one("SELECT user_id FROM users WHERE email = %s AND user_id <> %s", (email, session["user_id"])):
        errors.append("Another account already uses this email.")

    if errors:
        session["account_errors"] = {"details": errors}
    else:
        execute("UPDATE users SET full_name = %s, email = %s WHERE user_id = %s",
                (name, email, session["user_id"]))
        session["user_name"] = name
        flash("Your details were updated.")
    return redirect(url_for("accounts.account"))


@accounts.route("/account/password", methods=["POST"])
@traveller_required
def change_password():
    current = request.form.get("current_password", "")
    password = request.form.get("password", "")
    confirm = request.form.get("confirm_password", "")
    user = query_one("SELECT password_hash FROM users WHERE user_id = %s", (session["user_id"],))

    errors = []
    if not check_password_hash(user["password_hash"], current):
        errors.append("Your current password is wrong.")
    elif len(password) < MIN_PASSWORD:
        errors.append(f"New password needs at least {MIN_PASSWORD} characters.")
    elif password != confirm:
        errors.append("The two new passwords don't match.")

    if errors:
        session["account_errors"] = {"password": errors}
    else:
        execute("UPDATE users SET password_hash = %s WHERE user_id = %s",
                (generate_password_hash(password), session["user_id"]))
        flash("Your password was changed.")
    return redirect(url_for("accounts.account") + "#password")
