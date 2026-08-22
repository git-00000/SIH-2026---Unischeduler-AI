"""
Seed script -- populates the database with a realistic demo dataset so the
project is immediately demonstrable after installation.

Run with:
    python seed/seed_data.py

This DROPS and recreates all tables, so it is safe to re-run at any time
during development/demo prep.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database.db import db
from database.models import (
    User, Department, Teacher, Student, StudentGroup, Course, Room, TimeSlot,
    TeacherAvailability, CourseOffering, StudentCourseSelection,
)

app = create_app()

WORKING_DAYS = ["MON", "TUE", "WED", "THU", "FRI"]
# 8 periods/day; period 5 is a fixed lunch break (is_break=True), giving 7
# usable teaching periods/day x 5 days = 35 usable slots/week.
PERIOD_TIMES = [
    (1, "09:00", "10:00"),
    (2, "10:00", "11:00"),
    (3, "11:00", "12:00"),
    (4, "12:00", "13:00"),
    (5, "13:00", "14:00"),   # lunch break
    (6, "14:00", "15:00"),
    (7, "15:00", "16:00"),
    (8, "16:00", "17:00"),
]
LUNCH_PERIOD = 5


def seed():
    with app.app_context():
        print("Dropping and recreating all tables...")
        db.drop_all()
        db.create_all()

        # ---------------------------------------------------------- Departments
        dept_defs = [
            ("Computer Science & Engineering", "CSE"),
            ("Electronics & Communication Engineering", "ECE"),
            ("Mechanical Engineering", "MECH"),
            ("Humanities & Social Sciences", "HUM"),
        ]
        departments = {}
        for name, code in dept_defs:
            d = Department(name=name, code=code)
            db.session.add(d)
            departments[code] = d
        db.session.flush()
        print(f"  {len(departments)} departments created.")

        # ---------------------------------------------------------- Time slots
        slots_by_day_period = {}
        for day in WORKING_DAYS:
            for period_number, start, end in PERIOD_TIMES:
                slot = TimeSlot(
                    day=day, start_time=start, end_time=end,
                    period_number=period_number, is_break=(period_number == LUNCH_PERIOD),
                )
                db.session.add(slot)
                slots_by_day_period[(day, period_number)] = slot
        db.session.flush()
        print(f"  {len(slots_by_day_period)} timeslots created "
              f"({len(WORKING_DAYS)} days x {len(PERIOD_TIMES)} periods).")

        # ---------------------------------------------------------- Rooms
        room_defs = [
            ("R-101", 70, "Classroom", "Academic Block A"),
            ("R-102", 60, "Classroom", "Academic Block A"),
            ("R-103", 50, "Classroom", "Academic Block A"),
            ("R-201", 65, "Classroom", "Academic Block B"),
            ("R-203", 55, "Classroom", "Academic Block B"),
            ("R-204", 60, "Classroom", "Academic Block B"),
            ("R-202", 45, "Seminar Hall", "Academic Block B"),
            ("CL-01", 40, "Computer Lab", "Lab Block"),
            ("CL-02", 40, "Computer Lab", "Lab Block"),
            ("PL-01", 35, "Physics Lab", "Lab Block"),
            ("CH-01", 35, "Chemistry Lab", "Lab Block"),
            ("SH-01", 80, "Seminar Hall", "Academic Block B"),
        ]
        rooms = {}
        for number, cap, rtype, building in room_defs:
            r = Room(room_number=number, capacity=cap, room_type=rtype, building=building)
            db.session.add(r)
            rooms[number] = r
        db.session.flush()
        print(f"  {len(rooms)} rooms created.")

        # ---------------------------------------------------------- Teachers
        teacher_defs = [
            ("Dr. A. Sharma", "a.sharma@univ.edu", "CSE"),
            ("Dr. R. Verma", "r.verma@univ.edu", "CSE"),
            ("Prof. S. Iyer", "s.iyer@univ.edu", "CSE"),
            ("Dr. N. Gupta", "n.gupta@univ.edu", "CSE"),
            ("Prof. K. Rao", "k.rao@univ.edu", "CSE"),
            ("Dr. P. Nair", "p.nair@univ.edu", "ECE"),
            ("Dr. M. Joshi", "m.joshi@univ.edu", "ECE"),
            ("Prof. T. Menon", "t.menon@univ.edu", "ECE"),
            ("Dr. V. Krishnan", "v.krishnan@univ.edu", "ECE"),
            ("Dr. D. Kulkarni", "d.kulkarni@univ.edu", "MECH"),
            ("Prof. H. Desai", "h.desai@univ.edu", "MECH"),
            ("Dr. J. Bose", "j.bose@univ.edu", "MECH"),
            ("Dr. L. Banerjee", "l.banerjee@univ.edu", "HUM"),
            ("Prof. A. Chatterjee", "a.chatterjee@univ.edu", "HUM"),
            ("Dr. R. Pillai", "r.pillai@univ.edu", "HUM"),
            ("Prof. S. Reddy", "s.reddy@univ.edu", "HUM"),
        ]
        teachers = {}
        for name, email, dept_code in teacher_defs:
            t = Teacher(name=name, email=email, department_id=departments[dept_code].id)
            db.session.add(t)
            teachers[name] = t
        db.session.flush()
        print(f"  {len(teachers)} teachers created.")

        # ---------------------------------------------------------- Courses
        # (code, name, dept_code, type, credits, hours/wk, requires_lab, semester, capacity)
        course_defs = [
            ("CS301", "Data Structures", "CSE", "Core", 4, 4, False, 3, 70),
            ("CS302", "Database Management Systems", "CSE", "Core", 4, 4, False, 3, 70),
            ("CS303", "Operating Systems", "CSE", "Core", 4, 3, False, 3, 70),
            ("CS304", "Computer Networks Lab", "CSE", "Core", 2, 2, True, 3, 40),
            ("CS401", "Machine Learning", "CSE", "Elective", 3, 3, False, 5, 60),
            ("CS402", "Cloud Computing", "CSE", "Elective", 3, 3, False, 5, 60),
            ("CS403", "Programming Lab", "CSE", "Core", 2, 2, True, 3, 40),

            ("EC301", "Digital Electronics", "ECE", "Core", 4, 4, False, 3, 65),
            ("EC302", "Embedded Systems", "ECE", "Core", 4, 3, False, 3, 65),
            ("EC303", "Signals and Systems", "ECE", "Core", 3, 3, False, 3, 65),
            ("EC401", "VLSI Design", "ECE", "Elective", 3, 3, False, 5, 55),
            ("EC402", "Electronics Lab", "ECE", "Core", 2, 2, True, 3, 40),

            ("ME301", "Thermodynamics", "MECH", "Core", 4, 4, False, 3, 65),
            ("ME302", "Fluid Mechanics", "MECH", "Core", 4, 3, False, 3, 65),
            ("ME303", "Manufacturing Processes", "MECH", "Core", 3, 3, False, 3, 65),
            ("ME401", "Robotics", "MECH", "Elective", 3, 3, False, 5, 55),

            # Multidisciplinary / cross-department courses (NEP 2020 core feature)
            ("HU201", "Economics", "HUM", "Multidisciplinary", 3, 3, False, 3, 80),
            ("HU202", "Psychology", "HUM", "Multidisciplinary", 3, 3, False, 3, 80),
            ("HU203", "Environmental Studies", "HUM", "Multidisciplinary", 2, 2, False, 3, 80),
            ("HU301", "Data Analytics", "HUM", "Multidisciplinary", 3, 3, False, 5, 60),

            # Skill / ability / value-added courses
            ("HU101", "Communication Skills", "HUM", "Skill Enhancement", 2, 2, False, 1, 80),
            ("HU102", "Critical Thinking", "HUM", "Ability Enhancement", 2, 2, False, 1, 80),
            ("HU103", "Ethics and Values", "HUM", "Value Added", 2, 2, False, 1, 80),
        ]
        courses = {}
        for code, name, dept_code, ctype, credits, hours, lab, sem, cap in course_defs:
            c = Course(
                course_code=code, name=name, department_id=departments[dept_code].id,
                course_type=ctype, credits=credits, hours_per_week=hours,
                requires_lab=lab, semester=sem, capacity=cap,
            )
            db.session.add(c)
            courses[code] = c
        db.session.flush()
        print(f"  {len(courses)} courses created "
              f"({sum(1 for c in course_defs if c[3] == 'Multidisciplinary')} multidisciplinary).")

        # ---------------------------------------------------------- Course Offerings
        # (course_code -> list of qualified teacher names)
        offering_defs = {
            "CS301": ["Dr. A. Sharma", "Dr. R. Verma"],
            "CS302": ["Dr. R. Verma", "Prof. S. Iyer"],
            "CS303": ["Dr. N. Gupta"],
            "CS304": ["Prof. K. Rao"],
            "CS401": ["Dr. A. Sharma"],
            "CS402": ["Prof. S. Iyer"],
            "CS403": ["Dr. N. Gupta", "Prof. K. Rao"],

            "EC301": ["Dr. P. Nair"],
            "EC302": ["Dr. M. Joshi"],
            "EC303": ["Prof. T. Menon"],
            "EC401": ["Dr. V. Krishnan"],
            "EC402": ["Dr. P. Nair", "Dr. M. Joshi"],

            "ME301": ["Dr. D. Kulkarni"],
            "ME302": ["Prof. H. Desai"],
            "ME303": ["Dr. J. Bose"],
            "ME401": ["Dr. D. Kulkarni"],

            "HU201": ["Dr. L. Banerjee"],
            "HU202": ["Prof. A. Chatterjee"],
            "HU203": ["Dr. R. Pillai"],
            "HU301": ["Prof. S. Reddy"],
            "HU101": ["Dr. R. Pillai"],
            "HU102": ["Prof. A. Chatterjee"],
            "HU103": ["Dr. L. Banerjee"],
        }
        offering_count = 0
        for code, teacher_names in offering_defs.items():
            for tname in teacher_names:
                db.session.add(CourseOffering(course_id=courses[code].id, teacher_id=teachers[tname].id))
                offering_count += 1
        db.session.flush()
        print(f"  {offering_count} course offerings (teacher qualifications) created.")

        # ---------------------------------------------------------- Student Groups
        # Strengths are deliberately kept at or below the smaller classrooms'
        # capacity (R-103=50 is the tightest non-lab room) wherever possible,
        # so that disabling any single room during the What-If demo still
        # leaves enough alternative rooms for a feasible re-optimization.
        group_defs = [
            ("CSE-3A", "CSE", 3, 58),
            ("CSE-3B", "CSE", 3, 55),
            ("CSE-5A", "CSE", 5, 48),
            ("ECE-3A", "ECE", 3, 52),
            ("ECE-3B", "ECE", 3, 50),
            ("ECE-5A", "ECE", 5, 42),
            ("MECH-3A", "MECH", 3, 50),
            ("MECH-3B", "MECH", 3, 48),
            ("MECH-5A", "MECH", 5, 40),
            ("HUM-1A", "HUM", 1, 60),
        ]
        groups = {}
        for name, dept_code, sem, strength in group_defs:
            g = StudentGroup(name=name, department_id=departments[dept_code].id, semester=sem, strength=strength)
            db.session.add(g)
            groups[name] = g
        db.session.flush()
        print(f"  {len(groups)} student groups created.")

        # ---------------------------------------------------------- Students (sample, ~6 per group)
        student_count = 0
        for gname, g in groups.items():
            dept_code = [k for k, v in departments.items() if v.id == g.department_id][0]
            for i in range(1, 7):
                roll = f"{dept_code}{g.semester}{gname[-1]}{i:02d}"
                s = Student(
                    name=f"Student {roll}", roll_number=roll,
                    department_id=g.department_id, semester=g.semester, group_id=g.id,
                )
                db.session.add(s)
                student_count += 1
        db.session.flush()
        print(f"  {student_count} sample students created.")

        # ---------------------------------------------------------- Course Selections
        # Core courses per group (same department, same semester) + NEP multidisciplinary
        # / elective picks across departments -- this is what proves NEP-2020 flexibility.
        selection_defs = {
            "CSE-3A": ["CS301", "CS302", "CS303", "CS304", "HU201", "HU101"],
            "CSE-3B": ["CS301", "CS302", "CS303", "CS304", "HU202", "HU101"],
            "CSE-5A": ["CS401", "CS402", "CS403", "HU301"],
            "ECE-3A": ["EC301", "EC302", "EC303", "EC402", "HU202", "HU102"],
            "ECE-3B": ["EC301", "EC302", "EC303", "EC402", "HU203", "HU102"],
            "ECE-5A": ["EC401", "HU301"],
            "MECH-3A": ["ME301", "ME302", "ME303", "HU301", "HU103"],
            "MECH-3B": ["ME301", "ME302", "ME303", "HU203", "HU103"],
            "MECH-5A": ["ME401", "HU301"],
            "HUM-1A": ["HU101", "HU102", "HU103", "HU201", "HU203"],
        }
        selection_count = 0
        for gname, course_codes in selection_defs.items():
            g = groups[gname]
            for code in course_codes:
                db.session.add(StudentCourseSelection(
                    group_id=g.id, course_id=courses[code].id, semester=g.semester,
                ))
                selection_count += 1
        db.session.flush()
        cross_dept = sum(
            1 for gname, codes in selection_defs.items() for code in codes
            if courses[code].department_id != groups[gname].department_id
        )
        print(f"  {selection_count} course selections created ({cross_dept} cross-department / NEP multidisciplinary).")

        # ---------------------------------------------------------- Teacher Availability
        # A handful of realistic "unavailable" slots (e.g. admin duty, another commitment).
        unavailability = [
            ("Dr. A. Sharma", "MON", 1),
            ("Dr. A. Sharma", "FRI", 8),
            ("Prof. S. Iyer", "WED", 8),
            ("Dr. P. Nair", "TUE", 1),
            ("Dr. D. Kulkarni", "THU", 8),
            ("Prof. A. Chatterjee", "MON", 8),
        ]
        for tname, day, period in unavailability:
            slot = slots_by_day_period[(day, period)]
            db.session.add(TeacherAvailability(
                teacher_id=teachers[tname].id, time_slot_id=slot.id, available=False,
            ))
        print(f"  {len(unavailability)} teacher-unavailability records created.")

        # ---------------------------------------------------------- Users
        admin = User(username="admin", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)

        teacher_user = User(username="dr.sharma", role="teacher", teacher_id=teachers["Dr. A. Sharma"].id)
        teacher_user.set_password("teacher123")
        db.session.add(teacher_user)

        first_student = Student.query.filter_by(roll_number=f"CSE3A01").first()
        student_user = User(username="student1", role="student",
                             student_id=first_student.id if first_student else None)
        student_user.set_password("student123")
        db.session.add(student_user)

        db.session.commit()
        print("  3 demo user accounts created (admin / dr.sharma / student1).")

        print("\nSeed complete. Start the app with:  python app.py")
        print("Login at http://127.0.0.1:5000  ->  admin / admin123")


if __name__ == "__main__":
    seed()
