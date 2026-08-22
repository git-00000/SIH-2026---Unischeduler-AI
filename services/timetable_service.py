"""
Service layer that connects Flask routes to the AI optimization engine and
the database. Routes should never talk to SQLAlchemy models for timetable
generation directly -- they call into this module.
"""
from datetime import datetime, timezone

from database.db import db
from database.models import (
    StudentGroup, Course, Teacher, Room, TimeSlot, TeacherAvailability,
    CourseOffering, StudentCourseSelection, GenerationRun, TimetableEntry,
    Conflict,
)
from optimizer.timetable_generator import TimetableGenerator
from services.conflict_service import detect_pre_generation_conflicts, detect_entry_conflicts


def build_optimizer_data(unavailable_room_ids=None, unavailable_teacher_ids=None):
    """Pulls the current database state into the plain-dict bundle the
    optimizer package expects. Keeping this conversion in one place means
    the optimizer itself has zero SQLAlchemy dependencies and can be unit
    tested with plain Python dicts (see tests/test_optimizer.py)."""
    unavailable_room_ids = set(unavailable_room_ids or [])
    unavailable_teacher_ids = set(unavailable_teacher_ids or [])

    groups = {g.id: {"strength": g.strength} for g in StudentGroup.query.all()}
    courses = {
        c.id: {
            "hours_per_week": c.hours_per_week,
            "requires_lab": c.requires_lab,
            "capacity": c.capacity,
        }
        for c in Course.query.all()
    }
    rooms = {
        r.id: {"capacity": r.capacity, "room_type": r.room_type}
        for r in Room.query.all()
        if r.is_available
    }
    # Explicitly-marked-unavailable rooms are removed from the model too.
    for rid in list(unavailable_room_ids):
        rooms.pop(rid, None)

    slots = {
        s.id: {"day": s.day, "period_number": s.period_number}
        for s in TimeSlot.query.filter_by(is_break=False).all()
    }

    offerings = {(o.course_id, o.teacher_id) for o in CourseOffering.query.all()}
    selections = {(sel.group_id, sel.course_id) for sel in StudentCourseSelection.query.all()}

    teacher_unavailable = {
        (a.teacher_id, a.time_slot_id)
        for a in TeacherAvailability.query.filter_by(available=False).all()
    }

    data = {
        "groups": groups,
        "courses": courses,
        "rooms": rooms,
        "slots": slots,
        "offerings": offerings,
        "selections": selections,
        "teacher_unavailable": teacher_unavailable,
        "unavailable_rooms": unavailable_room_ids & set(r.id for r in Room.query.all()),
        "unavailable_teachers": unavailable_teacher_ids,
        # lookup tables used purely for human-readable conflict text
        "teacher_names": {t.id: t.name for t in Teacher.query.all()},
        "room_names": {r.id: r.room_number for r in Room.query.all()},
        "group_names": {g.id: g.name for g in StudentGroup.query.all()},
        "course_names": {c.id: f"{c.course_code} {c.name}" for c in Course.query.all()},
    }
    return data


def _cfg_dict(app_config):
    return {
        "WEIGHT_GROUP_GAP": app_config["WEIGHT_GROUP_GAP"],
        "WEIGHT_TEACHER_GAP": app_config["WEIGHT_TEACHER_GAP"],
        "WEIGHT_DAILY_OVERLOAD": app_config["WEIGHT_DAILY_OVERLOAD"],
        "WEIGHT_CONSECUTIVE_RUN": app_config["WEIGHT_CONSECUTIVE_RUN"],
        "WEIGHT_SAME_DAY_REPEAT": app_config["WEIGHT_SAME_DAY_REPEAT"],
        "DAILY_TARGET_PERIODS": app_config["DAILY_TARGET_PERIODS"],
        "MAX_CONSECUTIVE_BEFORE_PENALTY": app_config["MAX_CONSECUTIVE_BEFORE_PENALTY"],
        "SOLVER_TIME_LIMIT_SECONDS": app_config["SOLVER_TIME_LIMIT_SECONDS"],
    }


def generate_timetable(app_config, unavailable_room_ids=None, unavailable_teacher_ids=None,
                        previous_run_id=None, preserve=False):
    """Runs the full pipeline: build data -> pre-generation conflicts ->
    CP-SAT optimize -> persist GenerationRun + TimetableEntry + Conflict rows.
    Returns the created GenerationRun."""
    data = build_optimizer_data(unavailable_room_ids, unavailable_teacher_ids)
    cfg = _cfg_dict(app_config)

    pre_conflicts = detect_pre_generation_conflicts(data)

    previous_entries = None
    if preserve and previous_run_id:
        prev = TimetableEntry.query.filter_by(generation_run_id=previous_run_id).all()
        previous_entries = [
            (e.group_id, e.course_id, e.teacher_id, e.room_id, e.time_slot_id) for e in prev
        ]

    generator = TimetableGenerator(data, cfg)
    result = generator.generate(previous_entries=previous_entries)

    run = GenerationRun(
        timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
        status=result["status_name"],
        objective_score=result["objective_value"],
        generation_time=result["elapsed_seconds"],
        num_variables=result["meta"].get("num_variables", 0),
        num_constraints=result["meta"].get("num_constraints", 0),
        conflicts_before=len(pre_conflicts),
        notes=result["reason"],
    )
    db.session.add(run)
    db.session.flush()  # get run.id without committing yet

    for pc in pre_conflicts:
        db.session.add(Conflict(
            generation_run_id=run.id, conflict_type=pc["conflict_type"],
            severity=pc["severity"], description=pc["description"], stage="before",
        ))

    hard_after = 0
    if result["entries"]:
        for e in result["entries"]:
            db.session.add(TimetableEntry(
                generation_run_id=run.id,
                course_id=e["course_id"], teacher_id=e["teacher_id"],
                room_id=e["room_id"], group_id=e["group_id"],
                time_slot_id=e["time_slot_id"],
            ))
        after_conflicts = detect_entry_conflicts(result["entries"], data, stage="after")
        hard_after = len([c for c in after_conflicts if c["severity"] == "hard"])
        for ac in after_conflicts:
            db.session.add(Conflict(
                generation_run_id=run.id, conflict_type=ac["conflict_type"],
                severity=ac["severity"], description=ac["description"], stage="after",
            ))

    run.hard_conflicts = hard_after
    # soft_conflicts is the TRUE weighted count of soft-constraint violations
    # remaining -- computed from soft_terms alone in the optimizer, so it is
    # never contaminated by the re-optimization "preserve assignment" bonus
    # (which can make the raw objective negative but is not itself a conflict).
    run.soft_conflicts = (
        int(round(result["soft_conflict_score"])) if result["soft_conflict_score"] is not None else 0
    )

    if result["entries"]:
        GenerationRun.query.update({GenerationRun.is_active: False})
        run.is_active = True

    db.session.commit()
    return run


def naive_baseline_conflicts(app_config):
    """Used only by the AI Insights page to show a believable 'before AI'
    conflict count for comparison. Does not touch the database."""
    data = build_optimizer_data()
    cfg = _cfg_dict(app_config)
    generator = TimetableGenerator(data, cfg)
    naive_entries = generator.naive_baseline()
    conflicts = detect_entry_conflicts(naive_entries, data, stage="before")
    hard = len([c for c in conflicts if c["severity"] == "hard"])
    return hard, len(conflicts) - hard
