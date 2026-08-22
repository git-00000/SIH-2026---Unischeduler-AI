"""
Conflict detection service.

Used in two places:
1. Before generation -- scans raw data (course selections, teacher
   qualifications, room capacities) for structural problems that would make
   optimization fail or need attention.
2. After generation -- scans a concrete list of TimetableEntry-shaped dicts
   for hard-constraint violations (should always be zero for a CP-SAT
   OPTIMAL/FEASIBLE result) and reports soft-constraint issues in plain
   English for the "AI Optimization Insights" page.
"""
from collections import defaultdict


def detect_pre_generation_conflicts(data):
    """Structural conflicts visible before any solving happens."""
    conflicts = []

    for (g, c) in data["selections"]:
        group = data["groups"][g]
        course = data["courses"][c]

        qualified = [t for (cc, t) in data["offerings"] if cc == c]
        available_qualified = [t for t in qualified if t not in data["unavailable_teachers"]]
        if not available_qualified:
            conflicts.append({
                "conflict_type": "availability",
                "severity": "hard",
                "description": (
                    f"No available qualified teacher found for course "
                    f"'{course.get('name', c)}' needed by group "
                    f"'{group.get('name', g)}'."
                ),
            })

        suitable_rooms = [
            r for r, room in data["rooms"].items()
            if r not in data["unavailable_rooms"]
            and room["capacity"] >= group["strength"]
            and (
                (course["requires_lab"] and room["room_type"] in
                 ("Computer Lab", "Physics Lab", "Chemistry Lab"))
                or (not course["requires_lab"] and room["room_type"] not in
                    ("Computer Lab", "Physics Lab", "Chemistry Lab"))
            )
        ]
        if not suitable_rooms:
            conflicts.append({
                "conflict_type": "capacity",
                "severity": "hard",
                "description": (
                    f"No room of the required type/capacity is available for "
                    f"'{course.get('name', c)}' (group strength "
                    f"{group['strength']}, requires_lab={course['requires_lab']})."
                ),
            })

    return conflicts


def detect_entry_conflicts(entries, data, stage="after"):
    """entries: list of dicts with group_id, course_id, teacher_id, room_id,
    time_slot_id. Detects the classic hard clashes plus capacity issues.
    Works for both the naive baseline (many expected conflicts) and the
    CP-SAT solution (should be zero hard conflicts)."""
    conflicts = []

    teacher_slot = defaultdict(list)
    room_slot = defaultdict(list)
    group_slot = defaultdict(list)

    for e in entries:
        teacher_slot[(e["teacher_id"], e["time_slot_id"])].append(e)
        room_slot[(e["room_id"], e["time_slot_id"])].append(e)
        group_slot[(e["group_id"], e["time_slot_id"])].append(e)

    def slot_label(sid):
        slot = data["slots"].get(sid)
        return f"{slot['day']} period {slot['period_number']}" if slot else str(sid)

    for (t, s), es in teacher_slot.items():
        if len(es) > 1:
            name = data["teacher_names"].get(t, f"Teacher {t}")
            courses = ", ".join(data["course_names"].get(e["course_id"], "?") for e in es)
            conflicts.append({
                "conflict_type": "teacher",
                "severity": "hard",
                "description": f"Teacher conflict: {name} assigned to {len(es)} "
                                f"courses ({courses}) at {slot_label(s)}.",
                "stage": stage,
            })

    for (r, s), es in room_slot.items():
        if len(es) > 1:
            room_no = data["room_names"].get(r, f"Room {r}")
            courses = ", ".join(data["course_names"].get(e["course_id"], "?") for e in es)
            conflicts.append({
                "conflict_type": "room",
                "severity": "hard",
                "description": f"Room conflict: {room_no} assigned to {len(es)} "
                                f"courses ({courses}) at {slot_label(s)}.",
                "stage": stage,
            })

    for (g, s), es in group_slot.items():
        if len(es) > 1:
            gname = data["group_names"].get(g, f"Group {g}")
            courses = ", ".join(data["course_names"].get(e["course_id"], "?") for e in es)
            conflicts.append({
                "conflict_type": "student",
                "severity": "hard",
                "description": f"Student conflict: {gname} has {courses} scheduled "
                                f"simultaneously at {slot_label(s)}.",
                "stage": stage,
            })

    for e in entries:
        group = data["groups"].get(e["group_id"])
        room = data["rooms"].get(e["room_id"])
        if group and room and room["capacity"] < group["strength"]:
            conflicts.append({
                "conflict_type": "capacity",
                "severity": "hard",
                "description": (
                    f"Capacity conflict: {group['strength']} students from "
                    f"{data['group_names'].get(e['group_id'])} assigned to "
                    f"{data['room_names'].get(e['room_id'])} "
                    f"(capacity {room['capacity']})."
                ),
                "stage": stage,
            })

    return conflicts
