from flask import Blueprint, jsonify
from app.auth import role_required
from app.database.db import get_db

owner_operations_bp = Blueprint(
    "owner_operations",
    __name__,
    url_prefix="/owner/operations"
)


@owner_operations_bp.get("/technicians")
@role_required("owner")
def technician_overview():

    conn = get_db()

    technicians = conn.execute("""
        SELECT
            u.id,
            u.name,
            u.phone,
            u.skill,
            u.experience,
            u.city,
            u.status,
            COUNT(b.id) AS total_jobs,
            SUM(
                CASE
                    WHEN b.status IN ('assigned','accepted','in_progress')
                    THEN 1 ELSE 0
                END
            ) AS active_jobs,
            SUM(
                CASE
                    WHEN b.status='completed'
                    THEN 1 ELSE 0
                END
            ) AS completed_jobs
        FROM users u
        LEFT JOIN bookings b
            ON b.technician_id=u.id
        WHERE u.role='technician'
        GROUP BY u.id
        ORDER BY u.id DESC
    """).fetchall()

    conn.close()

    return jsonify({
        "technicians": [dict(x) for x in technicians]
    })


@owner_operations_bp.get("/active")
@role_required("owner")
def active_jobs():

    conn = get_db()

    jobs = conn.execute("""
        SELECT
            b.id,
            b.status,
            b.address,
            b.created_at,
            s.name AS service_name,
            c.name AS customer_name,
            t.name AS technician_name,
            b.technician_lat,
            b.technician_lng,
            b.location_updated_at
        FROM bookings b
        JOIN services s ON s.id=b.service_id
        JOIN users c ON c.id=b.customer_id
        LEFT JOIN users t ON t.id=b.technician_id
        WHERE b.status IN ('assigned','accepted','in_progress')
        ORDER BY b.id DESC
    """).fetchall()

    conn.close()

    return jsonify({
        "active_jobs": [dict(x) for x in jobs]
    })
