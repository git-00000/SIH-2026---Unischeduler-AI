"""
SQLAlchemy ORM models.

Design notes
------------
* StudentGroup is the scheduling unit (a batch/section of students). Individual
  Student rows belong to a StudentGroup. All timetable optimisation happens at
  the StudentGroup level, which keeps the CP-SAT model tractable while still
  giving every student a personalised view (their group's timetable).
* StudentCourseSelection links a StudentGroup to a Course. This is what makes
  NEP-2020 multidisciplinary education possible: a CSE group can select
  "Economics" (owned by the Humanities department) and the optimizer will
  treat it exactly like any other course when checking for clashes.
* CourseOffering links a Course to a Teacher who is qualified/assigned to
  teach it in a given semester/academic term. A course can have more than one
  offering (more than one qualified teacher) -- the optimizer chooses which
  offering to use for each group.
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import db


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    code = db.Column(db.String(20), nullable=False, unique=True)

    teachers = db.relationship("Teacher", backref="department", lazy=True)
    courses = db.relationship("Course", backref="department", lazy=True)
    student_groups = db.relationship("StudentGroup", backref="department", lazy=True)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "code": self.code}


class Teacher(db.Model):
    __tablename__ = "teachers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    max_hours_per_week = db.Column(db.Integer, default=18)

    offerings = db.relationship("CourseOffering", backref="teacher", lazy=True)
    availability = db.relationship("TeacherAvailability", backref="teacher", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "department_id": self.department_id,
            "department": self.department.name if self.department else None,
            "max_hours_per_week": self.max_hours_per_week,
        }


class StudentGroup(db.Model):
    """A batch/section of students e.g. 'CSE-3A'. The scheduling unit."""
    __tablename__ = "student_groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    strength = db.Column(db.Integer, nullable=False, default=40)

    students = db.relationship("Student", backref="group", lazy=True)
    selections = db.relationship("StudentCourseSelection", backref="group", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "department_id": self.department_id,
            "department": self.department.name if self.department else None,
            "semester": self.semester,
            "strength": self.strength,
        }


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    roll_number = db.Column(db.String(40), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey("student_groups.id"), nullable=True)

    department = db.relationship("Department")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "roll_number": self.roll_number,
            "department_id": self.department_id,
            "department": self.department.name if self.department else None,
            "semester": self.semester,
            "group_id": self.group_id,
            "group": self.group.name if self.group else None,
        }


COURSE_TYPES = [
    "Core",
    "Elective",
    "Multidisciplinary",
    "Ability Enhancement",
    "Skill Enhancement",
    "Value Added",
]


class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    course_type = db.Column(db.String(40), nullable=False, default="Core")
    credits = db.Column(db.Integer, nullable=False, default=3)
    hours_per_week = db.Column(db.Integer, nullable=False, default=3)
    requires_lab = db.Column(db.Boolean, default=False)
    semester = db.Column(db.Integer, nullable=False, default=1)
    capacity = db.Column(db.Integer, nullable=False, default=60)

    offerings = db.relationship("CourseOffering", backref="course", lazy=True)
    selections = db.relationship("StudentCourseSelection", backref="course", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "course_code": self.course_code,
            "name": self.name,
            "department_id": self.department_id,
            "department": self.department.name if self.department else None,
            "course_type": self.course_type,
            "credits": self.credits,
            "hours_per_week": self.hours_per_week,
            "requires_lab": self.requires_lab,
            "semester": self.semester,
            "capacity": self.capacity,
        }


class CoursePrerequisite(db.Model):
    __tablename__ = "course_prerequisites"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    prerequisite_course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)

    course = db.relationship("Course", foreign_keys=[course_id])
    prerequisite = db.relationship("Course", foreign_keys=[prerequisite_course_id])


ROOM_TYPES = ["Classroom", "Computer Lab", "Physics Lab", "Chemistry Lab", "Seminar Hall"]
LAB_ROOM_TYPES = {"Computer Lab", "Physics Lab", "Chemistry Lab"}


class Room(db.Model):
    __tablename__ = "rooms"

    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(20), unique=True, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    room_type = db.Column(db.String(40), nullable=False, default="Classroom")
    building = db.Column(db.String(80), default="Main Block")
    is_available = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "room_number": self.room_number,
            "capacity": self.capacity,
            "room_type": self.room_type,
            "building": self.building,
            "is_available": self.is_available,
        }


class TimeSlot(db.Model):
    __tablename__ = "time_slots"

    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(10), nullable=False)          # MON, TUE, ...
    start_time = db.Column(db.String(10), nullable=False)    # "09:00"
    end_time = db.Column(db.String(10), nullable=False)      # "10:00"
    period_number = db.Column(db.Integer, nullable=False)    # 1..N within the day
    is_break = db.Column(db.Boolean, default=False)          # lunch/break slot

    def to_dict(self):
        return {
            "id": self.id,
            "day": self.day,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "period_number": self.period_number,
            "is_break": self.is_break,
            "label": f"{self.day} {self.start_time}-{self.end_time}",
        }


class TeacherAvailability(db.Model):
    __tablename__ = "teacher_availability"

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False)
    time_slot_id = db.Column(db.Integer, db.ForeignKey("time_slots.id"), nullable=False)
    available = db.Column(db.Boolean, default=True)
    preferred = db.Column(db.Boolean, default=False)  # soft preference boost

    time_slot = db.relationship("TimeSlot")

    __table_args__ = (db.UniqueConstraint("teacher_id", "time_slot_id", name="uq_teacher_slot"),)


class CourseOffering(db.Model):
    """A teacher qualified/assigned to teach a course in a given semester term."""
    __tablename__ = "course_offerings"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False)
    academic_term = db.Column(db.String(20), default="2026-ODD")

    __table_args__ = (db.UniqueConstraint("course_id", "teacher_id", "academic_term", name="uq_offering"),)


class StudentCourseSelection(db.Model):
    """Which StudentGroup takes which Course this semester (core/elective/
    multidisciplinary alike). This is the table that drives NEP-2020 style
    cross-department enrolment."""
    __tablename__ = "student_course_selections"

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("student_groups.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    semester = db.Column(db.Integer, nullable=False)

    __table_args__ = (db.UniqueConstraint("group_id", "course_id", name="uq_group_course"),)


class GenerationRun(db.Model):
    __tablename__ = "generation_runs"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(30), default="PENDING")  # PENDING/OPTIMAL/FEASIBLE/INFEASIBLE/ERROR
    objective_score = db.Column(db.Float, nullable=True)
    hard_conflicts = db.Column(db.Integer, default=0)
    soft_conflicts = db.Column(db.Integer, default=0)
    generation_time = db.Column(db.Float, default=0.0)  # seconds
    num_variables = db.Column(db.Integer, default=0)
    num_constraints = db.Column(db.Integer, default=0)
    conflicts_before = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=False)  # currently displayed timetable
    notes = db.Column(db.Text, nullable=True)

    entries = db.relationship("TimetableEntry", backref="run", lazy=True, cascade="all, delete-orphan")
    conflicts = db.relationship("Conflict", backref="run", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "status": self.status,
            "objective_score": self.objective_score,
            "hard_conflicts": self.hard_conflicts,
            "soft_conflicts": self.soft_conflicts,
            "generation_time": self.generation_time,
            "num_variables": self.num_variables,
            "num_constraints": self.num_constraints,
            "conflicts_before": self.conflicts_before,
            "is_active": self.is_active,
            "notes": self.notes,
        }


class TimetableEntry(db.Model):
    __tablename__ = "timetable_entries"

    id = db.Column(db.Integer, primary_key=True)
    generation_run_id = db.Column(db.Integer, db.ForeignKey("generation_runs.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey("student_groups.id"), nullable=False)
    time_slot_id = db.Column(db.Integer, db.ForeignKey("time_slots.id"), nullable=False)

    course = db.relationship("Course")
    teacher = db.relationship("Teacher")
    room = db.relationship("Room")
    group = db.relationship("StudentGroup")
    time_slot = db.relationship("TimeSlot")

    def to_dict(self):
        return {
            "id": self.id,
            "generation_run_id": self.generation_run_id,
            "course_id": self.course_id,
            "course_code": self.course.course_code if self.course else None,
            "course_name": self.course.name if self.course else None,
            "course_type": self.course.course_type if self.course else None,
            "teacher_id": self.teacher_id,
            "teacher_name": self.teacher.name if self.teacher else None,
            "room_id": self.room_id,
            "room_number": self.room.room_number if self.room else None,
            "group_id": self.group_id,
            "group_name": self.group.name if self.group else None,
            "time_slot_id": self.time_slot_id,
            "day": self.time_slot.day if self.time_slot else None,
            "period_number": self.time_slot.period_number if self.time_slot else None,
            "start_time": self.time_slot.start_time if self.time_slot else None,
            "end_time": self.time_slot.end_time if self.time_slot else None,
        }


class Conflict(db.Model):
    __tablename__ = "conflicts"

    id = db.Column(db.Integer, primary_key=True)
    generation_run_id = db.Column(db.Integer, db.ForeignKey("generation_runs.id"), nullable=True)
    conflict_type = db.Column(db.String(40), nullable=False)   # teacher/room/student/capacity/availability
    severity = db.Column(db.String(10), nullable=False)        # hard/soft
    description = db.Column(db.Text, nullable=False)
    stage = db.Column(db.String(10), default="before")         # before/after optimization

    def to_dict(self):
        return {
            "id": self.id,
            "generation_run_id": self.generation_run_id,
            "conflict_type": self.conflict_type,
            "severity": self.severity,
            "description": self.description,
            "stage": self.stage,
        }


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="admin")  # admin/teacher/student
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=True)

    teacher = db.relationship("Teacher")
    student = db.relationship("Student")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "teacher_id": self.teacher_id,
            "student_id": self.student_id,
        }
