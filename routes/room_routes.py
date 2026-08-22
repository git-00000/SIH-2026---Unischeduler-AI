"""
Room + TimeSlot CRUD, and the "mark room/teacher unavailable" toggles used
by the What-If Re-optimization demo feature.
"""
from flask import Blueprint, request, jsonify, render_template

from database.db import db
from database.models import Room, TimeSlot, ROOM_TYPES
from routes.auth_routes import login_required, role_required

room_bp = Blueprint("rooms", __name__)


@room_bp.route("/rooms", methods=["GET"])
@login_required
def rooms_page():
    return render_template("rooms.html", room_types=ROOM_TYPES)


@room_bp.route("/api/rooms", methods=["GET"])
@login_required
def list_rooms():
    return jsonify([r.to_dict() for r in Room.query.all()])


@room_bp.route("/api/rooms", methods=["POST"])
@role_required("admin")
def create_room():
    payload = request.get_json(force=True)
    if not payload.get("room_number") or not payload.get("capacity"):
        return jsonify({"error": "room_number and capacity are required"}), 400
    if Room.query.filter_by(room_number=payload["room_number"]).first():
        return jsonify({"error": "room_number already exists"}), 409

    room = Room(
        room_number=payload["room_number"], capacity=payload["capacity"],
        room_type=payload.get("room_type", "Classroom"),
        building=payload.get("building", "Main Block"),
        is_available=payload.get("is_available", True),
    )
    db.session.add(room)
    db.session.commit()
    return jsonify(room.to_dict()), 201


@room_bp.route("/api/rooms/<int:room_id>", methods=["PUT"])
@role_required("admin")
def update_room(room_id):
    room = Room.query.get_or_404(room_id)
    payload = request.get_json(force=True)
    for field in ["room_number", "capacity", "room_type", "building", "is_available"]:
        if field in payload:
            setattr(room, field, payload[field])
    db.session.commit()
    return jsonify(room.to_dict())


@room_bp.route("/api/rooms/<int:room_id>", methods=["DELETE"])
@role_required("admin")
def delete_room(room_id):
    room = Room.query.get_or_404(room_id)
    db.session.delete(room)
    db.session.commit()
    return jsonify({"message": "Room deleted"})


@room_bp.route("/api/rooms/<int:room_id>/toggle-availability", methods=["POST"])
@role_required("admin")
def toggle_room_availability(room_id):
    """Used by the SIH demo: 'Mark Room 203 Unavailable' button."""
    room = Room.query.get_or_404(room_id)
    payload = request.get_json(silent=True) or {}
    room.is_available = bool(payload.get("is_available", not room.is_available))
    db.session.commit()
    return jsonify(room.to_dict())


# ------------------------------------------------------------- time slots
@room_bp.route("/api/time-slots", methods=["GET"])
@login_required
def list_time_slots():
    slots = TimeSlot.query.order_by(TimeSlot.day, TimeSlot.period_number).all()
    return jsonify([s.to_dict() for s in slots])


@room_bp.route("/api/time-slots", methods=["POST"])
@role_required("admin")
def create_time_slot():
    payload = request.get_json(force=True)
    required = ["day", "start_time", "end_time", "period_number"]
    missing = [f for f in required if not payload.get(f) and payload.get(f) != 0]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    slot = TimeSlot(
        day=payload["day"], start_time=payload["start_time"], end_time=payload["end_time"],
        period_number=payload["period_number"], is_break=payload.get("is_break", False),
    )
    db.session.add(slot)
    db.session.commit()
    return jsonify(slot.to_dict()), 201


@room_bp.route("/api/time-slots/<int:slot_id>", methods=["DELETE"])
@role_required("admin")
def delete_time_slot(slot_id):
    slot = TimeSlot.query.get_or_404(slot_id)
    db.session.delete(slot)
    db.session.commit()
    return jsonify({"message": "Time slot deleted"})
