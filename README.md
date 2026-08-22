# Sarathi — AI-Based Timetable Generation System Aligned with NEP 2020

A Smart India Hackathon (SIH) prototype that generates real, conflict-free
academic timetables using **constraint optimization**, not machine learning.

---

## 1. Problem Statement

Indian higher-education institutions adopting **NEP 2020** must support
multidisciplinary, flexible curricula: a Computer Science student may take
Economics, a Mechanical student may take Data Analytics, and every student
group can mix core, elective, ability-enhancement, skill-enhancement and
value-added courses from *any* department.

Manually building a timetable under these conditions — while also respecting
teacher availability, room capacity/type, lab requirements, and weekly-hour
targets — is a combinatorial problem that quickly becomes infeasible to do
by hand or with simple rule-based/greedy logic. A naive "first slot that's
free" scheduler produces dozens of silent clashes (see the **AI Optimization
Insights** page for a live, honest before/after comparison).

## 2. Why AI/Optimization, Not Machine Learning

This project deliberately does **not** use CNNs, LSTMs, Random Forests or
any predictive ML model — there is nothing to *predict* here; there is a
constraint-satisfaction problem to *solve*. The AI component is
**Google OR-Tools CP-SAT**, a state-of-the-art constraint programming solver.
The system:

1. Encodes every legal (course, teacher, room, group, timeslot) combination
   as a boolean decision variable.
2. Adds **hard constraints** that a feasible solution can never violate
   (teacher/room/group clashes, capacity, lab type, availability, weekly
   hours, qualification, enrolment).
3. Adds **soft constraints** as a weighted objective (gaps, overloaded days,
   long unbroken runs, same-day repeats) that CP-SAT minimises.
4. Returns a certifiably optimal or feasible timetable, with **zero hard
   conflicts** whenever one exists.

## 3. Architecture

```
Frontend (Bootstrap 5 + Chart.js + vanilla JS)
        │  fetch() / JSON
        ▼
Flask REST API (routes/)
        │
        ▼
Service Layer (services/)  ──── conflict detection, analytics
        │
        ▼
AI Optimization Engine (optimizer/)
        │  variables → hard constraints → soft constraints → objective
        ▼
Google OR-Tools CP-SAT
        │
        ▼
SQLite (SQLAlchemy ORM — swap DATABASE_URL for PostgreSQL/MySQL later)
```

The `optimizer/` package has **zero Flask/SQLAlchemy imports** — it works on
plain Python dicts (see `services/timetable_service.py:build_optimizer_data`),
which is what makes `tests/test_constraints.py` and `tests/test_optimizer.py`
possible without spinning up a database.

## 4. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, Bootstrap 5, Chart.js, vanilla JS |
| Backend | Python 3.10+, Flask |
| Database | SQLite (dev/demo) via SQLAlchemy ORM (Postgres/MySQL-ready) |
| AI / Optimization | Google OR-Tools **CP-SAT** |
| Auth | Session cookies (web pages) + Flask-JWT-Extended (API clients) |

## 5. Database Design

Key tables: `Department`, `Teacher`, `Student`, `StudentGroup`, `Course`,
`Room`, `TimeSlot`, `TeacherAvailability`, `CourseOffering`
(teacher-course qualification), `StudentCourseSelection` (group ↔ course —
**this is the NEP-2020 multidisciplinary enrolment table**), `GenerationRun`,
`TimetableEntry`, `Conflict`, `User`. Full definitions in
`database/models.py`.

`StudentGroup` is the scheduling unit (a batch/section). Individual
`Student` rows belong to a group and inherit its timetable — this keeps the
CP-SAT model tractable while still giving every student a personalised view.

## 6. AI Methodology

**Decision variable:** `x[group, course, teacher, room, slot] ∈ {0,1}`,
created *only* for combinations that could ever be legal (qualified teacher,
big-enough room of the right type, teacher available at that slot). This
means constraints 4–6 and 8–9 below are satisfied **by construction**.

### Hard constraints (never violated in a feasible solution)
1. **Teacher clash** — a teacher can't teach two things at once.
2. **Room clash** — a room can't host two classes at once.
3. **Student/group clash** — a group can't attend two courses at once
   (this is what protects multidisciplinary cross-department selections).
4. **Teacher availability** — by construction (no variable created).
5. **Room capacity** — by construction.
6. **Lab requirement** — by construction (room type must match).
7. **Course weekly hours** — exact count of sessions per course.
8. **Teacher-course compatibility** — only `CourseOffering` pairs used.
9. **Student course selection** — only `StudentCourseSelection` pairs used.
10. **No duplicate assignment** — guaranteed by the boolean formulation and
    constraints 1–3.

### Soft constraints (weighted objective, minimised)
- Isolated free-period gaps for student groups and for teachers.
- Daily overload (classes/day above a configurable target).
- Long unbroken runs of consecutive classes.
- A course repeating more than once on the same day (encourages spreading
  weekly hours across the week).

Weights live in `config.py` (`WEIGHT_*`, `DAILY_TARGET_PERIODS`,
`MAX_CONSECUTIVE_BEFORE_PENALTY`) and are fully tunable without touching the
solver code.

### Objective function
```
minimize:  Σ (weight_i × soft_violation_i)   [− preserve_bonus during re-optimization]
```

## 7. Conflict Detection

`services/conflict_service.py` produces human-readable conflict descriptions
at two points:

- **Before generation** — structural issues (no qualified/available teacher
  for a course, no suitable room) detected directly from enrolment data.
- **After generation** — a full scan of the produced timetable for
  teacher/room/student/capacity clashes (should be zero hard conflicts for
  an OPTIMAL/FEASIBLE CP-SAT run).

The same detector also scores a deliberately unintelligent **naive
first-fit baseline** (`TimetableGenerator.naive_baseline`) purely so the
**AI Optimization Insights** page can show an honest, non-fabricated
before/after comparison — it is never used as an actual timetable.

## 8. What-If Re-optimization

On the **Generate Timetable** page: mark a room unavailable and click
**Re-Optimize**. `services/timetable_service.generate_timetable(..., preserve=True)`
re-solves the model with a bonus term in the objective for keeping each
assignment that matches the previous `GenerationRun`, so the solver
naturally minimises disruption while still guaranteeing zero hard
conflicts under the new constraint.

## 9. Installation & Running

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env          # optional, sane defaults are built in

python seed/seed_data.py      # creates + seeds timetable.db
python app.py
```

Open **http://127.0.0.1:5000**.

### Demo credentials (created by the seed script)
| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Teacher | `dr.sharma` | `teacher123` |
| Student | `student1` | `student123` |

## 10. API Documentation (selected endpoints)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/login` | Login (session cookie + JWT) |
| GET/POST | `/api/courses` | List / create courses |
| PUT/DELETE | `/api/courses/<id>` | Update / delete a course |
| POST | `/api/course-offerings` | Assign a teacher to a course |
| GET/POST | `/api/course-selection` | Group ↔ course enrolment (NEP core) |
| GET/POST | `/api/teachers`, `/api/students`, `/api/rooms`, `/api/time-slots` | CRUD |
| POST | `/api/teacher-availability` | Set a teacher's per-slot availability |
| **POST** | **`/api/generate-timetable`** | **Run the CP-SAT optimizer** |
| **POST** | **`/api/reoptimize`** | **What-if re-optimization** |
| GET | `/api/timetable?group_id=`/`teacher_id=` | Fetch the active timetable |
| GET | `/api/conflicts?stage=before\|after` | Human-readable conflict list |
| GET | `/api/insights` | Solver stats for the AI Insights page |
| GET | `/api/dashboard/summary`, `/api/dashboard/charts` | Dashboard data |

All endpoints return structured JSON errors (never a bare `"Error"`) and use
proper HTTP status codes (400/401/403/404/409/422).

## 11. Demo Workflow (matches the SIH presentation script)

1. Login as **admin**.
2. Show **Departments** → **Teachers** → **Courses** (point out course types).
3. Show **Course Selection** — a CSE group taking "Economics"; an ECE group
   taking "Psychology" — the NEP-2020 multidisciplinary proof point.
4. Show **Rooms** and **Availability**.
5. Go to **Generate Timetable** → click **Generate**.
6. Open **Conflicts** — before vs after.
7. Open **AI Optimization Insights** — variables, constraints, solver
   status, objective score, improvement %.
8. Open **Timetable Grid** — view by group, then by teacher.
9. Open **Analytics** — room/teacher utilization, charts.
10. Back on **Generate Timetable**: mark a room unavailable → **Re-Optimize**
    → show that most of the schedule was preserved and the new constraint
    is respected.

## 12. Testing

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

- `tests/test_constraints.py` — isolates individual hard constraints
  (teacher/room/group clash, capacity, lab requirement, availability,
  weekly hours, cross-department/NEP selection) against small hand-built
  data bundles.
- `tests/test_optimizer.py` — full-pipeline tests of
  `TimetableGenerator` (valid timetable, no double-booking, naive baseline,
  infeasibility explanation).
- `tests/test_routes.py` — Flask test-client integration tests (auth,
  CRUD, generation, re-optimization, dashboard) against an isolated
  in-memory SQLite database.

## 13. Error Handling

The solver never returns a bare "Error". `TimetableGenerator._explain_infeasibility`
inspects demand vs. supply (labs vs. lab-requiring courses, weekly hours vs.
available slots, missing qualified/available teachers) and returns a
specific, readable explanation, e.g.:

> "No available qualified teacher exists for course id 7 (group id 3)."

## 14. Future Improvements

- Multiple ranked candidate solutions (CP-SAT solution pooling / hint-based
  re-solves) rather than a single best timetable.
- Room-change minimisation and explicit lunch/break spacing as additional
  soft constraints.
- Course prerequisites (`CoursePrerequisite` model is present but not yet
  wired into the solver).
- Migrate `DATABASE_URL` to PostgreSQL/MySQL for multi-institution scale.
- Per-student (not just per-group) elective scheduling for institutions
  where group cohorts fully diverge on electives.

## 15. SIH Presentation Talking Points

- "The AI here is Google OR-Tools **CP-SAT constraint optimization**, not a
  predictive ML model — there's nothing to predict, there's a scheduling
  problem to *solve* optimally."
- "Every hard constraint — teacher clashes, room clashes, **student clashes
  across departments** — is enforced by the solver, not by a rulebook we
  wrote by hand."
- "The **Insights** page shows our own naive baseline scheduler failing
  with real conflicts, and CP-SAT resolving them to zero hard conflicts —
  the improvement is measured, not claimed."
- "**What-If Re-optimization** demonstrates the system responding to a
  real-world disruption (a room going offline) in seconds, not hours of
  manual rework."
