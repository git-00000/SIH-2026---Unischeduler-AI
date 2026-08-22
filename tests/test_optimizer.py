"""
Tests for optimizer/timetable_generator.py -- the orchestration layer that
wraps model building + solving + the naive baseline used for comparison.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optimizer.timetable_generator import TimetableGenerator

CFG = {
    "WEIGHT_GROUP_GAP": 10, "WEIGHT_TEACHER_GAP": 8, "WEIGHT_DAILY_OVERLOAD": 6,
    "WEIGHT_CONSECUTIVE_RUN": 5, "WEIGHT_SAME_DAY_REPEAT": 4,
    "DAILY_TARGET_PERIODS": 5, "MAX_CONSECUTIVE_BEFORE_PENALTY": 3,
    "SOLVER_TIME_LIMIT_SECONDS": 10,
}


def sample_data():
    slots = {}
    sid = 1
    for day in ["MON", "TUE", "WED"]:
        for period in range(1, 6):
            slots[sid] = {"day": day, "period_number": period}
            sid += 1

    return {
        "groups": {1: {"strength": 40}, 2: {"strength": 35}},
        "courses": {
            1: {"hours_per_week": 3, "requires_lab": False, "capacity": 60},
            2: {"hours_per_week": 2, "requires_lab": True, "capacity": 60},
            3: {"hours_per_week": 2, "requires_lab": False, "capacity": 60},  # multidisciplinary
        },
        "rooms": {
            1: {"capacity": 60, "room_type": "Classroom"},
            2: {"capacity": 60, "room_type": "Classroom"},
            3: {"capacity": 40, "room_type": "Computer Lab"},
        },
        "slots": slots,
        "offerings": {(1, 1), (2, 2), (3, 1), (3, 2)},
        "selections": {(1, 1), (1, 2), (1, 3), (2, 1), (2, 3)},
        "teacher_unavailable": set(),
        "unavailable_rooms": set(),
        "unavailable_teachers": set(),
    }


class TestTimetableGenerator(unittest.TestCase):
    def test_generate_produces_valid_timetable(self):
        gen = TimetableGenerator(sample_data(), CFG)
        result = gen.generate()
        self.assertIn(result["status_name"], ("OPTIMAL", "FEASIBLE"))
        self.assertTrue(len(result["entries"]) > 0)

        # Every (group, course) pair must get exactly hours_per_week sessions.
        data = sample_data()
        counts = {}
        for e in result["entries"]:
            key = (e["group_id"], e["course_id"])
            counts[key] = counts.get(key, 0) + 1
        for (g, c), hours in [((1, 1), 3), ((1, 2), 2), ((1, 3), 2), ((2, 1), 3), ((2, 3), 2)]:
            self.assertEqual(counts.get((g, c), 0), hours)

    def test_no_teacher_or_room_or_group_double_booking(self):
        gen = TimetableGenerator(sample_data(), CFG)
        result = gen.generate()
        entries = result["entries"]

        teacher_slot = set()
        room_slot = set()
        group_slot = set()
        for e in entries:
            ts = (e["teacher_id"], e["time_slot_id"])
            rs = (e["room_id"], e["time_slot_id"])
            gs = (e["group_id"], e["time_slot_id"])
            self.assertNotIn(ts, teacher_slot)
            self.assertNotIn(rs, room_slot)
            self.assertNotIn(gs, group_slot)
            teacher_slot.add(ts)
            room_slot.add(rs)
            group_slot.add(gs)

    def test_naive_baseline_runs_without_error(self):
        gen = TimetableGenerator(sample_data(), CFG)
        entries = gen.naive_baseline()
        self.assertTrue(len(entries) > 0)

    def test_infeasible_when_no_teacher_qualified(self):
        data = sample_data()
        data["offerings"] = set()  # nobody is qualified to teach anything
        gen = TimetableGenerator(data, CFG)
        result = gen.generate()
        self.assertEqual(result["status_name"], "INFEASIBLE")
        self.assertIsNotNone(result["reason"])
        self.assertNotEqual(result["reason"].strip(), "Error")


if __name__ == "__main__":
    unittest.main()
