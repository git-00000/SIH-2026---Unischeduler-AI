"""
End-to-end route tests using Flask's test client against an isolated
in-memory SQLite database (never touches the real timetable.db).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database.db import db
from database.models import (
    User, Department, Teacher, Room, TimeSlot, StudentGroup, Course,
    CourseOffering, StudentCourseSelection,
)


class RouteTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("development")
        self.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        with self.app.app_context():
            db.drop_all()
            db.create_all()
            self._seed_minimal()

    def _seed_minimal(self):
        dept = Department(name="Computer Science", code="CSE")
        db.session.add(dept)
        db.session.flush()

        admin = User(username="admin", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)

        teacher = Teacher(name="Dr. Test", email="test@univ.edu", department_id=dept.id)
        db.session.add(teacher)
        db.session.flush()

        room = Room(room_number="R-1", capacity=60, room_type="Classroom")
        db.session.add(room)

        group = StudentGroup(name="CSE-1A", department_id=dept.id, semester=1, strength=40)
        db.session.add(group)
        db.session.flush()

        course = Course(course_code="CS101", name="Intro to Programming",
                         department_id=dept.id, course_type="Core",
                         credits=3, hours_per_week=2, semester=1, capacity=60)
        db.session.add(course)
        db.session.flush()

        db.session.add(CourseOffering(course_id=course.id, teacher_id=teacher.id))
        db.session.add(StudentCourseSelection(group_id=group.id, course_id=course.id, semester=1))

        for day in ["MON", "TUE"]:
            for p in range(1, 4):
                db.session.add(TimeSlot(day=day, start_time=f"{8+p}:00", end_time=f"{9+p}:00", period_number=p))

        db.session.commit()

    # ---------------------------------------------------------------- auth
    def test_login_requires_credentials(self):
        res = self.client.post("/api/auth/login", json={})
        self.assertEqual(res.status_code, 400)

    def test_login_rejects_bad_credentials(self):
        res = self.client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        self.assertEqual(res.status_code, 401)

    def test_login_success(self):
        res = self.client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("access_token", res.get_json())

    def test_protected_page_redirects_when_not_logged_in(self):
        res = self.client.get("/dashboard")
        self.assertEqual(res.status_code, 302)

    def test_protected_api_returns_401_when_not_logged_in(self):
        res = self.client.get("/api/courses")
        self.assertEqual(res.status_code, 401)

    def _login(self):
        self.client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})

    # ------------------------------------------------------------ courses
    def test_list_courses_after_login(self):
        self._login()
        res = self.client.get("/api/courses")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["course_code"], "CS101")

    def test_create_course_validation_error(self):
        self._login()
        res = self.client.post("/api/courses", json={"name": "Missing fields"})
        self.assertEqual(res.status_code, 400)

    def test_create_course_success(self):
        self._login()
        with self.app.app_context():
            dept_id = Department.query.filter_by(code="CSE").first().id
        res = self.client.post("/api/courses", json={
            "course_code": "CS102", "name": "Data Structures",
            "department_id": dept_id, "course_type": "Core", "hours_per_week": 3,
        })
        self.assertEqual(res.status_code, 201)

    # -------------------------------------------------------- generation
    def test_generate_timetable_endpoint(self):
        self._login()
        res = self.client.post("/api/generate-timetable", json={})
        self.assertIn(res.status_code, (201, 422))
        data = res.get_json()
        self.assertIn("run", data)
        self.assertIn(data["run"]["status"], ("OPTIMAL", "FEASIBLE", "INFEASIBLE"))

    def test_timetable_endpoint_before_generation(self):
        self._login()
        res = self.client.get("/api/timetable")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIsNone(data["run"])
        self.assertEqual(data["entries"], [])

    def test_reoptimize_without_prior_run_still_works(self):
        self._login()
        res = self.client.post("/api/reoptimize", json={})
        self.assertIn(res.status_code, (200, 422))

    def test_dashboard_summary_endpoint(self):
        self._login()
        res = self.client.get("/api/dashboard/summary")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["total_courses"], 1)
        self.assertEqual(data["total_rooms"], 1)


if __name__ == "__main__":
    unittest.main()
