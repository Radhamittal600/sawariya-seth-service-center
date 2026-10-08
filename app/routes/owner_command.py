from flask import Blueprint, jsonify
from app.auth import role_required
from app.database.db import get_db

owner_command_bp = Blueprint(
    "owner_command",
    __name__,
    url_prefix="/owner/command"
)


@owner_command_bp.get("/overview")
@role_required("owner")
def overview():
    conn = get_db()

    users = conn.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN role='customer' THEN 1 ELSE 0 END) AS customers,
            SUM(CASE WHEN role='technician' THEN 1 ELSE 0 END) AS technicians,
            SUM(CASE WHEN role='seller' THEN 1 ELSE 0 END) AS sellers,
            SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) AS pending
        FROM users
    """).fetchone()

    bookings = conn.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) AS pending,
            SUM(CASE WHEN status='accepted' THEN 1 ELSE 0 END) AS accepted,
            SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) AS completed,
            SUM(CASE WHEN status IN ('accepted','started') THEN 1 ELSE 0 END) AS active
        FROM bookings
    """).fetchone()

    payments = conn.execute("""
        SELECT
            COALESCE(SUM(
                CASE WHEN status='success'
                THEN amount ELSE 0 END
            ), 0) AS revenue,

            COALESCE(SUM(
                CASE WHEN status='success'
                THEN commission ELSE 0 END
            ), 0) AS commission,

            COUNT(
                CASE WHEN status='success'
                THEN 1 END
            ) AS successful
        FROM payments
    """).fetchone()

    complaints = conn.execute("""
        SELECT COUNT(*) AS total
        FROM complaints
        WHERE status NOT IN ('resolved','closed')
    """).fetchone()

    reviews = conn.execute("""
        SELECT
            COUNT(*) AS total,
            COALESCE(AVG(rating),0) AS average
        FROM reviews
        WHERE status='approved'
    """).fetchone()

    products = conn.execute("""
        SELECT COUNT(*) AS total
        FROM seller_products
    """).fetchone()

    orders = conn.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(
                CASE WHEN order_status='pending'
                THEN 1 ELSE 0 END
            ) AS pending
        FROM orders
    """).fetchone()

    conn.close()

    return jsonify({
        "users": dict(users),
        "bookings": dict(bookings),
        "payments": dict(payments),
        "complaints": dict(complaints),
        "reviews": dict(reviews),
        "products": dict(products),
        "orders": dict(orders)
    })


@owner_command_bp.get("/health")
@role_required("owner")
def command_health():
    conn = get_db()

    checks = {}

    try:
        conn.execute("SELECT 1").fetchone()
        checks["database"] = "online"
    except Exception:
        checks["database"] = "offline"

    try:
        conn.execute("SELECT COUNT(*) FROM users").fetchone()
        checks["users"] = "online"
    except Exception:
        checks["users"] = "offline"

    try:
        conn.execute("SELECT COUNT(*) FROM bookings").fetchone()
        checks["bookings"] = "online"
    except Exception:
        checks["bookings"] = "offline"

    try:
        conn.execute("SELECT COUNT(*) FROM payments").fetchone()
        checks["payments"] = "online"
    except Exception:
        checks["payments"] = "offline"

    conn.close()

    return jsonify(checks)
