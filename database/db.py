"""
Central SQLAlchemy instance. Kept separate from app.py to avoid circular
imports between models, routes and the Flask app factory.
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
