from flask import Blueprint, jsonify, request, render_template
from app.auth import role_required, get_current_user
from app.database.db import get_db

owner_bp = Blueprint("owner", __name__, url_prefix="/owner")


@owner_bp.get("")
@role_required("owner")
def owner_dashboard():
    user = get_current_user()
    return render_template("owner.html", user=user)


@owner_bp.get("/stats")
@role_required("owner")
def owner_stats():
    conn = get_db()

    data = {
        "customers": conn.execute(
            "SELECT COUNT(*) AS total FROM users WHERE role='customer'"
        ).fetchone()["total"],

        "technicians": conn.execute(
            "SELECT COUNT(*) AS total FROM users WHERE role='technician'"
        ).fetchone()["total"],

        "sellers": conn.execute(
            "SELECT COUNT(*) AS total FROM users WHERE role='seller'"
        ).fetchone()["total"],

        "pending_users": conn.execute(
            "SELECT COUNT(*) AS total FROM users WHERE status='pending'"
        ).fetchone()["total"],

        "bookings": conn.execute(
            "SELECT COUNT(*) AS total FROM bookings"
        ).fetchone()["total"],

        "active_bookings": conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM bookings
            WHERE status IN ('pending','assigned','accepted','in_progress')
            """
        ).fetchone()["total"]
    }

    conn.close()
    return jsonify(data)


@owner_bp.get("/pending-users")
@role_required("owner")
def pending_users():
    conn = get_db()

    users = conn.execute(
        """
        SELECT id,name,phone,role,status,address,city,pincode,
               skill,experience,business_name,gstin,pan,
               product_category,created_at
        FROM users
        WHERE status='pending'
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return jsonify({
        "users": [dict(user) for user in users]
    })


@owner_bp.post("/users/<int:user_id>/approve")
@role_required("owner")
def approve_user(user_id):
    conn = get_db()

    user = conn.execute(
        "SELECT id,role,status FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    if not user:
        conn.close()
        return jsonify({"error":"User not found"}), 404

    if user["role"] not in {"technician","seller"}:
        conn.close()
        return jsonify({"error":"Invalid role"}), 400

    conn.execute(
        "UPDATE users SET status='approved' WHERE id=?",
        (user_id,)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message":"User approved",
        "user_id":user_id
    })


@owner_bp.post("/users/<int:user_id>/reject")
@role_required("owner")
def reject_user(user_id):
    conn = get_db()

    user = conn.execute(
        "SELECT id,role FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    if not user:
        conn.close()
        return jsonify({"error":"User not found"}), 404

    conn.execute(
        "UPDATE users SET status='rejected' WHERE id=?",
        (user_id,)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message":"User rejected",
        "user_id":user_id
    })


@owner_bp.get("/bookings")
@role_required("owner")
def all_bookings():
    conn = get_db()

    bookings = conn.execute(
        """
        SELECT
            b.id,
            b.status,
            b.address,
            b.created_at,
            s.name AS service_name,
            c.id AS customer_id,
            c.name AS customer_name,
            c.phone AS customer_phone,
            t.id AS technician_id,
            t.name AS technician_name,
            t.phone AS technician_phone
        FROM bookings b
        JOIN services s ON s.id=b.service_id
        JOIN users c ON c.id=b.customer_id
        LEFT JOIN users t ON t.id=b.technician_id
        ORDER BY b.id DESC
        """
    ).fetchall()

    conn.close()

    return jsonify({
        "bookings":[dict(b) for b in bookings]
    })


@owner_bp.get("/technicians")
@role_required("owner")
def technicians():
    conn = get_db()

    users = conn.execute(
        """
        SELECT id,name,phone,skill,experience,city,status
        FROM users
        WHERE role='technician'
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return jsonify({
        "technicians":[dict(u) for u in users]
    })


@owner_bp.get("/customers")
@role_required("owner")
def customers():
    conn = get_db()

    users = conn.execute(
        """
        SELECT id,name,phone,address,city,pincode,status,created_at
        FROM users
        WHERE role='customer'
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return jsonify({
        "customers":[dict(u) for u in users]
    })


@owner_bp.get("/sellers")
@role_required("owner")
def sellers():
    conn = get_db()

    users = conn.execute(
        """
        SELECT id,name,phone,business_name,gstin,pan,
               product_category,city,status,created_at
        FROM users
        WHERE role='seller'
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return jsonify({
        "sellers":[dict(u) for u in users]
    })


@owner_bp.post("/bookings/<int:booking_id>/assign")
@role_required("owner")
def assign_booking(booking_id):
    data = request.get_json(silent=True) or {}
    technician_id = data.get("technician_id")

    if not technician_id:
        return jsonify({"error":"Technician ID is required"}), 400

    conn = get_db()

    technician = conn.execute(
        """
        SELECT id,role,status
        FROM users
        WHERE id=?
        """,
        (technician_id,)
    ).fetchone()

    if not technician:
        conn.close()
        return jsonify({"error":"Technician not found"}), 404

    if technician["role"] != "technician":
        conn.close()
        return jsonify({"error":"User is not a technician"}), 400

    if technician["status"] != "approved":
        conn.close()
        return jsonify({"error":"Technician is not approved"}), 400

    booking = conn.execute(
        "SELECT id,status FROM bookings WHERE id=?",
        (booking_id,)
    ).fetchone()

    if not booking:
        conn.close()
        return jsonify({"error":"Booking not found"}), 404

    conn.execute(
        """
        UPDATE bookings
        SET technician_id=?,status='assigned'
        WHERE id=?
        """,
        (technician_id, booking_id)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message":"Technician assigned",
        "booking_id":booking_id,
        "technician_id":technician_id,
        "status":"assigned"
    })


@owner_bp.post("/bookings/<int:booking_id>/unassign")
@role_required("owner")
def unassign_booking(booking_id):
    conn = get_db()

    booking = conn.execute(
        "SELECT id FROM bookings WHERE id=?",
        (booking_id,)
    ).fetchone()

    if not booking:
        conn.close()
        return jsonify({"error":"Booking not found"}), 404

    conn.execute(
        """
        UPDATE bookings
        SET technician_id=NULL,status='pending'
        WHERE id=?
        """,
        (booking_id,)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message":"Technician unassigned",
        "booking_id":booking_id,
        "status":"pending"
    })
