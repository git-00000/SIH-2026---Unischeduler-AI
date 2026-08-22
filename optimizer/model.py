"""
Assembles the complete CP-SAT model: variables + hard constraints +
soft constraints + objective. This is the single entry point used by
timetable_generator.py so that Flask routes never touch OR-Tools directly.
"""
from ortools.sat.python import cp_model as cp_model_module

from optimizer.variables import build_variables
from optimizer.hard_constraints import apply_hard_constraints
from optimizer.soft_constraints import build_soft_terms
from optimizer.objective import apply_objective


def build_model(data, cfg, previous_entries=None):
    """
    data: dict bundle described in variables.py
    cfg:  dict of weight/target settings (see config.Config)
    previous_entries: optional list of (g, c, t, r, s) tuples from a prior
                       GenerationRun -- used by the re-optimization workflow
                       to bias the solver towards minimal disruption.

    Returns: (cp_model, x, index, used_group, used_teacher, meta, soft_terms)
    soft_terms is the list of (weight, badness_var) tuples used to build the
    objective -- returned so the caller can report the TRUE soft-constraint
    violation count separately from the raw objective value (which, during
    re-optimization, also contains a negative "preserve previous assignment"
    bonus term that must never be shown to the user as a conflict count).
    """
    model = cp_model_module.CpModel()

    x, index = build_variables(model, data)

    if not x:
        meta = {"num_variables": 0, "num_constraints": 0, "feasible_pairs": 0}
        return model, x, index, {}, {}, meta, []

    used_group, used_teacher = apply_hard_constraints(model, x, index, data)

    soft_terms = build_soft_terms(model, x, index, used_group, used_teacher, data, cfg)

    preserve_terms = None
    if previous_entries:
        preserve_terms = [x[key] for key in previous_entries if key in x]

    apply_objective(model, soft_terms, preserve_terms=preserve_terms)

    meta = {
        "num_variables": len(x) + len(used_group) + len(used_teacher) + len(soft_terms),
        "num_constraints": (
            len(index["by_group_course"])   # weekly-hours constraints
            + len(index["by_teacher_slot"])  # teacher clash
            + len(index["by_room_slot"])     # room clash
            + len(index["by_group_slot"])    # group clash
        ),
        "feasible_pairs": len(index["by_group_course"]),
    }
    return model, x, index, used_group, used_teacher, meta, soft_terms
