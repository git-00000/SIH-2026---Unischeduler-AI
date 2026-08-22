"""
Soft constraints -- these are not forbidden, they are *penalised* in the
objective function so the solver prefers schedules that avoid them.

Implements (from the SIH spec's "as many as practical" list):
 1. Minimize student/group free gaps        -> group_gap_penalties
 2. Minimize teacher free gaps               -> teacher_gap_penalties
 3/4. Avoid too many classes in a single day -> daily_overload_penalties
 5. Spread course periods through the week   -> same_day_repeat_penalties
 9. Avoid long unbroken runs of classes      -> consecutive_run_penalties

Each function returns a list of BoolVar/IntVar "badness" terms. The caller
(objective.py) multiplies each list by its configured weight and adds it to
the objective to minimise.
"""


def _sorted_slots_by_day(data):
    """day -> [slot_id, ...] ordered by period_number."""
    by_day = {}
    for s, slot in data["slots"].items():
        by_day.setdefault(slot["day"], []).append((slot["period_number"], s))
    for day in by_day:
        by_day[day].sort()
        by_day[day] = [s for _, s in by_day[day]]
    return by_day


def _isolated_gap_penalties(cp_model, used, entity_ids, by_day, prefix):
    """Penalise a single free period sandwiched between two occupied periods,
    for every entity (group or teacher) and every day. Uses the standard
    CNF encoding of the implication:
        (occ[p-1] AND NOT occ[p] AND occ[p+1]) => gap_var
    so the solver cannot cheat by leaving gap_var at 0 when a real gap
    exists (it is only ever helpful, never required, to set it to 1)."""
    penalties = []
    for entity in entity_ids:
        for day, slot_list in by_day.items():
            for i in range(1, len(slot_list) - 1):
                prev_s, cur_s, next_s = slot_list[i - 1], slot_list[i], slot_list[i + 1]
                prev_var = used.get((entity, prev_s))
                cur_var = used.get((entity, cur_s))
                next_var = used.get((entity, next_s))
                if prev_var is None or cur_var is None or next_var is None:
                    continue
                gap_var = cp_model.NewBoolVar(f"gap_{prefix}_{entity}_{day}_{i}")
                # prev AND NOT cur AND next  => gap_var
                cp_model.AddBoolOr([prev_var.Not(), cur_var, next_var.Not(), gap_var])
                penalties.append(gap_var)
    return penalties


def _daily_overload_penalties(cp_model, used, entity_ids, by_day, target, prefix):
    penalties = []
    for entity in entity_ids:
        for day, slot_list in by_day.items():
            day_vars = [used[(entity, s)] for s in slot_list if (entity, s) in used]
            if not day_vars:
                continue
            count = cp_model.NewIntVar(0, len(day_vars), f"count_{prefix}_{entity}_{day}")
            cp_model.Add(count == sum(day_vars))
            excess = cp_model.NewIntVar(0, len(day_vars), f"excess_{prefix}_{entity}_{day}")
            cp_model.AddMaxEquality(excess, [count - target, 0])
            penalties.append(excess)
    return penalties


def _consecutive_run_penalties(cp_model, used, entity_ids, by_day, max_run, prefix):
    """Penalise any window of (max_run + 1) consecutive occupied periods."""
    penalties = []
    window = max_run + 1
    for entity in entity_ids:
        for day, slot_list in by_day.items():
            if len(slot_list) < window:
                continue
            for i in range(0, len(slot_list) - window + 1):
                window_slots = slot_list[i:i + window]
                window_vars = [used.get((entity, s)) for s in window_slots]
                if any(v is None for v in window_vars):
                    continue
                run_var = cp_model.NewBoolVar(f"run_{prefix}_{entity}_{day}_{i}")
                # ALL occupied => run_var. CNF: for each v, (NOT v OR run_var) is wrong direction;
                # correct implication (v1 AND v2 AND ... vN) => run_var is:
                # (NOT v1 OR NOT v2 OR ... OR NOT vN OR run_var)
                clause = [v.Not() for v in window_vars] + [run_var]
                cp_model.AddBoolOr(clause)
                penalties.append(run_var)
    return penalties


def build_soft_terms(cp_model, x, index, used_group, used_teacher, data, cfg):
    """Returns a flat list of (weight, badness_var) tuples to minimise."""
    by_day = _sorted_slots_by_day(data)
    group_ids = list(data["groups"].keys())
    teacher_ids = list({t for (_, t) in data["offerings"]})

    terms = []

    group_gap = _isolated_gap_penalties(cp_model, used_group, group_ids, by_day, "grp")
    terms += [(cfg["WEIGHT_GROUP_GAP"], v) for v in group_gap]

    teacher_gap = _isolated_gap_penalties(cp_model, used_teacher, teacher_ids, by_day, "tch")
    terms += [(cfg["WEIGHT_TEACHER_GAP"], v) for v in teacher_gap]

    daily_overload = _daily_overload_penalties(
        cp_model, used_group, group_ids, by_day, cfg["DAILY_TARGET_PERIODS"], "ovl"
    )
    terms += [(cfg["WEIGHT_DAILY_OVERLOAD"], v) for v in daily_overload]

    consecutive = _consecutive_run_penalties(
        cp_model, used_group, group_ids, by_day, cfg["MAX_CONSECUTIVE_BEFORE_PENALTY"], "run"
    )
    terms += [(cfg["WEIGHT_CONSECUTIVE_RUN"], v) for v in consecutive]

    # Same-day repeat: penalise sum(keys) > 1 for a (group, course, day)
    for (g, c, day), keys in index["by_group_course_day"].items():
        if len(keys) <= 1:
            continue
        s = sum(x[k] for k in keys)
        excess = cp_model.NewIntVar(0, len(keys), f"repeat_g{g}_c{c}_{day}")
        cp_model.AddMaxEquality(excess, [s - 1, 0])
        terms.append((cfg["WEIGHT_SAME_DAY_REPEAT"], excess))

    return terms
