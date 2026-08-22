"""
Decision-variable construction for the CP-SAT timetable model.

Variable definition
--------------------
x[(group_id, course_id, teacher_id, room_id, slot_id)] = BoolVar

1 -> this course session for this student group is taught by this teacher,
     in this room, at this timeslot.
0 -> not selected.

We do NOT create a variable for every mathematically possible combination --
only for combinations that could ever be legal. This keeps the model small
and keeps every hard constraint about *eligibility* (qualified teacher,
room big enough, correct room type, teacher available) automatically
satisfied by construction, rather than needing extra constraints.
"""
from database.models import LAB_ROOM_TYPES


def build_variables(cp_model, data):
    """
    data is a plain-dict bundle produced by services/timetable_service.py:
        groups:      {group_id: {"strength": int}}
        courses:     {course_id: {"hours_per_week": int, "requires_lab": bool, "capacity": int}}
        rooms:       {room_id: {"capacity": int, "room_type": str}}
        slots:       {slot_id: {"day": str, "period_number": int}}   (break slots already excluded)
        offerings:   set of (course_id, teacher_id)  -- qualified teacher for a course
        selections:  set of (group_id, course_id)    -- group has selected/must-take this course
        teacher_unavailable: set of (teacher_id, slot_id)
        unavailable_rooms: set of room_id
        unavailable_teachers: set of teacher_id (fully unavailable, e.g. on leave)

    Returns:
        x: dict[(g, c, t, r, s)] -> BoolVar
        index: helper lookup dicts for building constraints efficiently
    """
    x = {}

    # Helper indices for fast constraint construction later.
    by_group_slot = {}      # (g, s) -> list of var keys
    by_teacher_slot = {}    # (t, s) -> list of var keys
    by_room_slot = {}       # (r, s) -> list of var keys
    by_group_course = {}    # (g, c) -> list of var keys
    by_teacher = {}         # t -> list of var keys (for workload)
    by_group_course_day = {}  # (g, c, day) -> list of var keys

    for (g, c) in data["selections"]:
        course = data["courses"][c]
        group = data["groups"][g]

        qualified_teachers = [t for (cc, t) in data["offerings"] if cc == c]
        if not qualified_teachers:
            continue  # no teacher can teach this course -- reported as a conflict elsewhere

        eligible_rooms = []
        for r, room in data["rooms"].items():
            if r in data["unavailable_rooms"]:
                continue
            if room["capacity"] < group["strength"]:
                continue
            if course["requires_lab"] and room["room_type"] not in LAB_ROOM_TYPES:
                continue
            if not course["requires_lab"] and room["room_type"] in LAB_ROOM_TYPES:
                continue
            eligible_rooms.append(r)
        if not eligible_rooms:
            continue  # no suitable room -- reported as a conflict elsewhere

        for t in qualified_teachers:
            if t in data["unavailable_teachers"]:
                continue
            for s, slot in data["slots"].items():
                if (t, s) in data["teacher_unavailable"]:
                    continue
                for r in eligible_rooms:
                    key = (g, c, t, r, s)
                    var = cp_model.NewBoolVar(f"x_g{g}_c{c}_t{t}_r{r}_s{s}")
                    x[key] = var

                    by_group_slot.setdefault((g, s), []).append(key)
                    by_teacher_slot.setdefault((t, s), []).append(key)
                    by_room_slot.setdefault((r, s), []).append(key)
                    by_group_course.setdefault((g, c), []).append(key)
                    by_teacher.setdefault(t, []).append(key)
                    day = slot["day"]
                    by_group_course_day.setdefault((g, c, day), []).append(key)

    index = {
        "by_group_slot": by_group_slot,
        "by_teacher_slot": by_teacher_slot,
        "by_room_slot": by_room_slot,
        "by_group_course": by_group_course,
        "by_teacher": by_teacher,
        "by_group_course_day": by_group_course_day,
    }
    return x, index
