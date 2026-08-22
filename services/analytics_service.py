"""
Analytics/dashboard aggregation. Pure read queries -- no optimizer calls.
"""
from collections import Counter
from database.models import (
    Student, Teacher, Course, Room, StudentGroup, GenerationRun,
    TimetableEntry, Department,
)


def get_dashboard_summary():
    active_run = GenerationRun.query.filter_by(is_active=True).order_by(
        GenerationRun.timestamp.desc()).first()

    multidisciplinary_courses = Course.query.filter_by(course_type="Multidisciplinary").count()

    summary = {
        "total_students": Student.query.count(),
        "total_teachers": Teacher.query.count(),
        "total_courses": Course.query.count(),
        "total_rooms": Room.query.count(),
        "total_groups": StudentGroup.query.count(),
        "multidisciplinary_courses": multidisciplinary_courses,
        "hard_conflicts": active_run.hard_conflicts if active_run else None,
        "soft_conflicts": active_run.soft_conflicts if active_run else None,
        "optimization_score": active_run.objective_score if active_run else None,
        "last_generation_time": active_run.timestamp.isoformat() if active_run else None,
        "last_generation_duration": active_run.generation_time if active_run else None,
        "active_run_id": active_run.id if active_run else None,
    }

    if active_run:
        entries = TimetableEntry.query.filter_by(generation_run_id=active_run.id).all()
        total_rooms = Room.query.count()
        total_teachers = Teacher.query.count()
        used_room_slots = len({(e.room_id, e.time_slot_id) for e in entries})
        used_teacher_slots = len({(e.teacher_id, e.time_slot_id) for e in entries})
        from database.models import TimeSlot
        total_slots = TimeSlot.query.filter_by(is_break=False).count()
        summary["room_utilization"] = round(
            100 * used_room_slots / (total_rooms * total_slots), 1
        ) if total_rooms and total_slots else 0
        summary["teacher_utilization"] = round(
            100 * used_teacher_slots / (total_teachers * total_slots), 1
        ) if total_teachers and total_slots else 0
    else:
        summary["room_utilization"] = 0
        summary["teacher_utilization"] = 0

    return summary


def get_chart_data():
    active_run = GenerationRun.query.filter_by(is_active=True).order_by(
        GenerationRun.timestamp.desc()).first()

    course_type_counts = Counter(c.course_type for c in Course.query.all())

    dept_course_counts = Counter()
    for c in Course.query.all():
        dept = Department.query.get(c.department_id)
        dept_course_counts[dept.code if dept else "?"] += 1

    room_utilization = []
    teacher_workload = []
    daily_distribution = Counter()

    if active_run:
        entries = TimetableEntry.query.filter_by(generation_run_id=active_run.id).all()
        room_counts = Counter(e.room_id for e in entries)
        for r in Room.query.all():
            room_utilization.append({"room": r.room_number, "classes": room_counts.get(r.id, 0)})

        teacher_counts = Counter(e.teacher_id for e in entries)
        for t in Teacher.query.all():
            if teacher_counts.get(t.id):
                teacher_workload.append({"teacher": t.name, "classes": teacher_counts.get(t.id, 0)})

        for e in entries:
            daily_distribution[e.time_slot.day] += 1

    return {
        "course_type_distribution": [{"type": k, "count": v} for k, v in course_type_counts.items()],
        "department_course_distribution": [{"department": k, "count": v} for k, v in dept_course_counts.items()],
        "room_utilization": room_utilization,
        "teacher_workload": teacher_workload,
        "daily_distribution": [{"day": d, "count": c} for d, c in daily_distribution.items()],
    }
