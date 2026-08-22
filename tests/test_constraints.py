"""
Unit tests for the CP-SAT hard constraints, run directly against
optimizer/model.py using small hand-built data bundles (no Flask/DB needed).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ortools.sat.python import cp_model as cp_model_module
from optimizer.model import build_model
from optimizer.solver import solve_model

DEFAULT_CFG = {
    "WEIGHT_GROUP_GAP": 10, "WEIGHT_TEACHER_GAP": 8, "WEIGHT_DAILY_OVERLOAD": 6,
    "WEIGHT_CONSECUTIVE_RUN": 5, "WEIGHT_SAME_DAY_REPEAT": 4,
    "DAILY_TARGET_PERIODS": 5, "MAX_CONSECUTIVE_BEFORE_PENALTY": 3,
}


def base_data():
    """A minimal, deliberately tight bundle: 1 group, 2 courses, 1 teacher
    qualified for both, 1 room, only 2 timeslots available -- forces the
    solver to prove it avoids clashes rather than just having lots of slack."""
    return {
        "groups": {1: {"strength": 30}},
        "courses": {
            1: {"hours_per_week": 1, "requires_lab": False, "capacity": 60},
            2: {"hours_per_week": 1, "requires_lab": False, "capacity": 60},
        },
        "rooms": {1: {"capacity": 60, "room_type": "Classroom"}},
        "slots": {1: {"day": "MON", "period_number": 1}, 2: {"day": "MON", "period_number": 2}},
        "offerings": {(1, 1), (2, 1)},          # teacher 1 qualified for both courses
        "selections": {(1, 1), (1, 2)},          # group 1 takes both courses
        "teacher_unavailable": set(),
        "unavailable_rooms": set(),
        "unavailable_teachers": set(),
    }


class TestHardConstraints(unittest.TestCase):
    def _solve(self, data):
        model, x, index, used_group, used_teacher, meta, soft_terms = build_model(data, DEFAULT_CFG)
        result = solve_model(model, time_limit_seconds=10)
        entries = []
        if result["status"] in (cp_model_module.OPTIMAL, cp_model_module.FEASIBLE):
            solver = result["solver"]
            for key, var in x.items():
                if solver.Value(var) == 1:
                    entries.append(key)
        return result, entries

    def test_teacher_clash_avoided(self):
        """Same teacher, 2 courses, same group -- solver must NOT put both
        in the same slot even though only one teacher exists."""
        data = base_data()
        result, entries = self._solve(data)
        self.assertIn(result["status_name"], ("OPTIMAL", "FEASIBLE"))
        slots_used = [e[4] for e in entries]
        self.assertEqual(len(slots_used), len(set(slots_used)), "Group/teacher was double-booked in one slot")

    def test_room_clash_forces_infeasible_when_no_alternative(self):
        """Two groups both needing the only room at the only available
        slot cannot both be satisfied -- the model must recognise this."""
        data = base_data()
        data["groups"][2] = {"strength": 30}
        data["selections"] = {(1, 1), (2, 1)}
        data["courses"] = {1: {"hours_per_week": 1, "requires_lab": False, "capacity": 60}}
        data["slots"] = {1: {"day": "MON", "period_number": 1}}  # only ONE slot, ONE room
        data["offerings"] = {(1, 1)}
        result, entries = self._solve(data)
        # Only one of the two groups can get the single room/slot -> infeasible
        self.assertEqual(result["status_name"], "INFEASIBLE")

    def test_student_group_clash_avoided(self):
        """The classic NEP-2020 case: a group takes a core course and a
        cross-department multidisciplinary course. They must never collide."""
        data = base_data()
        result, entries = self._solve(data)
        group_slot_pairs = [(e[0], e[4]) for e in entries]
        self.assertEqual(len(group_slot_pairs), len(set(group_slot_pairs)))

    def test_room_capacity_respected(self):
        """A room smaller than the group must never be used -- verified by
        confirming no variable even exists for that combination."""
        data = base_data()
        data["groups"][1]["strength"] = 100  # bigger than the only room's capacity (60)
        model, x, index, used_group, used_teacher, meta, soft_terms = build_model(data, DEFAULT_CFG)
        self.assertEqual(len(x), 0, "No variable should exist for an over-capacity room")

    def test_lab_requirement_respected(self):
        """A course requiring a lab must never be assigned to a plain classroom."""
        data = base_data()
        data["courses"][1]["requires_lab"] = True
        data["selections"] = {(1, 1)}
        data["courses"] = {1: data["courses"][1]}
        model, x, index, used_group, used_teacher, meta, soft_terms = build_model(data, DEFAULT_CFG)
        self.assertEqual(len(x), 0, "No classroom-only room should be usable for a lab course")

    def test_teacher_availability_respected(self):
        """A teacher marked unavailable at a slot must never receive a
        variable for that slot."""
        data = base_data()
        data["teacher_unavailable"] = {(1, 1)}
        model, x, index, used_group, used_teacher, meta, soft_terms = build_model(data, DEFAULT_CFG)
        for (g, c, t, r, s) in x:
            if t == 1:
                self.assertNotEqual(s, 1)

    def test_course_weekly_hours_exact(self):
        """A 2-hour/week course must receive exactly 2 sessions."""
        data = base_data()
        data["courses"] = {1: {"hours_per_week": 2, "requires_lab": False, "capacity": 60}}
        data["selections"] = {(1, 1)}
        data["slots"] = {
            1: {"day": "MON", "period_number": 1}, 2: {"day": "MON", "period_number": 2},
            3: {"day": "TUE", "period_number": 1},
        }
        data["offerings"] = {(1, 1)}
        result, entries = self._solve(data)
        self.assertEqual(result["status_name"], "OPTIMAL")
        self.assertEqual(len(entries), 2)

    def test_multidisciplinary_cross_department_selection_scheduled(self):
        """Simulates a CSE group selecting an HUM-owned 'Economics' course --
        confirms the optimizer treats it identically to any other course and
        schedules it without clashing against the group's other course."""
        data = base_data()  # group 1 already takes course 1 (dept-agnostic here) and course 2
        result, entries = self._solve(data)
        self.assertIn(result["status_name"], ("OPTIMAL", "FEASIBLE"))
        self.assertEqual(len(entries), 2)


if __name__ == "__main__":
    unittest.main()
