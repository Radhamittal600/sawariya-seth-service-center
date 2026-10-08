from flask import Blueprint, jsonify
from app.auth import role_required
from app.database.db import get_db

payments_bp = Blueprint("payments", __name__, url_prefix="/owner/payments")


@payments_bp.get("")
@role_required("owner")
def all_payments():

    conn = get_db()

    payments = conn.execute(
        """
        SELECT
            p.id,
            p.booking_id,
            p.customer_id,
            p.technician_id,
            p.amount,
            p.commission,
            p.technician_amount,
            p.payment_method,
            p.transaction_id,
            p.status,
            p.refund_status,
            p.created_at,
            c.name AS customer_name,
            t.name AS technician_name
        FROM payments p
        LEFT JOIN users c ON c.id = p.customer_id
        LEFT JOIN users t ON t.id = p.technician_id
        ORDER BY p.id DESC
        """
    ).fetchall()

    conn.close()

    return jsonify({
        "payments": [dict(p) for p in payments]
    })


@payments_bp.get("/summary")
@role_required("owner")
def payment_summary():

    conn = get_db()

    total = conn.execute(
        """
        SELECT COALESCE(SUM(amount),0) AS value
        FROM payments
        WHERE status='success'
        """
    ).fetchone()["value"]

    commission = conn.execute(
        """
        SELECT COALESCE(SUM(commission),0) AS value
        FROM payments
        WHERE status='success'
        """
    ).fetchone()["value"]

    refunds = conn.execute(
        """
        SELECT COALESCE(SUM(amount),0) AS value
        FROM refunds
        WHERE status='approved'
        """
    ).fetchone()["value"]

    pending = conn.execute(
        """
        SELECT COALESCE(SUM(amount),0) AS value
        FROM payments
        WHERE status='pending'
        """
    ).fetchone()["value"]

    successful_count = conn.execute(
        """
        SELECT COUNT(*) AS value
        FROM payments
        WHERE status='success'
        """
    ).fetchone()["value"]

    conn.close()

    return jsonify({
        "total_revenue": total,
        "commission": commission,
        "refunds": refunds,
        "pending": pending,
        "successful_payments": successful_count
    })
