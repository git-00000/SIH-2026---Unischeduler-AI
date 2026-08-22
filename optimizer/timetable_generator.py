"""
High level orchestration for timetable generation.

TimetableGenerator.generate() runs the real CP-SAT optimizer and returns a
clean result dict ready to be persisted by services/timetable_service.py.

TimetableGenerator.naive_baseline() builds a deliberately unintelligent
first-fit assignment (no clash checking) purely so the "AI Optimization
Insights" page can show a believable, honestly-labelled *before* picture --
this is never treated as a real usable timetable and is never confused with
the CP-SAT solution.
"""
from itertools import cycle
from ortools.sat.python import cp_model as cp_model_module

from optimizer.model import build_model
from optimizer.solver import solve_model


class TimetableGenerator:
    def __init__(self, data, cfg):
        """data: bundle dict from timetable_service.build_optimizer_data()
        cfg: dict of weights/targets (from Flask app config)"""
        self.data = data
        self.cfg = cfg

    def generate(self, previous_entries=None, time_limit=None):
        time_limit = time_limit or self.cfg.get("SOLVER_TIME_LIMIT_SECONDS", 30)

        model, x, index, used_group, used_teacher, meta, soft_terms = build_model(
            self.data, self.cfg, previous_entries=previous_entries
        )

        if not x:
            return {
                "status_name": "INFEASIBLE",
                "reason": "No valid (teacher, room, slot) combination exists for any "
                          "selected course. Check teacher qualifications (course "
                          "offerings), room capacities/types, and teacher availability.",
                "entries": [],
                "meta": meta,
                "objective_value": None,
                "soft_conflict_score": None,
                "elapsed_seconds": 0,
            }

        result = solve_model(model, time_limit_seconds=time_limit)

        entries = []
        soft_conflict_score = None
        if result["status"] in (cp_model_module.OPTIMAL, cp_model_module.FEASIBLE):
            solver = result["solver"]
            for (g, c, t, r, s), var in x.items():
                if solver.Value(var) == 1:
                    entries.append({
                        "group_id": g, "course_id": c, "teacher_id": t,
                        "room_id": r, "time_slot_id": s,
                    })
            # The TRUE soft-constraint badness score -- deliberately computed
            # from soft_terms alone (never the raw objective), so a
            # re-optimization "preserve previous assignment" bonus never
            # leaks into the reported conflict count.
            soft_conflict_score = sum(
                weight * solver.Value(var) for weight, var in soft_terms
            )
        else:
            reason = self._explain_infeasibility()
            return {
                "status_name": result["status_name"],
                "reason": reason,
                "entries": [],
                "meta": meta,
                "objective_value": None,
                "soft_conflict_score": None,
                "elapsed_seconds": result["elapsed_seconds"],
            }

        return {
            "status_name": result["status_name"],
            "reason": None,
            "entries": entries,
            "meta": meta,
            "objective_value": result["objective_value"],
            "soft_conflict_score": soft_conflict_score,
            "elapsed_seconds": result["elapsed_seconds"],
        }

    def _explain_infeasibility(self):
        """Best-effort, human readable explanation of why no feasible
        timetable exists, based on simple demand-vs-supply checks (does not
        require re-solving the model)."""
        reasons = []
        lab_courses = [c for c, info in self.data["courses"].items() if info["requires_lab"]]
        lab_rooms = [r for r, info in self.data["rooms"].items()
                     if info["room_type"] in ("Computer Lab", "Physics Lab", "Chemistry Lab")
                     and r not in self.data["unavailable_rooms"]]
        if lab_courses and not lab_rooms:
            reasons.append(
                f"{len(lab_courses)} course(s) require a laboratory but no laboratory "
                f"room is currently available."
            )

        total_slots = len(self.data["slots"])
        for c, info in self.data["courses"].items():
            if info["hours_per_week"] > total_slots:
                reasons.append(
                    f"Course id {c} requires {info['hours_per_week']} periods/week but "
                    f"only {total_slots} timeslots exist per week."
                )

        for (g, c) in self.data["selections"]:
            qualified = [t for (cc, t) in self.data["offerings"] if cc == c]
            available_qualified = [t for t in qualified if t not in self.data["unavailable_teachers"]]
            if not available_qualified:
                reasons.append(
                    f"No available qualified teacher exists for course id {c} "
                    f"(group id {g})."
                )

        if not reasons:
            reasons.append(
                "The combined demand for teachers, rooms and timeslots from all "
                "selected courses exceeds the available supply within the current "
                "constraints (teacher availability, room capacity/type)."
            )
        return " ".join(sorted(set(reasons))[:5])

    def naive_baseline(self):
        """A deliberately non-optimized, first-fit scheduler used ONLY to
        generate an honest 'before optimization' conflict count for the
        insights page. It ignores clashes on purpose so the contrast with
        the CP-SAT result is real and demonstrable, not fabricated."""
        slot_ids = sorted(self.data["slots"].keys(),
                           key=lambda s: (self.data["slots"][s]["day"], self.data["slots"][s]["period_number"]))
        if not slot_ids:
            return []
        slot_cycle = cycle(slot_ids)

        room_ids = sorted(self.data["rooms"].keys())
        entries = []
        for (g, c) in self.data["selections"]:
            hours = self.data["courses"][c]["hours_per_week"]
            qualified = [t for (cc, t) in self.data["offerings"] if cc == c]
            teacher = qualified[0] if qualified else None
            if teacher is None or not room_ids:
                continue
            room = room_ids[(g + c) % len(room_ids)]
            for _ in range(hours):
                s = next(slot_cycle)
                entries.append({
                    "group_id": g, "course_id": c, "teacher_id": teacher,
                    "room_id": room, "time_slot_id": s,
                })
        return entries
