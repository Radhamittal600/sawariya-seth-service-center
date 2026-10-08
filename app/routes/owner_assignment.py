
from flask import Blueprint, jsonify, request
from datetime import datetime

from app.auth import role_required, get_current_user
from app.database.db import get_db

owner_assignment_bp = Blueprint(
    "owner_assignment",
    __name__,
    url_prefix="/owner/assignment"
)


# =========================================================
# TECHNICIANS
# =========================================================

@owner_assignment_bp.get("/technicians")
@role_required("owner")
def technicians():

    conn = get_db()

    rows = conn.execute("""
        SELECT
            id,
            name,
            phone,
            status,
            skill,
            experience,
            city
        FROM users
        WHERE role = 'technician'
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return jsonify({
        "technicians": [
            dict(row) for row in rows
        ]
    })


# =========================================================
# BOOKINGS
# =========================================================

@owner_assignment_bp.get("/bookings")
@role_required("owner")
def bookings():

    conn = get_db()

    rows = conn.execute("""
        SELECT
            b.id,
            b.customer_id,
            b.technician_id,
            b.service_id,
            b.status,
            b.address,
            b.technician_lat,
            b.technician_lng,
            b.location_updated_at,
            u.name AS customer_name,
            t.name AS technician_name,
            s.name AS service_name
        FROM bookings b
        LEFT JOIN users u
            ON u.id = b.customer_id
        LEFT JOIN users t
            ON t.id = b.technician_id
        LEFT JOIN services s
            ON s.id = b.service_id
        ORDER BY b.id DESC
    """).fetchall()

    conn.close()

    return jsonify({
        "bookings": [
            dict(row) for row in rows
        ]
    })


# =========================================================
# ASSIGN TECHNICIAN
# =========================================================

@owner_assignment_bp.post("/booking/<int:booking_id>/assign")
@role_required("owner")
def assign(booking_id):

    data = request.get_json(silent=True) or {}

    try:
        technician_id = int(data.get("technician_id"))
    except (TypeError, ValueError):
        return jsonify({
            "error": "Invalid technician_id"
        }), 400

    conn = get_db()

    booking = conn.execute("""
        SELECT id, customer_id, status
        FROM bookings
        WHERE id = ?
    """, (booking_id,)).fetchone()

    if not booking:
        conn.close()
        return jsonify({
            "error": "Booking not found"
        }), 404

    technician = conn.execute("""
        SELECT id, name, status
        FROM users
        WHERE id = ?
          AND role = 'technician'
    """, (technician_id,)).fetchone()

    if not technician:
        conn.close()
        return jsonify({
            "error": "Technician not found"
        }), 404

    if technician["status"] != "approved":
        conn.close()
        return jsonify({
            "error": "Technician is not approved"
        }), 403

    now = datetime.utcnow().isoformat()

    conn.execute("""
        UPDATE bookings
        SET technician_id = ?,
            status = 'assigned'
        WHERE id = ?
    """, (
        technician_id,
        booking_id
    ))

    conn.execute("""
        INSERT INTO notifications
        (user_id,title,message,created_at)
        VALUES (?,?,?,?)
    """, (
        technician_id,
        "New Job Assigned",
        f"Booking #{booking_id} has been assigned to you.",
        now
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Technician assigned",
        "booking_id": booking_id,
        "technician_id": technician_id
    })


# =========================================================
# UNASSIGN
# =========================================================

@owner_assignment_bp.post("/booking/<int:booking_id>/unassign")
@role_required("owner")
def unassign(booking_id):

    conn = get_db()

    booking = conn.execute("""
        SELECT technician_id
        FROM bookings
        WHERE id = ?
    """, (booking_id,)).fetchone()

    if not booking:
        conn.close()
        return jsonify({
            "error": "Booking not found"
        }), 404

    conn.execute("""
        UPDATE bookings
        SET technician_id = NULL,
            status = 'pending'
        WHERE id = ?
    """, (booking_id,))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Technician unassigned",
        "booking_id": booking_id
    })
