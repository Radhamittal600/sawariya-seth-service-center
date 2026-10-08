from flask import Blueprint, jsonify, request
from app.auth import role_required, get_current_user
from app.database.db import get_db

owner_notifications_bp = Blueprint(
    "owner_notifications",
    __name__,
    url_prefix="/owner/notifications"
)


@owner_notifications_bp.get("")
@role_required("owner")
def notification_list():
    conn = get_db()

    rows = conn.execute("""
        SELECT
            n.id,
            n.user_id,
            n.title,
            n.message,
            n.notification_type,
            n.is_read,
            n.created_at,
            u.name AS user_name,
            u.role AS user_role
        FROM notifications n
        LEFT JOIN users u ON u.id = n.user_id
        ORDER BY n.id DESC
        LIMIT 200
    """).fetchall()

    conn.close()

    return jsonify({
        "notifications": [dict(x) for x in rows]
    })


@owner_notifications_bp.post("/send")
@role_required("owner")
def send_notification():
    data = request.get_json(silent=True) or {}

    title = str(data.get("title", "")).strip()
    message = str(data.get("message", "")).strip()
    target_role = str(data.get("target_role", "all")).strip().lower()

    if not title or not message:
        return jsonify({
            "error": "Title and message are required"
        }), 400

    allowed_roles = {
        "all",
        "customer",
        "technician",
        "seller"
    }

    if target_role not in allowed_roles:
        return jsonify({
            "error": "Invalid target role"
        }), 400

    conn = get_db()

    if target_role == "all":
        users = conn.execute("""
            SELECT id
            FROM users
            WHERE role IN ('customer','technician','seller')
            AND status='approved'
        """).fetchall()
    else:
        users = conn.execute("""
            SELECT id
            FROM users
            WHERE role=?
            AND status='approved'
        """, (target_role,)).fetchall()

    for user in users:
        conn.execute("""
            INSERT INTO notifications
            (
                user_id,
                title,
                message,
                notification_type
            )
            VALUES (?, ?, ?, 'owner_announcement')
        """, (
            user["id"],
            title,
            message
        ))

    conn.commit()

    sent = len(users)

    conn.close()

    return jsonify({
        "message": "Notification sent",
        "target_role": target_role,
        "recipients": sent
    })


@owner_notifications_bp.get("/summary")
@role_required("owner")
def notification_summary():
    conn = get_db()

    total = conn.execute("""
        SELECT COUNT(*) AS total
        FROM notifications
    """).fetchone()["total"]

    unread = conn.execute("""
        SELECT COUNT(*) AS total
        FROM notifications
        WHERE is_read=0
    """).fetchone()["total"]

    conn.close()

    return jsonify({
        "total": total,
        "unread": unread
    })
