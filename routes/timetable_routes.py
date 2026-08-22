"""
The heart of the demo: trigger AI generation, re-optimize (what-if),
view the generated timetable, view conflicts, and the "AI Optimization
Insights" transparency page that SIH judges care about.
"""
from flask import Blueprint, request, jsonify, render_template, current_app

from database.db import db
from database.models import (
    GenerationRun, TimetableEntry, Conflict, Room, Teacher, StudentGroup,
)
from routes.auth_routes import login_required, role_required
from services.timetable_service import generate_timetable, naive_baseline_conflicts

timetable_bp = Blueprint("timetable", __name__)


@timetable_bp.route("/generate", methods=["GET"])
@login_required
def generate_page():
    return render_template("generate.html")


@timetable_bp.route("/timetable", methods=["GET"])
@login_required
def timetable_page():
    return render_template("timetable.html")


@timetable_bp.route("/conflicts", methods=["GET"])
@login_required
def conflicts_page():
    return render_template("conflicts.html")


@timetable_bp.route("/analytics", methods=["GET"])
@login_required
def analytics_page():
    return render_template("analytics.html")


@timetable_bp.route("/insights", methods=["GET"])
@login_required
def insights_page():
    return render_template("insights.html")


# ------------------------------------------------------------------ API ----
@timetable_bp.route("/api/generate-timetable", methods=["POST"])
@role_required("admin")
def api_generate_timetable():
    unavailable_rooms = [r.id for r in Room.query.filter_by(is_available=False).all()]
    run = generate_timetable(current_app.config, unavailable_room_ids=unavailable_rooms)
    return jsonify({
        "run": run.to_dict(),
        "message": (
            "Timetable generated successfully." if run.status in ("OPTIMAL", "FEASIBLE")
            else f"Generation failed: {run.notes}"
        ),
    }), (201 if run.status in ("OPTIMAL", "FEASIBLE") else 422)


@timetable_bp.route("/api/reoptimize", methods=["POST"])
@role_required("admin")
def api_reoptimize():
    """What-if re-optimization: pass in newly-unavailable room/teacher ids and
    the previous run to preserve as much of the existing schedule as
    possible while resolving the new constraint."""
    payload = request.get_json(silent=True) or {}
    unavailable_room_ids = payload.get("unavailable_room_ids", [])
    unavailable_teacher_ids = payload.get("unavailable_teacher_ids", [])

    # also respect any rooms toggled unavailable via /api/rooms/<id>/toggle-availability
    unavailable_room_ids = list(set(unavailable_room_ids) | {
        r.id for r in Room.query.filter_by(is_available=False).all()
    })

    previous_run = GenerationRun.query.filter_by(is_active=True).order_by(
        GenerationRun.timestamp.desc()).first()

    run = generate_timetable(
        current_app.config,
        unavailable_room_ids=unavailable_room_ids,
        unavailable_teacher_ids=unavailable_teacher_ids,
        previous_run_id=previous_run.id if previous_run else None,
        preserve=True,
    )
    preserved = 0
    if previous_run and run.status in ("OPTIMAL", "FEASIBLE"):
        prev_keys = {
            (e.group_id, e.course_id, e.teacher_id, e.room_id, e.time_slot_id)
            for e in TimetableEntry.query.filter_by(generation_run_id=previous_run.id).all()
        }
        new_keys = {
            (e.group_id, e.course_id, e.teacher_id, e.room_id, e.time_slot_id)
            for e in TimetableEntry.query.filter_by(generation_run_id=run.id).all()
        }
        preserved = len(prev_keys & new_keys)

    return jsonify({
        "run": run.to_dict(),
        "preserved_assignments": preserved,
        "message": (
            "Timetable re-optimized while preserving as many existing "
            "assignments as possible." if run.status in ("OPTIMAL", "FEASIBLE")
            else f"Re-optimization failed: {run.notes}"
        ),
    }), (200 if run.status in ("OPTIMAL", "FEASIBLE") else 422)


@timetable_bp.route("/api/timetable", methods=["GET"])
@login_required
def api_get_timetable():
    run_id = request.args.get("run_id", type=int)
    group_id = request.args.get("group_id", type=int)
    teacher_id = request.args.get("teacher_id", type=int)

    run = GenerationRun.query.get(run_id) if run_id else GenerationRun.query.filter_by(
        is_active=True).order_by(GenerationRun.timestamp.desc()).first()

    if not run:
        return jsonify({"entries": [], "run": None, "message": "No timetable has been generated yet."})

    q = TimetableEntry.query.filter_by(generation_run_id=run.id)
    if group_id:
        q = q.filter_by(group_id=group_id)
    if teacher_id:
        q = q.filter_by(teacher_id=teacher_id)

    return jsonify({"entries": [e.to_dict() for e in q.all()], "run": run.to_dict()})


@timetable_bp.route("/api/generation-runs", methods=["GET"])
@login_required
def api_generation_runs():
    runs = GenerationRun.query.order_by(GenerationRun.timestamp.desc()).limit(20).all()
    return jsonify([r.to_dict() for r in runs])


@timetable_bp.route("/api/conflicts", methods=["GET"])
@login_required
def api_conflicts():
    run_id = request.args.get("run_id", type=int)
    stage = request.args.get("stage")
    run = GenerationRun.query.get(run_id) if run_id else GenerationRun.query.filter_by(
        is_active=True).order_by(GenerationRun.timestamp.desc()).first()
    if not run:
        return jsonify([])
    q = Conflict.query.filter_by(generation_run_id=run.id)
    if stage:
        q = q.filter_by(stage=stage)
    return jsonify([c.to_dict() for c in q.all()])


@timetable_bp.route("/api/insights", methods=["GET"])
@login_required
def api_insights():
    run = GenerationRun.query.filter_by(is_active=True).order_by(
        GenerationRun.timestamp.desc()).first()
    if not run:
        return jsonify({"message": "No timetable has been generated yet."})

    naive_hard, naive_soft = naive_baseline_conflicts(current_app.config)
    before_total = naive_hard + naive_soft
    after_total = (run.hard_conflicts or 0) + (run.soft_conflicts or 0)
    improvement = 0
    if before_total > 0:
        improvement = round(100 * (before_total - after_total) / before_total, 1)

    return jsonify({
        "run": run.to_dict(),
        "solver_status": run.status,
        "num_variables": run.num_variables,
        "num_constraints": run.num_constraints,
        "objective_score": run.objective_score,
        "generation_time_seconds": run.generation_time,
        "before": {"hard_conflicts": naive_hard, "soft_conflicts": naive_soft},
        "after": {"hard_conflicts": run.hard_conflicts, "soft_conflicts": run.soft_conflicts},
        "optimization_improvement_percent": improvement,
        "methodology": (
            "AI is implemented using Google OR-Tools CP-SAT constraint "
            "programming / constraint optimization -- not conventional "
            "machine learning (no CNN/LSTM/Random Forest is used)."
        ),
    })
