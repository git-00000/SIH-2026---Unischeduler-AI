"""
Dashboard page + summary/analytics JSON used by Chart.js on the frontend.
"""
from flask import Blueprint, render_template, jsonify, session, request

from database.db import db
from database.models import Department
from routes.auth_routes import login_required, role_required
from services.analytics_service import get_dashboard_summary, get_chart_data

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/", methods=["GET"])
@dashboard_bp.route("/dashboard", methods=["GET"])
@login_required
def dashboard_page():
    return render_template("dashboard.html", role=session.get("role"))


@dashboard_bp.route("/api/dashboard/summary", methods=["GET"])
@login_required
def api_dashboard_summary():
    return jsonify(get_dashboard_summary())


@dashboard_bp.route("/api/dashboard/charts", methods=["GET"])
@login_required
def api_dashboard_charts():
    return jsonify(get_chart_data())


@dashboard_bp.route("/api/departments", methods=["GET"])
@login_required
def api_departments():
    return jsonify([d.to_dict() for d in Department.query.all()])


@dashboard_bp.route("/api/departments", methods=["POST"])
@role_required("admin")
def create_department():
    payload = request.get_json(force=True)
    if not payload.get("name") or not payload.get("code"):
        return jsonify({"error": "name and code are required"}), 400
    if Department.query.filter_by(code=payload["code"]).first():
        return jsonify({"error": "Department code already exists"}), 409
    dept = Department(name=payload["name"], code=payload["code"])
    db.session.add(dept)
    db.session.commit()
    return jsonify(dept.to_dict()), 201
