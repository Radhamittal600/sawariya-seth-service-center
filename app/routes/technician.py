
from flask import Blueprint, jsonify, request
from datetime import datetime

from app.auth import role_required, get_current_user
from app.database.db import get_db

technician_bp = Blueprint(
    "technician",
    __name__,
    url_prefix="/technician"
)


# =========================================================
# MY JOBS
# =========================================================

@technician_bp.get("/jobs")
@role_required("technician")
def jobs():

    user = get_current_user()

    conn = get_db()

    rows = conn.execute("""
        SELECT
            b.id,
            b.customer_id,
            b.technician_id,
            b.service_id,
            b.status,
            b.address,
            b.created_at,
            b.technician_lat,
            b.technician_lng,
            b.location_updated_at,
            u.name AS customer_name,
            u.phone AS customer_phone,
            s.name AS service_name
        FROM bookings b
        LEFT JOIN users u
            ON u.id = b.customer_id
        LEFT JOIN services s
            ON s.id = b.service_id
        WHERE b.technician_id = ?
        ORDER BY b.id DESC
    """, (user["id"],)).fetchall()

    conn.close()

    return jsonify({
        "jobs": [
            dict(row) for row in rows
        ]
    })


# =========================================================
# ACCEPT
# =========================================================

@technician_bp.post("/jobs/<int:booking_id>/accept")
@role_required("technician")
def accept_job(booking_id):

    user = get_current_user()

    conn = get_db()

    booking = conn.execute("""
        SELECT id, technician_id, status
        FROM bookings
        WHERE id = ?
    """, (booking_id,)).fetchone()

    if not booking:
        conn.close()
        return jsonify({
            "error": "Booking not found"
        }), 404

    if booking["technician_id"] != user["id"]:
        conn.close()
        return jsonify({
            "error": "This job is not assigned to you"
        }), 403

    if booking["status"] not in (
        "assigned",
        "pending"
    ):
        conn.close()
        return jsonify({
            "error": "Job cannot be accepted now"
        }), 400

    conn.execute("""
        UPDATE bookings
        SET status = 'accepted'
        WHERE id = ?
    """, (booking_id,))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Job accepted"
    })


# =========================================================
# REJECT
# =========================================================

@technician_bp.post("/jobs/<int:booking_id>/reject")
@role_required("technician")
def reject_job(booking_id):

    user = get_current_user()

    conn = get_db()

    booking = conn.execute("""
        SELECT id, technician_id, status
        FROM bookings
        WHERE id = ?
    """, (booking_id,)).fetchone()

    if not booking:
        conn.close()
        return jsonify({
            "error": "Booking not found"
        }), 404

    if booking["technician_id"] != user["id"]:
        conn.close()
        return jsonify({
            "error": "Permission denied"
        }), 403

    conn.execute("""
        UPDATE bookings
        SET technician_id = NULL,
            status = 'pending'
        WHERE id = ?
    """, (booking_id,))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Job rejected"
    })


# =========================================================
# START JOB
# =========================================================

@technician_bp.post("/jobs/<int:booking_id>/start")
@role_required("technician")
def start_job(booking_id):

    user = get_current_user()

    conn = get_db()

    booking = conn.execute("""
        SELECT id, technician_id, status
        FROM bookings
        WHERE id = ?
    """, (booking_id,)).fetchone()

    if not booking:
        conn.close()
        return jsonify({
            "error": "Booking not found"
        }), 404

    if booking["technician_id"] != user["id"]:
        conn.close()
        return jsonify({
            "error": "Permission denied"
        }), 403

    if booking["status"] != "accepted":
        conn.close()
        return jsonify({
            "error": "Accept the job first"
        }), 400

    conn.execute("""
        UPDATE bookings
        SET status = 'in_progress'
        WHERE id = ?
    """, (booking_id,))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Job started"
    })


# =========================================================
# COMPLETE JOB
# =========================================================

@technician_bp.post("/jobs/<int:booking_id>/complete")
@role_required("technician")
def complete_job(booking_id):

    user = get_current_user()

    conn = get_db()

    booking = conn.execute("""
        SELECT id, technician_id, status
        FROM bookings
        WHERE id = ?
    """, (booking_id,)).fetchone()

    if not booking:
        conn.close()
        return jsonify({
            "error": "Booking not found"
        }), 404

    if booking["technician_id"] != user["id"]:
        conn.close()
        return jsonify({
            "error": "Permission denied"
        }), 403

    if booking["status"] != "in_progress":
        conn.close()
        return jsonify({
            "error": "Job is not in progress"
        }), 400

    conn.execute("""
        UPDATE bookings
        SET status = 'completed'
        WHERE id = ?
    """, (booking_id,))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Job completed"
    })


# =========================================================
# LIVE LOCATION
# =========================================================

@technician_bp.post("/location")
@role_required("technician")
def update_location():

    user = get_current_user()

    data = request.get_json(silent=True) or {}

    try:
        lat = float(data.get("lat"))
        lng = float(data.get("lng"))
    except (TypeError, ValueError):
        return jsonify({
            "error": "Invalid latitude/longitude"
        }), 400

    if not (-90 <= lat <= 90):
        return jsonify({
            "error": "Invalid latitude"
        }), 400

    if not (-180 <= lng <= 180):
        return jsonify({
            "error": "Invalid longitude"
        }), 400

    booking_id = data.get("booking_id")

    conn = get_db()

    if booking_id is not None:

        try:
            booking_id = int(booking_id)
        except (TypeError, ValueError):
            conn.close()
            return jsonify({
                "error": "Invalid booking_id"
            }), 400

        booking = conn.execute("""
            SELECT id, technician_id, status
            FROM bookings
            WHERE id = ?
        """, (booking_id,)).fetchone()

        if not booking:
            conn.close()
            return jsonify({
                "error": "Booking not found"
            }), 404

        if booking["technician_id"] != user["id"]:
            conn.close()
            return jsonify({
                "error": "Permission denied"
            }), 403

        conn.execute("""
            UPDATE bookings
            SET technician_lat = ?,
                technician_lng = ?,
                location_updated_at = ?
            WHERE id = ?
        """, (
            lat,
            lng,
            datetime.utcnow().isoformat(),
            booking_id
        ))

    else:

        # Update all active jobs for this technician.
        conn.execute("""
            UPDATE bookings
            SET technician_lat = ?,
                technician_lng = ?,
                location_updated_at = ?
            WHERE technician_id = ?
              AND status IN
                  ('assigned','accepted','in_progress')
        """, (
            lat,
            lng,
            datetime.utcnow().isoformat(),
            user["id"]
        ))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Location updated",
        "lat": lat,
        "lng": lng
    })


# =========================================================
# LOCATION FOR CUSTOMER / OWNER
# =========================================================

@technician_bp.get("/location/<int:booking_id>")
def booking_location(booking_id):

    user = get_current_user()

    if not user:
        return jsonify({
            "error": "Login required"
        }), 401

    conn = get_db()

    booking = conn.execute("""
        SELECT
            id,
            customer_id,
            technician_id,
            status,
            technician_lat,
            technician_lng,
            location_updated_at
        FROM bookings
        WHERE id = ?
    """, (booking_id,)).fetchone()

    if not booking:
        conn.close()
        return jsonify({
            "error": "Booking not found"
        }), 404

    allowed = False

    if user["role"] == "owner":
        allowed = True

    elif user["role"] == "customer":
        allowed = (
            booking["customer_id"] == user["id"]
        )

    elif user["role"] == "technician":
        allowed = (
            booking["technician_id"] == user["id"]
        )

    if not allowed:
        conn.close()
        return jsonify({
            "error": "Permission denied"
        }), 403

    conn.close()

    return jsonify({
        "booking_id": booking["id"],
        "status": booking["status"],
        "technician_id": booking["technician_id"],
        "lat": booking["technician_lat"],
        "lng": booking["technician_lng"],
        "updated_at": booking["location_updated_at"]
    })
