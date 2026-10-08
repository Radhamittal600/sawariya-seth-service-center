from flask import Blueprint, jsonify
from app.auth import role_required
from app.database.db import get_db

owner_marketplace_bp = Blueprint(
    "owner_marketplace",
    __name__,
    url_prefix="/owner/marketplace"
)


@owner_marketplace_bp.get("/products")
@role_required("owner")
def products():

    conn = get_db()

    rows = conn.execute("""
        SELECT
            p.id,
            p.name,
            p.description,
            p.category,
            p.price,
            p.stock,
            p.approval_status,
            p.active,
            u.name AS seller_name,
            u.phone AS seller_phone
        FROM seller_products p
        JOIN users u ON u.id=p.seller_id
        ORDER BY p.id DESC
    """).fetchall()

    conn.close()

    return jsonify({
        "products": [dict(x) for x in rows]
    })


@owner_marketplace_bp.get("/orders")
@role_required("owner")
def orders():

    conn = get_db()

    rows = conn.execute("""
        SELECT
            o.id,
            o.customer_id,
            o.seller_id,
            o.total_amount,
            o.payment_status,
            o.order_status,
            o.delivery_address,
            o.created_at,
            c.name AS customer_name,
            s.name AS seller_name
        FROM orders o
        LEFT JOIN users c ON c.id=o.customer_id
        LEFT JOIN users s ON s.id=o.seller_id
        ORDER BY o.id DESC
    """).fetchall()

    conn.close()

    return jsonify({
        "orders": [dict(x) for x in rows]
    })


@owner_marketplace_bp.get("/summary")
@role_required("owner")
def marketplace_summary():

    conn = get_db()

    products = conn.execute(
        "SELECT COUNT(*) AS total FROM seller_products"
    ).fetchone()["total"]

    pending_products = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM seller_products
        WHERE approval_status='pending'
        """
    ).fetchone()["total"]

    orders = conn.execute(
        "SELECT COUNT(*) AS total FROM orders"
    ).fetchone()["total"]

    sales = conn.execute(
        """
        SELECT COALESCE(SUM(total_amount),0) AS total
        FROM orders
        WHERE payment_status='paid'
        """
    ).fetchone()["total"]

    conn.close()

    return jsonify({
        "products": products,
        "pending_products": pending_products,
        "orders": orders,
        "sales": sales
    })
