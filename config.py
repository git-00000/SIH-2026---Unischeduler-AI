"""
Application configuration.
Reads values from environment variables (via python-dotenv) so the same
codebase can move from SQLite (local/demo) to PostgreSQL/MySQL in production
without any code changes -- only the DATABASE_URL needs to change.
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=12)

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'timetable.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ---- Optimizer tunables ----
    # Working days used to build the default timeslot grid (seed script).
    WORKING_DAYS = ["MON", "TUE", "WED", "THU", "FRI"]
    PERIODS_PER_DAY = 7
    SOLVER_TIME_LIMIT_SECONDS = 30

    # Soft-constraint objective weights (see optimizer/objective.py)
    WEIGHT_GROUP_GAP = 10
    WEIGHT_TEACHER_GAP = 8
    WEIGHT_DAILY_OVERLOAD = 6
    WEIGHT_CONSECUTIVE_RUN = 5
    WEIGHT_SAME_DAY_REPEAT = 4
    DAILY_TARGET_PERIODS = 5          # soft target of classes/day/group before penalty
    MAX_CONSECUTIVE_BEFORE_PENALTY = 3  # penalize runs longer than this


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
