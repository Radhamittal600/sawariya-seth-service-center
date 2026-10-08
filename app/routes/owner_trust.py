from flask import Blueprint, jsonify
from app.auth import role_required
from app.database.db import get_db

owner_trust_bp = Blueprint(
    "owner_trust",
    __name__,
    url_prefix="/owner/trust"
)


@owner_trust_bp.get("/complaints")
@role_required("owner")
def complaints():

    conn = get_db()

    rows = conn.execute("""
        SELECT
            c.id,
            c.booking_id,
            c.subject,
            c.description,
            c.priority,
            c.status,
            c.assigned_to,
            c.created_at,
            u.name AS user_name,
            u.phone AS user_phone
        FROM complaints c
        LEFT JOIN users u ON u.id=c.user_id
        ORDER BY c.id DESC
    """).fetchall()

    conn.close()

    return jsonify({
        "complaints": [dict(x) for x in rows]
    })


@owner_trust_bp.get("/reviews")
@role_required("owner")
def reviews():

    conn = get_db()

    rows = conn.execute("""
        SELECT
            r.id,
            r.booking_id,
            r.rating,
            r.review,
            r.status,
            r.created_at,
            c.name AS customer_name,
            t.name AS technician_name
        FROM reviews r
        LEFT JOIN users c ON c.id=r.customer_id
        LEFT JOIN users t ON t.id=r.technician_id
        ORDER BY r.id DESC
    """).fetchall()

    conn.close()

    return jsonify({
        "reviews": [dict(x) for x in rows]
    })


@owner_trust_bp.get("/tickets")
@role_required("owner")
def support_tickets():

    conn = get_db()

    rows = conn.execute("""
        SELECT
            s.id,
            s.subject,
            s.message,
            s.priority,
            s.status,
            s.created_at,
            u.name AS user_name,
            u.phone AS user_phone
        FROM support_tickets s
        LEFT JOIN users u ON u.id=s.user_id
        ORDER BY s.id DESC
    """).fetchall()

    conn.close()

    return jsonify({
        "tickets": [dict(x) for x in rows]
    })


@owner_trust_bp.get("/summary")
@role_required("owner")
def trust_summary():

    conn = get_db()

    complaints = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM complaints
        WHERE status IN ('open','in_progress')
        """
    ).fetchone()["total"]

    reviews = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM reviews
        WHERE status='pending'
        """
    ).fetchone()["total"]

    tickets = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM support_tickets
        WHERE status IN ('open','in_progress')
        """
    ).fetchone()["total"]

    conn.close()

    return jsonify({
        "open_complaints": complaints,
        "pending_reviews": reviews,
        "open_tickets": tickets
    })
