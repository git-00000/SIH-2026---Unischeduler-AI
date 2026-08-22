"""
Student + StudentGroup CRUD, plus a student's personalised timetable view.
"""
from flask import Blueprint, request, jsonify, render_template, session

from database.db import db
from database.models import (
    Student, StudentGroup, Department, TimetableEntry, GenerationRun,
    StudentCourseSelection, Course,
)
from routes.auth_routes import login_required, role_required

student_bp = Blueprint("students", __name__)


@student_bp.route("/students", methods=["GET"])
@login_required
def students_page():
    return render_template("students.html")


@student_bp.route("/api/student-groups", methods=["GET"])
@login_required
def list_groups():
    return jsonify([g.to_dict() for g in StudentGroup.query.all()])


@student_bp.route("/api/student-groups", methods=["POST"])
@role_required("admin")
def create_group():
    payload = request.get_json(force=True)
    if not payload.get("name") or not payload.get("department_id") or not payload.get("semester"):
        return jsonify({"error": "name, department_id and semester are required"}), 400
    if not Department.query.get(payload["department_id"]):
        return jsonify({"error": "Invalid department_id"}), 400

    group = StudentGroup(
        name=payload["name"], department_id=payload["department_id"],
        semester=payload["semester"], strength=payload.get("strength", 40),
    )
    db.session.add(group)
    db.session.commit()
    return jsonify(group.to_dict()), 201


@student_bp.route("/api/student-groups/<int:group_id>", methods=["PUT"])
@role_required("admin")
def update_group(group_id):
    group = StudentGroup.query.get_or_404(group_id)
    payload = request.get_json(force=True)
    for field in ["name", "department_id", "semester", "strength"]:
        if field in payload:
            setattr(group, field, payload[field])
    db.session.commit()
    return jsonify(group.to_dict())


@student_bp.route("/api/student-groups/<int:group_id>", methods=["DELETE"])
@role_required("admin")
def delete_group(group_id):
    group = StudentGroup.query.get_or_404(group_id)
    db.session.delete(group)
    db.session.commit()
    return jsonify({"message": "Group deleted"})


@student_bp.route("/api/student-groups/<int:group_id>/timetable", methods=["GET"])
@login_required
def group_timetable(group_id):
    active_run = GenerationRun.query.filter_by(is_active=True).first()
    if not active_run:
        return jsonify({"entries": [], "message": "No active timetable has been generated yet."})
    entries = TimetableEntry.query.filter_by(
        generation_run_id=active_run.id, group_id=group_id
    ).all()
    return jsonify({"entries": [e.to_dict() for e in entries]})


@student_bp.route("/api/students", methods=["GET"])
@login_required
def list_students():
    group_id = request.args.get("group_id", type=int)
    q = Student.query
    if group_id:
        q = q.filter_by(group_id=group_id)
    return jsonify([s.to_dict() for s in q.all()])


@student_bp.route("/api/students", methods=["POST"])
@role_required("admin")
def create_student():
    payload = request.get_json(force=True)
    required = ["name", "roll_number", "department_id", "semester"]
    missing = [f for f in required if not payload.get(f)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    if Student.query.filter_by(roll_number=payload["roll_number"]).first():
        return jsonify({"error": "roll_number already exists"}), 409

    student = Student(
        name=payload["name"], roll_number=payload["roll_number"],
        department_id=payload["department_id"], semester=payload["semester"],
        group_id=payload.get("group_id"),
    )
    db.session.add(student)
    db.session.commit()
    return jsonify(student.to_dict()), 201


@student_bp.route("/api/students/<int:student_id>", methods=["PUT"])
@role_required("admin")
def update_student(student_id):
    student = Student.query.get_or_404(student_id)
    payload = request.get_json(force=True)
    for field in ["name", "roll_number", "department_id", "semester", "group_id"]:
        if field in payload:
            setattr(student, field, payload[field])
    db.session.commit()
    return jsonify(student.to_dict())


@student_bp.route("/api/students/<int:student_id>", methods=["DELETE"])
@role_required("admin")
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    db.session.delete(student)
    db.session.commit()
    return jsonify({"message": "Student deleted"})


@student_bp.route("/api/my/timetable", methods=["GET"])
@login_required
def my_timetable():
    """Convenience endpoint for a logged-in student: resolves their group and
    returns that group's active timetable + their course selections."""
    from database.models import User
    user = User.query.get(session["user_id"])
    if not user or not user.student or not user.student.group_id:
        return jsonify({"entries": [], "message": "No group assigned to this student."})

    group_id = user.student.group_id
    active_run = GenerationRun.query.filter_by(is_active=True).first()
    entries = []
    if active_run:
        entries = [e.to_dict() for e in TimetableEntry.query.filter_by(
            generation_run_id=active_run.id, group_id=group_id).all()]

    selections = StudentCourseSelection.query.filter_by(group_id=group_id).all()
    courses = [Course.query.get(s.course_id).to_dict() for s in selections]

    return jsonify({"entries": entries, "courses": courses, "group_id": group_id})
