from flask import Blueprint, jsonify, request
from app.auth import role_required
from app.database.db import get_db

owner_master_bp = Blueprint(
    "owner_master",
    __name__,
    url_prefix="/owner/master"
)


def rows_to_dict(rows):
    return [dict(row) for row in rows]


@owner_master_bp.get("/users")
@role_required("owner")
def users():
    conn = get_db()
    rows = conn.execute("""
        SELECT id,name,phone,role,status,city,
               business_name,skill,experience,created_at
        FROM users
        ORDER BY id DESC
        LIMIT 500
    """).fetchall()
    conn.close()
    return jsonify(rows_to_dict(rows))


@owner_master_bp.get("/technicians")
@role_required("owner")
def technicians():
    conn = get_db()
    rows = conn.execute("""
        SELECT
            u.id,
            u.name,
            u.phone,
            u.status,
            u.skill,
            u.experience,
            COUNT(b.id) AS total_jobs,
            SUM(
                CASE WHEN b.status='completed'
                THEN 1 ELSE 0 END
            ) AS completed_jobs
        FROM users u
        LEFT JOIN bookings b
            ON b.technician_id=u.id
        WHERE u.role='technician'
        GROUP BY u.id
        ORDER BY u.id DESC
    """).fetchall()
    conn.close()
    return jsonify(rows_to_dict(rows))


@owner_master_bp.get("/sellers")
@role_required("owner")
def sellers():
    conn = get_db()
    rows = conn.execute("""
        SELECT
            u.id,
            u.name,
            u.phone,
            u.status,
            u.business_name,
            u.gstin,
            u.pan,
            COUNT(sp.id) AS products
        FROM users u
        LEFT JOIN seller_products sp
            ON sp.seller_id=u.id
        WHERE u.role='seller'
        GROUP BY u.id
        ORDER BY u.id DESC
    """).fetchall()
    conn.close()
    return jsonify(rows_to_dict(rows))


@owner_master_bp.get("/bookings")
@role_required("owner")
def bookings():
    conn = get_db()
    rows = conn.execute("""
        SELECT
            b.id,
            b.status,
            b.address,
            b.created_at,
            c.name AS customer_name,
            c.phone AS customer_phone,
            t.name AS technician_name,
            s.name AS service_name,
            b.technician_lat,
            b.technician_lng
        FROM bookings b
        JOIN users c ON c.id=b.customer_id
        LEFT JOIN users t ON t.id=b.technician_id
        JOIN services s ON s.id=b.service_id
        ORDER BY b.id DESC
        LIMIT 500
    """).fetchall()
    conn.close()
    return jsonify(rows_to_dict(rows))


@owner_master_bp.get("/payments")
@role_required("owner")
def payments():
    conn = get_db()
    rows = conn.execute("""
        SELECT
            p.*,
            c.name AS customer_name,
            t.name AS technician_name
        FROM payments p
        LEFT JOIN users c ON c.id=p.customer_id
        LEFT JOIN users t ON t.id=p.technician_id
        ORDER BY p.id DESC
        LIMIT 500
    """).fetchall()
    conn.close()
    return jsonify(rows_to_dict(rows))


@owner_master_bp.get("/orders")
@role_required("owner")
def orders():
    conn = get_db()
    rows = conn.execute("""
        SELECT
            o.*,
            c.name AS customer_name,
            s.name AS seller_name
        FROM orders o
        LEFT JOIN users c ON c.id=o.customer_id
        LEFT JOIN users s ON s.id=o.seller_id
        ORDER BY o.id DESC
        LIMIT 500
    """).fetchall()
    conn.close()
    return jsonify(rows_to_dict(rows))


@owner_master_bp.get("/products")
@role_required("owner")
def products():
    conn = get_db()
    rows = conn.execute("""
        SELECT
            sp.*,
            u.name AS seller_name
        FROM seller_products sp
        LEFT JOIN users u ON u.id=sp.seller_id
        ORDER BY sp.id DESC
        LIMIT 500
    """).fetchall()
    conn.close()
    return jsonify(rows_to_dict(rows))


@owner_master_bp.get("/kyc")
@role_required("owner")
def kyc():
    conn = get_db()
    rows = conn.execute("""
        SELECT
            k.*,
            u.name,
            u.phone,
            u.role
        FROM kyc_documents k
        JOIN users u ON u.id=k.user_id
        ORDER BY k.id DESC
        LIMIT 500
    """).fetchall()
    conn.close()
    return jsonify(rows_to_dict(rows))


@owner_master_bp.get("/complaints")
@role_required("owner")
def complaints():
    conn = get_db()
    rows = conn.execute("""
        SELECT
            c.*,
            u.name AS user_name,
            u.phone
        FROM complaints c
        LEFT JOIN users u ON u.id=c.user_id
        ORDER BY c.id DESC
        LIMIT 500
    """).fetchall()
    conn.close()
    return jsonify(rows_to_dict(rows))


@owner_master_bp.get("/reviews")
@role_required("owner")
def reviews():
    conn = get_db()
    rows = conn.execute("""
        SELECT
            r.*,
            c.name AS customer_name,
            t.name AS technician_name
        FROM reviews r
        LEFT JOIN users c ON c.id=r.customer_id
        LEFT JOIN users t ON t.id=r.technician_id
        ORDER BY r.id DESC
        LIMIT 500
    """).fetchall()
    conn.close()
    return jsonify(rows_to_dict(rows))


@owner_master_bp.get("/support")
@role_required("owner")
def support():
    conn = get_db()
    rows = conn.execute("""
        SELECT
            st.*,
            u.name AS user_name,
            u.phone
        FROM support_tickets st
        LEFT JOIN users u ON u.id=st.user_id
        ORDER BY st.id DESC
        LIMIT 500
    """).fetchall()
    conn.close()
    return jsonify(rows_to_dict(rows))


@owner_master_bp.get("/notifications")
@role_required("owner")
def notifications():
    conn = get_db()
    rows = conn.execute("""
        SELECT
            n.*,
            u.name AS user_name,
            u.role AS user_role
        FROM notifications n
        LEFT JOIN users u ON u.id=n.user_id
        ORDER BY n.id DESC
        LIMIT 500
    """).fetchall()
    conn.close()
    return jsonify(rows_to_dict(rows))


@owner_master_bp.get("/security")
@role_required("owner")
def security():
    conn = get_db()
    rows = conn.execute("""
        SELECT *
        FROM security_events
        ORDER BY id DESC
        LIMIT 500
    """).fetchall()
    conn.close()
    return jsonify(rows_to_dict(rows))


@owner_master_bp.get("/audit")
@role_required("owner")
def audit():
    conn = get_db()
    rows = conn.execute("""
        SELECT
            a.*,
            u.name AS user_name
        FROM audit_logs a
        LEFT JOIN users u ON u.id=a.user_id
        ORDER BY a.id DESC
        LIMIT 500
    """).fetchall()
    conn.close()
    return jsonify(rows_to_dict(rows))


@owner_master_bp.get("/summary")
@role_required("owner")
def summary():
    conn = get_db()

    users = conn.execute(
        "SELECT COUNT(*) AS n FROM users"
    ).fetchone()["n"]

    technicians = conn.execute(
        "SELECT COUNT(*) AS n FROM users WHERE role='technician'"
    ).fetchone()["n"]

    sellers = conn.execute(
        "SELECT COUNT(*) AS n FROM users WHERE role='seller'"
    ).fetchone()["n"]

    customers = conn.execute(
        "SELECT COUNT(*) AS n FROM users WHERE role='customer'"
    ).fetchone()["n"]

    bookings = conn.execute(
        "SELECT COUNT(*) AS n FROM bookings"
    ).fetchone()["n"]

    products = conn.execute(
        "SELECT COUNT(*) AS n FROM seller_products"
    ).fetchone()["n"]

    orders = conn.execute(
        "SELECT COUNT(*) AS n FROM orders"
    ).fetchone()["n"]

    complaints = conn.execute(
        "SELECT COUNT(*) AS n FROM complaints WHERE status NOT IN ('resolved','closed')"
    ).fetchone()["n"]

    pending_users = conn.execute(
        "SELECT COUNT(*) AS n FROM users WHERE status='pending'"
    ).fetchone()["n"]

    conn.close()

    return jsonify({
        "users": users,
        "customers": customers,
        "technicians": technicians,
        "sellers": sellers,
        "bookings": bookings,
        "products": products,
        "orders": orders,
        "open_complaints": complaints,
        "pending_users": pending_users
    })


@owner_master_bp.get("/dashboard")
@role_required("owner")
def dashboard():
    conn = get_db()

    def count(table, where=""):
        query = f"SELECT COUNT(*) AS n FROM {table}"
        if where:
            query += " WHERE " + where
        return conn.execute(query).fetchone()["n"]

    result = {
        "users": count("users"),
        "customers": count("users", "role='customer'"),
        "technicians": count("users", "role='technician'"),
        "sellers": count("users", "role='seller'"),
        "pending_users": count("users", "status='pending'"),

        "bookings": count("bookings"),
        "pending_bookings": count("bookings", "status='pending'"),
        "active_bookings": count(
            "bookings",
            "status IN ('accepted','started')"
        ),
        "completed_bookings": count(
            "bookings",
            "status='completed'"
        ),

        "products": count("seller_products"),
        "orders": count("orders"),
        "pending_orders": count(
            "orders",
            "order_status='pending'"
        ),

        "kyc": count("kyc_documents"),
        "pending_kyc": count(
            "kyc_documents",
            "status='pending'"
        ),

        "complaints": count("complaints"),
        "open_complaints": count(
            "complaints",
            "status NOT IN ('resolved','closed')"
        ),

        "reviews": count("reviews"),
        "support_tickets": count("support_tickets"),
        "notifications": count("notifications"),
        "security_events": count("security_events"),
        "audit_logs": count("audit_logs")
    }

    try:
        payment = conn.execute("""
            SELECT
                COALESCE(SUM(
                    CASE
                        WHEN status='success'
                        THEN amount ELSE 0
                    END
                ),0) AS revenue,

                COALESCE(SUM(
                    CASE
                        WHEN status='success'
                        THEN commission ELSE 0
                    END
                ),0) AS commission
            FROM payments
        """).fetchone()

        result["revenue"] = payment["revenue"]
        result["commission"] = payment["commission"]

    except Exception:
        result["revenue"] = 0
        result["commission"] = 0

    conn.close()

    return jsonify(result)
