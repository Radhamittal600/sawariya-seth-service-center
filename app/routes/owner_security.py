from flask import Blueprint, jsonify
from app.auth import role_required
from app.database.db import get_db

owner_security_bp = Blueprint(
    "owner_security",
    __name__,
    url_prefix="/owner/security"
)


@owner_security_bp.get("/events")
@role_required("owner")
def security_events():
    conn = get_db()

    rows = conn.execute("""
        SELECT
            s.id,
            s.user_id,
            s.event_type,
            s.ip_address,
            s.details,
            s.severity,
            s.created_at,
            u.name AS user_name,
            u.phone AS user_phone
        FROM security_events s
        LEFT JOIN users u ON u.id=s.user_id
        ORDER BY s.id DESC
        LIMIT 200
    """).fetchall()

    conn.close()

    return jsonify({
        "events": [dict(x) for x in rows]
    })


@owner_security_bp.get("/audit")
@role_required("owner")
def audit_logs():
    conn = get_db()

    rows = conn.execute("""
        SELECT
            a.id,
            a.user_id,
            a.action,
            a.details,
            a.created_at,
            u.name AS user_name,
            u.phone AS user_phone
        FROM audit_logs a
        LEFT JOIN users u ON u.id=a.user_id
        ORDER BY a.id DESC
        LIMIT 200
    """).fetchall()

    conn.close()

    return jsonify({
        "logs": [dict(x) for x in rows]
    })


@owner_security_bp.get("/summary")
@role_required("owner")
def security_summary():
    conn = get_db()

    critical = conn.execute("""
        SELECT COUNT(*) AS total
        FROM security_events
        WHERE severity='critical'
    """).fetchone()["total"]

    warnings = conn.execute("""
        SELECT COUNT(*) AS total
        FROM security_events
        WHERE severity='warning'
    """).fetchone()["total"]

    audit_count = conn.execute("""
        SELECT COUNT(*) AS total
        FROM audit_logs
    """).fetchone()["total"]

    conn.close()

    return jsonify({
        "critical_events": critical,
        "warning_events": warnings,
        "audit_logs": audit_count
    })
