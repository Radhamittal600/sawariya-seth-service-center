from flask import Blueprint, jsonify, request, render_template
from app.auth import role_required, get_current_user
from app.database.db import get_db
bookings_bp = Blueprint(
    "bookings",
    __name__,
    url_prefix="/bookings"
)


@bookings_bp.post("")
@role_required("customer")
def create_booking():
    data = request.get_json(silent=True) or {}

    service_id = data.get("service_id")
    address = str(data.get("address", "")).strip()

    if not service_id or not address:
        return jsonify({
            "error": "Service and address are required"
        }), 400

    conn = get_db()

    service = conn.execute(
        """
        SELECT id, name
        FROM services
        WHERE id = ? AND active = 1
        """,
        (service_id,),
    ).fetchone()

    if not service:
        conn.close()
        return jsonify({
            "error": "Service not found"
        }), 404

    user = get_current_user()

    cursor = conn.execute(
        """
        INSERT INTO bookings
        (customer_id, service_id, address, status)
        VALUES (?, ?, ?, 'pending')
        """,
        (user["id"], service_id, address),
    )

    conn.commit()

    booking_id = cursor.lastrowid
    conn.close()

    return jsonify({
        "message": "Booking created",
        "booking_id": booking_id,
        "status": "pending"
    }), 201


@bookings_bp.get("/my")
@role_required("customer")
def my_bookings():
    user = get_current_user()

    conn = get_db()

    bookings = conn.execute(
        """
        SELECT
            b.id,
            b.status,
            b.address,
            b.created_at,
            s.name AS service_name,
            t.name AS technician_name
        FROM bookings b
        JOIN services s ON s.id = b.service_id
        LEFT JOIN users t ON t.id = b.technician_id
        WHERE b.customer_id = ?
        ORDER BY b.id DESC
        """,
        (user["id"],),
    ).fetchall()

    conn.close()

    return jsonify({
        "bookings": [dict(booking) for booking in bookings]
    })


@bookings_bp.get("/<int:booking_id>")
@role_required("customer", "technician", "owner")
def get_booking(booking_id):
    conn = get_db()

    booking = conn.execute(
        """
        SELECT
            b.id,
            b.customer_id,
            b.technician_id,
            b.service_id,
            b.status,
            b.address,
            b.created_at,
            s.name AS service_name,
            c.name AS customer_name,
            t.name AS technician_name
        FROM bookings b
        JOIN services s ON s.id = b.service_id
        JOIN users c ON c.id = b.customer_id
        LEFT JOIN users t ON t.id = b.technician_id
        WHERE b.id = ?
        """,
        (booking_id,),
    ).fetchone()

    conn.close()

    if not booking:
        return jsonify({
            "error": "Booking not found"
        }), 404

    return jsonify({
        "booking": dict(booking)
    })
@bookings_bp.get("/<int:booking_id>/technician-location")
@role_required("customer")
def technician_location(booking_id):
    user = get_current_user()

    conn = get_db()

    booking = conn.execute(
        """
        SELECT
            b.id,
            b.customer_id,
            b.technician_id,
            b.status,
            b.technician_lat,
            b.technician_lng,
            b.location_updated_at
        FROM bookings b
        WHERE b.id = ?
        """,
        (booking_id,),
    ).fetchone()

    conn.close()

    if not booking:
        return jsonify({
            "error": "Booking not found"
        }), 404

    if booking["customer_id"] != user["id"]:
        return jsonify({
            "error": "This booking does not belong to you"
        }), 403

    if booking["status"] not in {"accepted", "in_progress"}:
        return jsonify({
            "error": "Technician location is not available"
        }), 400

    if booking["technician_lat"] is None:
        return jsonify({
            "error": "Technician location not available yet"
        }), 404

    return jsonify({
        "booking_id": booking["id"],
        "status": booking["status"],
        "latitude": booking["technician_lat"],
        "longitude": booking["technician_lng"],
        "updated_at": booking["location_updated_at"]
    })
@bookings_bp.get("/<int:booking_id>/track")
@role_required("customer")
def track_booking_page(booking_id):
    user = get_current_user()

    conn = get_db()

    booking = conn.execute(
        """
        SELECT id, customer_id, status
        FROM bookings
        WHERE id = ?
        """,
        (booking_id,),
    ).fetchone()

    conn.close()

    if not booking:
        return jsonify({
            "error": "Booking not found"
        }), 404

    if booking["customer_id"] != user["id"]:
        return jsonify({
            "error": "This booking does not belong to you"
        }), 403

    if booking["status"] not in {"accepted", "in_progress"}:
        return jsonify({
            "error": "Tracking is not active"
        }), 400

    return render_template(
        "tracking.html",
        booking_id=booking_id
    )
