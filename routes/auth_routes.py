"""
Authentication.

The server-rendered pages use a simple Flask session cookie (set on
successful login) protected by the `login_required` / `role_required`
decorators below. The JSON API additionally issues a JWT (via
Flask-JWT-Extended) on the same /api/auth/login endpoint so the project can
also be driven headlessly (Postman, another frontend, mobile app, etc.)
without relying on cookies.
"""
from functools import wraps
from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template, flash
from flask_jwt_extended import create_access_token

from database.db import db
from database.models import User, Teacher, Student

auth_bp = Blueprint("auth", __name__)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required"}), 401
            return redirect(url_for("auth.login_page", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Authentication required"}), 401
                return redirect(url_for("auth.login_page"))
            if session.get("role") not in roles:
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Insufficient permissions"}), 403
                flash("You do not have permission to view that page.", "danger")
                return redirect(url_for("dashboard.dashboard_page"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


@auth_bp.route("/login", methods=["GET"])
def login_page():
    if "user_id" in session:
        return redirect(url_for("dashboard.dashboard_page"))
    return render_template("login.html")


@auth_bp.route("/logout", methods=["GET"])
def logout():
    session.clear()
    return redirect(url_for("auth.login_page"))


@auth_bp.route("/api/auth/login", methods=["POST"])
def api_login():
    payload = request.get_json(silent=True) or request.form
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    session["user_id"] = user.id
    session["role"] = user.role
    session["username"] = user.username

    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})

    return jsonify({
        "message": "Login successful",
        "access_token": token,
        "user": user.to_dict(),
        "redirect": url_for("dashboard.dashboard_page"),
    })


@auth_bp.route("/api/auth/me", methods=["GET"])
@login_required
def api_me():
    user = User.query.get(session["user_id"])
    return jsonify(user.to_dict())
