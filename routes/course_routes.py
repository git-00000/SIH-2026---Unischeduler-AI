"""
Course CRUD + course-selection (the table that drives NEP-2020
multidisciplinary enrolment) + course-offering (teacher qualification) APIs.
"""
from flask import Blueprint, request, jsonify, render_template

from database.db import db
from database.models import (
    Course, Department, CourseOffering, Teacher, StudentCourseSelection,
    StudentGroup, COURSE_TYPES,
)
from routes.auth_routes import login_required, role_required

course_bp = Blueprint("courses", __name__)


# ---------------------------------------------------------------- pages ----
@course_bp.route("/courses", methods=["GET"])
@login_required
def courses_page():
    return render_template("courses.html", course_types=COURSE_TYPES)


@course_bp.route("/course-selection", methods=["GET"])
@login_required
def course_selection_page():
    return render_template("course_selection.html")


# ------------------------------------------------------------------ API ----
@course_bp.route("/api/courses", methods=["GET"])
@login_required
def list_courses():
    dept_id = request.args.get("department_id", type=int)
    q = Course.query
    if dept_id:
        q = q.filter_by(department_id=dept_id)
    return jsonify([c.to_dict() for c in q.all()])


@course_bp.route("/api/courses", methods=["POST"])
@role_required("admin")
def create_course():
    payload = request.get_json(force=True)
    required = ["course_code", "name", "department_id", "course_type", "hours_per_week"]
    missing = [f for f in required if not payload.get(f) and payload.get(f) != 0]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    if not Department.query.get(payload["department_id"]):
        return jsonify({"error": "Invalid department_id"}), 400
    if payload["course_type"] not in COURSE_TYPES:
        return jsonify({"error": f"course_type must be one of {COURSE_TYPES}"}), 400
    if Course.query.filter_by(course_code=payload["course_code"]).first():
        return jsonify({"error": "course_code already exists"}), 409

    course = Course(
        course_code=payload["course_code"],
        name=payload["name"],
        department_id=payload["department_id"],
        course_type=payload["course_type"],
        credits=payload.get("credits", 3),
        hours_per_week=payload["hours_per_week"],
        requires_lab=bool(payload.get("requires_lab", False)),
        semester=payload.get("semester", 1),
        capacity=payload.get("capacity", 60),
    )
    db.session.add(course)
    db.session.commit()
    return jsonify(course.to_dict()), 201


@course_bp.route("/api/courses/<int:course_id>", methods=["PUT"])
@role_required("admin")
def update_course(course_id):
    course = Course.query.get_or_404(course_id)
    payload = request.get_json(force=True)
    for field in ["course_code", "name", "department_id", "course_type", "credits",
                  "hours_per_week", "requires_lab", "semester", "capacity"]:
        if field in payload:
            setattr(course, field, payload[field])
    db.session.commit()
    return jsonify(course.to_dict())


@course_bp.route("/api/courses/<int:course_id>", methods=["DELETE"])
@role_required("admin")
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    db.session.delete(course)
    db.session.commit()
    return jsonify({"message": "Course deleted"})


# ---------------------------------------------------------- offerings ----
@course_bp.route("/api/course-offerings", methods=["GET"])
@login_required
def list_offerings():
    course_id = request.args.get("course_id", type=int)
    q = CourseOffering.query
    if course_id:
        q = q.filter_by(course_id=course_id)
    result = []
    for o in q.all():
        teacher = Teacher.query.get(o.teacher_id)
        course = Course.query.get(o.course_id)
        result.append({
            "id": o.id, "course_id": o.course_id, "teacher_id": o.teacher_id,
            "teacher_name": teacher.name if teacher else None,
            "course_name": course.name if course else None,
            "academic_term": o.academic_term,
        })
    return jsonify(result)


@course_bp.route("/api/course-offerings", methods=["POST"])
@role_required("admin")
def create_offering():
    payload = request.get_json(force=True)
    if not payload.get("course_id") or not payload.get("teacher_id"):
        return jsonify({"error": "course_id and teacher_id are required"}), 400
    if not Course.query.get(payload["course_id"]):
        return jsonify({"error": "Invalid course_id"}), 400
    if not Teacher.query.get(payload["teacher_id"]):
        return jsonify({"error": "Invalid teacher_id"}), 400

    offering = CourseOffering(
        course_id=payload["course_id"],
        teacher_id=payload["teacher_id"],
        academic_term=payload.get("academic_term", "2026-ODD"),
    )
    db.session.add(offering)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "This teacher is already an offering for this course/term"}), 409
    return jsonify({"id": offering.id}), 201


@course_bp.route("/api/course-offerings/<int:offering_id>", methods=["DELETE"])
@role_required("admin")
def delete_offering(offering_id):
    offering = CourseOffering.query.get_or_404(offering_id)
    db.session.delete(offering)
    db.session.commit()
    return jsonify({"message": "Offering deleted"})


# --------------------------------------------------- course selection ----
@course_bp.route("/api/course-selection", methods=["GET"])
@login_required
def list_selections():
    group_id = request.args.get("group_id", type=int)
    q = StudentCourseSelection.query
    if group_id:
        q = q.filter_by(group_id=group_id)
    result = []
    for s in q.all():
        course = Course.query.get(s.course_id)
        group = StudentGroup.query.get(s.group_id)
        result.append({
            "id": s.id, "group_id": s.group_id, "group_name": group.name if group else None,
            "course_id": s.course_id, "course_code": course.course_code if course else None,
            "course_name": course.name if course else None,
            "course_type": course.course_type if course else None,
            "is_cross_department": (
                course.department_id != group.department_id if course and group else False
            ),
            "semester": s.semester,
        })
    return jsonify(result)


@course_bp.route("/api/course-selection", methods=["POST"])
@role_required("admin")
def create_selection():
    payload = request.get_json(force=True)
    group_id, course_id = payload.get("group_id"), payload.get("course_id")
    if not group_id or not course_id:
        return jsonify({"error": "group_id and course_id are required"}), 400
    group = StudentGroup.query.get(group_id)
    course = Course.query.get(course_id)
    if not group or not course:
        return jsonify({"error": "Invalid group_id or course_id"}), 400

    if StudentCourseSelection.query.filter_by(group_id=group_id, course_id=course_id).first():
        return jsonify({"error": "This group has already selected this course"}), 409

    selection = StudentCourseSelection(
        group_id=group_id, course_id=course_id, semester=payload.get("semester", group.semester)
    )
    db.session.add(selection)
    db.session.commit()
    return jsonify({"id": selection.id}), 201


@course_bp.route("/api/course-selection/<int:selection_id>", methods=["DELETE"])
@role_required("admin")
def delete_selection(selection_id):
    selection = StudentCourseSelection.query.get_or_404(selection_id)
    db.session.delete(selection)
    db.session.commit()
    return jsonify({"message": "Selection removed"})
