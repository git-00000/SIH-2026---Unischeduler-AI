"""
Application entry point.

Run with:  python app.py
Then open: http://127.0.0.1:5000
"""
import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from config import config_by_name
from database.db import db


def create_app(env=None):
    app = Flask(__name__)
    env = env or os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config_by_name.get(env, config_by_name["development"]))

    db.init_app(app)
    CORS(app)
    JWTManager(app)

    # ---- Blueprints ----
    from routes.auth_routes import auth_bp
    from routes.course_routes import course_bp
    from routes.teacher_routes import teacher_bp
    from routes.student_routes import student_bp
    from routes.room_routes import room_bp
    from routes.timetable_routes import timetable_bp
    from routes.dashboard_routes import dashboard_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(course_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(room_bp)
    app.register_blueprint(timetable_bp)
    app.register_blueprint(dashboard_bp)

    # ---- Error handlers (spec requires useful errors, never bare "Error") ----
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad request", "details": str(e)}), 400

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
