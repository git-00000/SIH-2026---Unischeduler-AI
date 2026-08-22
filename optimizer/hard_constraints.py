"""
Hard constraints -- a feasible CP-SAT solution can NEVER violate these.
Because variables are only created for eligible (teacher, room, slot)
combinations (see variables.py), constraints 4 (teacher availability), 5
(room capacity) and 6 (lab requirement) are already guaranteed by
construction. This module implements the remaining clash / coverage rules.

Implements SIH spec constraints:
 1. Teacher clash
 2. Room clash
 3. Student/group clash (covers multidisciplinary cross-department clashes)
 4. Teacher availability          -> by construction (variables.py)
 5. Room capacity                 -> by construction (variables.py)
 6. Lab requirement                -> by construction (variables.py)
 7. Course weekly hours (exact count)
 8. Teacher-course compatibility   -> by construction (only offerings used)
 9. Student course selection       -> by construction (only selections used)
10. No duplicate assignment        -> guaranteed by boolean formulation +
                                       the clash constraints below
"""


def apply_hard_constraints(cp_model, x, index, data):
    """Adds all hard constraints to cp_model. Returns (used_group, used_teacher)
    boolean-variable dicts that soft_constraints.py reuses to avoid rebuilding
    the same aggregation logic."""

    # --- Constraint 7: exact weekly hours per (group, course) ---
    for (g, c), keys in index["by_group_course"].items():
        hours = data["courses"][c]["hours_per_week"]
        cp_model.Add(sum(x[k] for k in keys) == hours)

    # --- Constraint 1: teacher cannot teach two things at once ---
    used_teacher = {}
    for (t, s), keys in index["by_teacher_slot"].items():
        used = cp_model.NewBoolVar(f"used_t{t}_s{s}")
        cp_model.Add(sum(x[k] for k in keys) == used)
        used_teacher[(t, s)] = used

    # --- Constraint 2: room cannot host two classes at once ---
    for (r, s), keys in index["by_room_slot"].items():
        cp_model.Add(sum(x[k] for k in keys) <= 1)

    # --- Constraint 3: a student group cannot attend two courses at once
    #     (this is exactly what protects multidisciplinary selections) ---
    used_group = {}
    for (g, s), keys in index["by_group_slot"].items():
        used = cp_model.NewBoolVar(f"used_g{g}_s{s}")
        cp_model.Add(sum(x[k] for k in keys) == used)
        used_group[(g, s)] = used

    return used_group, used_teacher
