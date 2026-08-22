"""
Teacher CRUD + teacher availability + teacher's own timetable view.
"""
from flask import Blueprint, request, jsonify, render_template, session

from database.db import db
from database.models import (
    Teacher, Department, TeacherAvailability, TimeSlot, TimetableEntry,
    GenerationRun,
)
from routes.auth_routes import login_required, role_required

teacher_bp = Blueprint("teachers", __name__)


@teacher_bp.route("/teachers", methods=["GET"])
@login_required
def teachers_page():
    return render_template("teachers.html")


@teacher_bp.route("/availability", methods=["GET"])
@login_required
def availability_page():
    return render_template("availability.html")


@teacher_bp.route("/api/teachers", methods=["GET"])
@login_required
def list_teachers():
    return jsonify([t.to_dict() for t in Teacher.query.all()])


@teacher_bp.route("/api/teachers", methods=["POST"])
@role_required("admin")
def create_teacher():
    payload = request.get_json(force=True)
    if not payload.get("name") or not payload.get("email") or not payload.get("department_id"):
        return jsonify({"error": "name, email and department_id are required"}), 400
    if not Department.query.get(payload["department_id"]):
        return jsonify({"error": "Invalid department_id"}), 400
    if Teacher.query.filter_by(email=payload["email"]).first():
        return jsonify({"error": "email already exists"}), 409

    teacher = Teacher(
        name=payload["name"], email=payload["email"],
        department_id=payload["department_id"],
        max_hours_per_week=payload.get("max_hours_per_week", 18),
    )
    db.session.add(teacher)
    db.session.commit()
    return jsonify(teacher.to_dict()), 201


@teacher_bp.route("/api/teachers/<int:teacher_id>", methods=["PUT"])
@role_required("admin")
def update_teacher(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)
    payload = request.get_json(force=True)
    for field in ["name", "email", "department_id", "max_hours_per_week"]:
        if field in payload:
            setattr(teacher, field, payload[field])
    db.session.commit()
    return jsonify(teacher.to_dict())


@teacher_bp.route("/api/teachers/<int:teacher_id>", methods=["DELETE"])
@role_required("admin")
def delete_teacher(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)
    db.session.delete(teacher)
    db.session.commit()
    return jsonify({"message": "Teacher deleted"})


@teacher_bp.route("/api/teachers/<int:teacher_id>/timetable", methods=["GET"])
@login_required
def teacher_timetable(teacher_id):
    active_run = GenerationRun.query.filter_by(is_active=True).first()
    if not active_run:
        return jsonify({"entries": [], "message": "No active timetable has been generated yet."})
    entries = TimetableEntry.query.filter_by(
        generation_run_id=active_run.id, teacher_id=teacher_id
    ).all()
    return jsonify({"entries": [e.to_dict() for e in entries]})


# ------------------------------------------------------------- availability
@teacher_bp.route("/api/teacher-availability", methods=["GET"])
@login_required
def get_availability():
    teacher_id = request.args.get("teacher_id", type=int)
    if not teacher_id:
        return jsonify({"error": "teacher_id is required"}), 400
    rows = TeacherAvailability.query.filter_by(teacher_id=teacher_id).all()
    by_slot = {r.time_slot_id: r for r in rows}
    result = []
    for slot in TimeSlot.query.order_by(TimeSlot.day, TimeSlot.period_number).all():
        row = by_slot.get(slot.id)
        result.append({
            "time_slot_id": slot.id,
            "day": slot.day,
            "period_number": slot.period_number,
            "start_time": slot.start_time,
            "end_time": slot.end_time,
            "is_break": slot.is_break,
            "available": row.available if row else True,
            "preferred": row.preferred if row else False,
        })
    return jsonify(result)


@teacher_bp.route("/api/teacher-availability", methods=["POST"])
@role_required("admin", "teacher")
def set_availability():
    payload = request.get_json(force=True)
    teacher_id = payload.get("teacher_id")
    time_slot_id = payload.get("time_slot_id")
    if not teacher_id or not time_slot_id:
        return jsonify({"error": "teacher_id and time_slot_id are required"}), 400

    row = TeacherAvailability.query.filter_by(
        teacher_id=teacher_id, time_slot_id=time_slot_id
    ).first()
    if not row:
        row = TeacherAvailability(teacher_id=teacher_id, time_slot_id=time_slot_id)
        db.session.add(row)
    row.available = bool(payload.get("available", True))
    row.preferred = bool(payload.get("preferred", False))
    db.session.commit()
    return jsonify({"message": "Availability updated"})
