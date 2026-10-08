from flask import Blueprint, jsonify
from app.auth import role_required
from app.database.db import get_db

owner_analytics_bp = Blueprint(
    "owner_analytics",
    __name__,
    url_prefix="/owner/analytics"
)


@owner_analytics_bp.get("/overview")
@role_required("owner")
def overview():

    conn = get_db()

    revenue = conn.execute("""
        SELECT COALESCE(SUM(amount),0) AS value
        FROM payments
        WHERE status='success'
    """).fetchone()["value"]

    bookings = conn.execute("""
        SELECT COUNT(*) AS value
        FROM bookings
    """).fetchone()["value"]

    completed = conn.execute("""
        SELECT COUNT(*) AS value
        FROM bookings
        WHERE status='completed'
    """).fetchone()["value"]

    active = conn.execute("""
        SELECT COUNT(*) AS value
        FROM bookings
        WHERE status IN
        ('pending','assigned','accepted','in_progress')
    """).fetchone()["value"]

    customers = conn.execute("""
        SELECT COUNT(*) AS value
        FROM users
        WHERE role='customer'
    """).fetchone()["value"]

    technicians = conn.execute("""
        SELECT COUNT(*) AS value
        FROM users
        WHERE role='technician'
        AND status='approved'
    """).fetchone()["value"]

    sellers = conn.execute("""
        SELECT COUNT(*) AS value
        FROM users
        WHERE role='seller'
        AND status='approved'
    """).fetchone()["value"]

    complaints = conn.execute("""
        SELECT COUNT(*) AS value
        FROM complaints
        WHERE status IN ('open','in_progress')
    """).fetchone()["value"]

    reviews = conn.execute("""
        SELECT
            COALESCE(AVG(rating),0) AS average,
            COUNT(*) AS total
        FROM reviews
    """).fetchone()

    conn.close()

    return jsonify({
        "revenue": revenue,
        "bookings": bookings,
        "completed_bookings": completed,
        "active_bookings": active,
        "customers": customers,
        "technicians": technicians,
        "sellers": sellers,
        "open_complaints": complaints,
        "average_rating": round(reviews["average"], 2),
        "total_reviews": reviews["total"]
    })


@owner_analytics_bp.get("/technicians")
@role_required("owner")
def technician_performance():

    conn = get_db()

    rows = conn.execute("""
        SELECT
            u.id,
            u.name,
            u.city,
            u.skill,
            COUNT(b.id) AS total_jobs,
            SUM(
                CASE
                    WHEN b.status='completed'
                    THEN 1 ELSE 0
                END
            ) AS completed_jobs,
            SUM(
                CASE
                    WHEN b.status IN
                    ('assigned','accepted','in_progress')
                    THEN 1 ELSE 0
                END
            ) AS active_jobs
        FROM users u
        LEFT JOIN bookings b
            ON b.technician_id=u.id
        WHERE u.role='technician'
        GROUP BY u.id
        ORDER BY completed_jobs DESC
    """).fetchall()

    conn.close()

    return jsonify({
        "technicians":[dict(x) for x in rows]
    })


@owner_analytics_bp.get("/services")
@role_required("owner")
def service_performance():

    conn = get_db()

    rows = conn.execute("""
        SELECT
            s.id,
            s.name,
            COUNT(b.id) AS bookings
        FROM services s
        LEFT JOIN bookings b
            ON b.service_id=s.id
        GROUP BY s.id
        ORDER BY bookings DESC
    """).fetchall()

    conn.close()

    return jsonify({
        "services":[dict(x) for x in rows]
    })
