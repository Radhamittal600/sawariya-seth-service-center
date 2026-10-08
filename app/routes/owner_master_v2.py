
from flask import Blueprint, jsonify, request
from datetime import datetime

from app.auth import role_required, get_current_user
from app.database.db import get_db

owner_master_v2_bp = Blueprint(
    "owner_master_v2",
    __name__,
    url_prefix="/owner/master-v2"
)


def audit(conn, user_id, action, target_type="", target_id=None, details=""):
    try:
        conn.execute("""
            INSERT INTO audit_logs
            (user_id, action, target_type, target_id, details, created_at)
            VALUES (?,?,?,?,?,?)
        """, (
            user_id,
            action,
            target_type,
            target_id,
            details,
            datetime.utcnow().isoformat()
        ))
    except Exception:
        pass


# =========================================================
# MASTER DASHBOARD
# =========================================================

@owner_master_v2_bp.get("/dashboard")
@role_required("owner")
def dashboard():

    conn = get_db()

    def count(table, where=""):
        try:
            return conn.execute(
                f"SELECT COUNT(*) FROM {table} {where}"
            ).fetchone()[0]
        except Exception:
            return 0

    data = {
        "users": count("users"),
        "customers": count(
            "users",
            "WHERE role='customer'"
        ),
        "technicians": count(
            "users",
            "WHERE role='technician'"
        ),
        "sellers": count(
            "users",
            "WHERE role='seller'"
        ),
        "pending_users": count(
            "users",
            "WHERE status='pending'"
        ),
        "blocked_users": count(
            "users",
            "WHERE status='blocked'"
        ),
        "bookings": count("bookings"),
        "active_bookings": count(
            "bookings",
            """WHERE status IN
            ('pending','assigned','accepted','in_progress')"""
        ),
        "completed_bookings": count(
            "bookings",
            "WHERE status='completed'"
        ),
        "services": count("services"),
        "products": count("products"),
        "orders": count("orders"),
        "complaints": count("complaints"),
        "reviews": count("reviews"),
        "notifications": count("notifications"),
        "security_events": count("security_events"),
        "audit_logs": count("audit_logs"),
        "payments": count("payments"),
        "commissions": count("commissions"),
        "refunds": count("refunds"),
        "kyc_documents": count("kyc_documents")
    }

    conn.close()

    return jsonify(data)


# =========================================================
# ALL USERS
# =========================================================

@owner_master_v2_bp.get("/users")
@role_required("owner")
def users():

    conn = get_db()

    rows = conn.execute("""
        SELECT
            id,
            name,
            phone,
            role,
            status,
            created_at
        FROM users
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return jsonify({
        "users": [dict(row) for row in rows]
    })


# =========================================================
# APPROVE USER
# =========================================================

@owner_master_v2_bp.post("/users/<int:user_id>/approve")
@role_required("owner")
def approve_user(user_id):

    owner = get_current_user()

    conn = get_db()

    user = conn.execute("""
        SELECT id, name, role, status
        FROM users
        WHERE id=?
    """, (user_id,)).fetchone()

    if not user:
        conn.close()
        return jsonify({
            "error": "User not found"
        }), 404

    conn.execute("""
        UPDATE users
        SET status='approved'
        WHERE id=?
          AND role!='owner'
    """, (user_id,))

    audit(
        conn,
        owner["id"],
        "approve_user",
        "user",
        user_id,
        f"Approved {user['role']}"
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "User approved"
    })


# =========================================================
# BLOCK USER
# =========================================================

@owner_master_v2_bp.post("/users/<int:user_id>/block")
@role_required("owner")
def block_user(user_id):

    owner = get_current_user()

    conn = get_db()

    user = conn.execute("""
        SELECT id, role
        FROM users
        WHERE id=?
    """, (user_id,)).fetchone()

    if not user:
        conn.close()
        return jsonify({
            "error": "User not found"
        }), 404

    if user["role"] == "owner":
        conn.close()
        return jsonify({
            "error": "Owner account cannot be blocked"
        }), 403

    conn.execute("""
        UPDATE users
        SET status='blocked'
        WHERE id=?
    """, (user_id,))

    audit(
        conn,
        owner["id"],
        "block_user",
        "user",
        user_id,
        "User blocked by owner"
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "User blocked"
    })


# =========================================================
# UNBLOCK USER
# =========================================================

@owner_master_v2_bp.post("/users/<int:user_id>/unblock")
@role_required("owner")
def unblock_user(user_id):

    owner = get_current_user()

    conn = get_db()

    user = conn.execute("""
        SELECT id, role
        FROM users
        WHERE id=?
    """, (user_id,)).fetchone()

    if not user:
        conn.close()
        return jsonify({
            "error": "User not found"
        }), 404

    conn.execute("""
        UPDATE users
        SET status='approved'
        WHERE id=?
          AND role!='owner'
    """, (user_id,))

    audit(
        conn,
        owner["id"],
        "unblock_user",
        "user",
        user_id,
        "User unblocked by owner"
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "User unblocked"
    })


# =========================================================
# BOOKINGS
# =========================================================

@owner_master_v2_bp.get("/bookings")
@role_required("owner")
def bookings():

    conn = get_db()

    rows = conn.execute("""
        SELECT
            b.id,
            b.status,
            b.address,
            b.created_at,
            b.customer_id,
            b.technician_id,
            u.name AS customer_name,
            t.name AS technician_name,
            s.name AS service_name
        FROM bookings b
        LEFT JOIN users u
            ON u.id=b.customer_id
        LEFT JOIN users t
            ON t.id=b.technician_id
        LEFT JOIN services s
            ON s.id=b.service_id
        ORDER BY b.id DESC
    """).fetchall()

    conn.close()

    return jsonify({
        "bookings": [dict(row) for row in rows]
    })


# =========================================================
# SECURITY EVENTS
# =========================================================

@owner_master_v2_bp.get("/security")
@role_required("owner")
def security():

    conn = get_db()

    rows = conn.execute("""
        SELECT *
        FROM security_events
        ORDER BY id DESC
        LIMIT 100
    """).fetchall()

    conn.close()

    return jsonify({
        "events": [dict(row) for row in rows]
    })


# =========================================================
# AUDIT LOGS
# =========================================================

@owner_master_v2_bp.get("/audit")
@role_required("owner")
def audit_logs():

    conn = get_db()

    rows = conn.execute("""
        SELECT *
        FROM audit_logs
        ORDER BY id DESC
        LIMIT 200
    """).fetchall()

    conn.close()

    return jsonify({
        "logs": [dict(row) for row in rows]
    })


# =========================================================
# SYSTEM STATUS
# =========================================================

@owner_master_v2_bp.get("/system")
@role_required("owner")
def system_status():

    conn = get_db()

    result = {
        "database": "online",
        "server_time": datetime.utcnow().isoformat(),
        "tables": {}
    }

    tables = [
        "users",
        "bookings",
        "services",
        "products",
        "orders",
        "payments",
        "commissions",
        "refunds",
        "complaints",
        "reviews",
        "notifications",
        "kyc_documents",
        "security_events",
        "audit_logs",
        "video_calls"
    ]

    for table in tables:
        try:
            result["tables"][table] = conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
        except Exception:
            result["tables"][table] = None

    conn.close()

    return jsonify(result)
