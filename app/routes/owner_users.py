from flask import Blueprint, jsonify, request
from app.auth import role_required
from app.database.db import get_db

owner_users_bp = Blueprint(
    "owner_users",
    __name__,
    url_prefix="/owner/users"
)


@owner_users_bp.get("")
@role_required("owner")
def users():
    role = request.args.get("role", "").strip()
    status = request.args.get("status", "").strip()
    search = request.args.get("search", "").strip()

    conn = get_db()

    query = """
        SELECT
            id,
            name,
            phone,
            role,
            status,
            address,
            city,
            pincode,
            skill,
            experience,
            business_name,
            gstin,
            pan,
            product_category,
            created_at
        FROM users
        WHERE 1=1
    """

    params = []

    if role in ("customer", "technician", "seller", "owner"):
        query += " AND role=?"
        params.append(role)

    if status in ("pending", "approved", "rejected", "blocked"):
        query += " AND status=?"
        params.append(status)

    if search:
        query += """
            AND (
                name LIKE ?
                OR phone LIKE ?
                OR business_name LIKE ?
            )
        """
        term = f"%{search}%"
        params.extend([term, term, term])

    query += " ORDER BY id DESC LIMIT 500"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return jsonify({
        "users": [dict(row) for row in rows],
        "count": len(rows)
    })


@owner_users_bp.get("/<int:user_id>")
@role_required("owner")
def user_detail(user_id):
    conn = get_db()

    user = conn.execute("""
        SELECT
            id,
            name,
            phone,
            role,
            status,
            address,
            city,
            pincode,
            skill,
            experience,
            business_name,
            gstin,
            pan,
            product_category,
            created_at
        FROM users
        WHERE id=?
    """, (user_id,)).fetchone()

    conn.close()

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(dict(user))


@owner_users_bp.post("/<int:user_id>/block")
@role_required("owner")
def block_user(user_id):
    conn = get_db()

    user = conn.execute(
        "SELECT id, role FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    if not user:
        conn.close()
        return jsonify({"error": "User not found"}), 404

    if user["role"] == "owner":
        conn.close()
        return jsonify({"error": "Owner account cannot be blocked"}), 403

    conn.execute(
        "UPDATE users SET status='blocked' WHERE id=?",
        (user_id,)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "User blocked",
        "user_id": user_id
    })


@owner_users_bp.post("/<int:user_id>/unblock")
@role_required("owner")
def unblock_user(user_id):
    conn = get_db()

    user = conn.execute(
        "SELECT id, role FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    if not user:
        conn.close()
        return jsonify({"error": "User not found"}), 404

    if user["role"] == "owner":
        conn.close()
        return jsonify({"error": "Owner account cannot be unblocked here"}), 403

    conn.execute(
        "UPDATE users SET status='approved' WHERE id=?",
        (user_id,)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "User unblocked",
        "user_id": user_id
    })


@owner_users_bp.get("/summary")
@role_required("owner")
def user_summary():
    conn = get_db()

    rows = conn.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN role='customer' THEN 1 ELSE 0 END) AS customers,
            SUM(CASE WHEN role='technician' THEN 1 ELSE 0 END) AS technicians,
            SUM(CASE WHEN role='seller' THEN 1 ELSE 0 END) AS sellers,
            SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) AS pending,
            SUM(CASE WHEN status='blocked' THEN 1 ELSE 0 END) AS blocked,
            SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) AS approved
        FROM users
    """).fetchone()

    conn.close()

    return jsonify(dict(rows))
