from app.auth import hash_password
from flask import current_app, Blueprint, request, jsonify, session
import sqlite3
from pathlib import Path
from datetime import datetime

owner_super_bp = Blueprint("owner_super", __name__, url_prefix="/owner/super")

DB_PATH = Path(__file__).resolve().parents[2] / "sawariya.db"


# =========================================================
# DATABASE
# =========================================================

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def json_rows(rows):
    return [dict(x) for x in rows]


def table_exists(conn, table):
    row = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name=?",
        (table,)
    ).fetchone()
    return bool(row)


# =========================================================
# OWNER ONLY
# =========================================================

def owner_only():
    if session.get("user_id") is None:
        return False

    return session.get("role") == "owner"


def owner_denied():
    return jsonify({
        "ok": False,
        "error": "Owner access required"
    }), 403


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# =========================================================
# SAFE NOTIFICATION
# =========================================================

def notify(conn, user_id, title, message, notification_type="owner"):
    try:
        if not table_exists(conn, "notifications"):
            return

        conn.execute("""
            INSERT INTO notifications
            (user_id,title,message,notification_type,created_at)
            VALUES (?,?,?,?,?)
        """, (
            user_id,
            title,
            message,
            notification_type,
            now()
        ))
    except Exception:
        pass


# =========================================================
# SAFE AUDIT
# =========================================================

def audit(conn, action, target_type="", target_id=None, details=""):
    try:
        if not table_exists(conn, "audit_logs"):
            return

        cols = [
            x["name"]
            for x in conn.execute(
                "PRAGMA table_info(audit_logs)"
            ).fetchall()
        ]

        data = {}

        if "action" in cols:
            data["action"] = action

        if "actor_id" in cols:
            data["actor_id"] = session.get("user_id")

        if "user_id" in cols:
            data["user_id"] = session.get("user_id")

        if "target_type" in cols:
            data["target_type"] = target_type

        if "target_id" in cols:
            data["target_id"] = target_id

        if "details" in cols:
            data["details"] = details

        if "created_at" in cols:
            data["created_at"] = now()

        if data:
            keys = list(data.keys())
            values = [data[k] for k in keys]

            conn.execute(
                "INSERT INTO audit_logs "
                f"({','.join(keys)}) "
                f"VALUES ({','.join(['?'] * len(values))})",
                values
            )

    except Exception:
        pass


# =========================================================
# HEALTH
# =========================================================

@owner_super_bp.get("/health")
def health():
    if not owner_only():
        return owner_denied()

    return jsonify({
        "ok": True,
        "service": "Sawariya Owner A-Z Master Control",
        "owner": True,
        "time": now()
    })


# =========================================================
# DASHBOARD
# =========================================================

@owner_super_bp.get("/api/summary")
def summary():
    if not owner_only():
        return owner_denied()

    conn = db()

    def count(query, args=()):
        try:
            return conn.execute(query, args).fetchone()[0]
        except Exception:
            return 0

    result = {
        "users": count("SELECT COUNT(*) FROM users"),
        "customers": count(
            "SELECT COUNT(*) FROM users WHERE role='customer'"
        ),
        "technicians": count(
            "SELECT COUNT(*) FROM users WHERE role='technician'"
        ),
        "sellers": count(
            "SELECT COUNT(*) FROM users WHERE role='seller'"
        ),
        "owners": count(
            "SELECT COUNT(*) FROM users WHERE role='owner'"
        ),
        "pending_users": count(
            "SELECT COUNT(*) FROM users WHERE status='pending'"
        ),
        "blocked_users": count(
            "SELECT COUNT(*) FROM users WHERE status='blocked'"
        ),
        "bookings": count("SELECT COUNT(*) FROM bookings"),
        "products": count("SELECT COUNT(*) FROM seller_products"),
        "orders": count("SELECT COUNT(*) FROM orders"),
        "payments": count("SELECT COUNT(*) FROM payments"),
        "complaints": count("SELECT COUNT(*) FROM complaints"),
        "reviews": count("SELECT COUNT(*) FROM reviews"),
        "kyc": count("SELECT COUNT(*) FROM kyc_documents"),
        "support": count("SELECT COUNT(*) FROM support_tickets"),
        "notifications": count("SELECT COUNT(*) FROM notifications"),
        "security_events": count("SELECT COUNT(*) FROM security_events"),
        "audit_logs": count("SELECT COUNT(*) FROM audit_logs"),
        "refunds": count("SELECT COUNT(*) FROM refunds")
    }

    conn.close()

    return jsonify(result)


# =========================================================
# USERS
# =========================================================

@owner_super_bp.get("/api/users")
def users():
    if not owner_only():
        return owner_denied()

    conn = db()
    try:
        available = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(users)").fetchall()
        }

        wanted = [
            "id", "name", "phone", "role", "status",
            "address", "city", "pincode", "skill", "experience",
            "business_name", "gstin", "pan", "product_category",
            "profile_photo", "created_at"
        ]

        required = {"id", "name", "phone", "role", "status"}
        missing_required = required - available
        if missing_required:
            return jsonify({
                "ok": False,
                "error": "Required users columns are missing",
                "missing_columns": sorted(missing_required)
            }), 500

        columns = [
            f'"{col}"' if col in available else f'NULL AS "{col}"'
            for col in wanted
        ]

        rows = conn.execute(
            "SELECT " + ", ".join(columns) +
            " FROM users ORDER BY id DESC LIMIT 500"
        ).fetchall()

        return jsonify({
            "ok": True,
            "users": json_rows(rows)
        })
    except Exception:
        current_app.logger.exception("Super Owner users API failed")
        return jsonify({
            "ok": False,
            "error": "Unable to load users. Check server logs."
        }), 500
    finally:
        conn.close()


@owner_super_bp.post("/user/<int:user_id>/<action>")
def user_action(user_id, action):
    if not owner_only():
        return owner_denied()

    allowed = {
        "approve": "approved",
        "block": "blocked",
        "unblock": "approved",
        "pending": "pending",
        "reject": "rejected"
    }

    if action not in allowed:
        return jsonify({
            "ok": False,
            "error": "Invalid user action"
        }), 400

    if user_id == session.get("user_id") and action == "block":
        return jsonify({
            "ok": False,
            "error": "Owner cannot block own account"
        }), 400

    conn = db()

    user = conn.execute(
        "SELECT id,name,role,status "
        "FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    if not user:
        conn.close()
        return jsonify({
            "ok": False,
            "error": "User not found"
        }), 404

    status = allowed[action]

    conn.execute(
        "UPDATE users SET status=? WHERE id=?",
        (status, user_id)
    )

    notify(
        conn,
        user_id,
        "OWNER ACCOUNT UPDATE",
        f"Your account status is now: {status}",
        "account_status"
    )

    audit(
        conn,
        f"user_{action}",
        "user",
        user_id,
        f"status={status}"
    )

    conn.commit()
    conn.close()

    return jsonify({
        "ok": True,
        "message": "User updated",
        "user_id": user_id,
        "status": status
    })


# =========================================================
# CHANGE ROLE
# =========================================================

@owner_super_bp.post("/user/<int:user_id>/role")
def change_role(user_id):
    if not owner_only():
        return owner_denied()

    data = request.get_json(silent=True) or {}
    role = str(data.get("role", "")).strip().lower()

    allowed = {
        "customer",
        "technician",
        "seller",
        "owner"
    }

    if role not in allowed:
        return jsonify({
            "ok": False,
            "error": "Invalid role"
        }), 400

    if user_id == session.get("user_id") and role != "owner":
        return jsonify({
            "ok": False,
            "error": "Owner cannot remove own owner role"
        }), 400

    conn = db()

    user = conn.execute(
        "SELECT id,name FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    if not user:
        conn.close()
        return jsonify({
            "ok": False,
            "error": "User not found"
        }), 404

    conn.execute(
        "UPDATE users SET role=? WHERE id=?",
        (role, user_id)
    )

    audit(
        conn,
        "change_user_role",
        "user",
        user_id,
        f"role={role}"
    )

    conn.commit()
    conn.close()

    return jsonify({
        "ok": True,
        "message": "Role updated",
        "role": role
    })


# =========================================================
# TECHNICIANS
# =========================================================



# =========================================================
# SUPER OWNER — CREATE ACCOUNT
# =========================================================

@owner_super_bp.post("/api/users/create")
def create_account():
    if not owner_only():
        return owner_denied()

    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    phone = str(data.get("phone", "")).strip()
    password = str(data.get("password", ""))
    role = str(data.get("role", "")).strip().lower()

    if not name or not phone or not password:
        return jsonify({"ok": False, "error": "Name, phone and password are required"}), 400
    if role not in {"owner", "customer", "technician", "seller"}:
        return jsonify({"ok": False, "error": "Invalid role"}), 400
    if not phone.isdigit() or len(phone) != 10:
        return jsonify({"ok": False, "error": "Phone must be 10 digits"}), 400
    if len(password) < 8:
        return jsonify({"ok": False, "error": "Password must be at least 8 characters"}), 400

    conn = db()
    try:
        cols = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(users)").fetchall()
        }
        required = {"id", "name", "phone", "password_hash", "role", "status"}
        if not required.issubset(cols):
            return jsonify({
                "ok": False,
                "error": "Database users table is missing required columns"
            }), 500

        if conn.execute("SELECT 1 FROM users WHERE phone=?", (phone,)).fetchone():
            return jsonify({"ok": False, "error": "Phone number already registered"}), 409

        values = {
            "name": name,
            "phone": phone,
            "password_hash": hash_password(password),
            "role": role,
            "status": "approved" if role in {"owner", "customer"} else "pending",
            "address": str(data.get("address", "")).strip(),
            "city": str(data.get("city", "")).strip(),
            "pincode": str(data.get("pincode", "")).strip(),
            "skill": str(data.get("skill", "")).strip(),
            "experience": str(data.get("experience", "")).strip(),
            "business_name": str(data.get("business_name", "")).strip(),
            "gstin": str(data.get("gstin", "")).strip().upper(),
            "pan": str(data.get("pan", "")).strip().upper(),
            "product_category": str(data.get("product_category", "")).strip()
        }

        # Insert only columns that actually exist in this database.
        insert_values = {k: v for k, v in values.items() if k in cols}
        names = list(insert_values)
        sql = (
            "INSERT INTO users (" + ", ".join('"' + n + '"' for n in names) +
            ") VALUES (" + ", ".join("?" for _ in names) + ")"
        )
        cur = conn.execute(sql, [insert_values[n] for n in names])
        conn.commit()

        return jsonify({
            "ok": True,
            "message": "Account created",
            "user_id": cur.lastrowid,
            "role": role,
            "status": values["status"]
        }), 201
    except Exception:
        conn.rollback()
        current_app.logger.exception("Super Owner create-account API failed")
        return jsonify({"ok": False, "error": "Account creation failed; check server logs"}), 500
    finally:
        conn.close()


@owner_super_bp.get("/api/technicians")
def technicians():
    if not owner_only():
        return owner_denied()

    conn = db()
    try:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)")}
        if not {"id", "name", "phone", "role", "status"}.issubset(cols):
            return jsonify({"ok": False, "error": "Required user columns missing"}), 500

        skill = 'u.skill' if "skill" in cols else "'' AS skill"
        experience = 'u.experience' if "experience" in cols else "'' AS experience"

        has_bookings = table_exists(conn, "bookings")
        booking_cols = (
            {r["name"] for r in conn.execute("PRAGMA table_info(bookings)")}
            if has_bookings else set()
        )

        if {"id", "technician_id", "status"}.issubset(booking_cols):
            job_fields = """
                COUNT(b.id) AS total_jobs,
                COALESCE(SUM(CASE WHEN b.status='completed' THEN 1 ELSE 0 END),0)
                AS completed_jobs
            """
            join = "LEFT JOIN bookings b ON b.technician_id=u.id"
        else:
            job_fields = "0 AS total_jobs, 0 AS completed_jobs"
            join = ""

        rows = conn.execute(f"""
            SELECT u.id,u.name,u.phone,u.status,
                   {skill},{experience},{job_fields}
            FROM users u {join}
            WHERE u.role='technician'
            GROUP BY u.id
            ORDER BY u.id DESC
        """).fetchall()
        return jsonify({"ok": True, "technicians": json_rows(rows)})
    except Exception:
        current_app.logger.exception("Owner technicians API failed")
        return jsonify({"ok": False, "error": "Technicians temporarily unavailable"}), 500
    finally:
        conn.close()

# =========================================================
# SELLERS
# =========================================================

@owner_super_bp.get("/api/sellers")
def sellers():
    if not owner_only():
        return owner_denied()

    conn = db()
    try:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)")}
        if not {"id", "name", "phone", "role", "status"}.issubset(cols):
            return jsonify({"ok": False, "error": "Required user columns missing"}), 500

        business = 'u.business_name' if "business_name" in cols else "'' AS business_name"
        gstin = 'u.gstin' if "gstin" in cols else "'' AS gstin"

        product_table = None
        for candidate in ("seller_products", "products"):
            if table_exists(conn, candidate):
                tcols = {
                    r["name"] for r in
                    conn.execute(f'PRAGMA table_info("{candidate}")')
                }
                if {"id", "seller_id"}.issubset(tcols):
                    product_table = candidate
                    break

        if product_table:
            join = f'LEFT JOIN "{product_table}" sp ON sp.seller_id=u.id'
            count_sql = "COUNT(DISTINCT sp.id)"
        else:
            join = ""
            count_sql = "0"

        rows = conn.execute(f"""
            SELECT u.id,u.name,u.phone,u.status,
                   {business},{gstin},{count_sql} AS products
            FROM users u {join}
            WHERE u.role='seller'
            GROUP BY u.id
            ORDER BY u.id DESC
        """).fetchall()
        return jsonify({"ok": True, "sellers": json_rows(rows)})
    except Exception:
        current_app.logger.exception("Owner sellers API failed")
        return jsonify({"ok": False, "error": "Sellers temporarily unavailable"}), 500
    finally:
        conn.close()

# =========================================================
# PRODUCTS
# =========================================================

@owner_super_bp.get("/api/products")
def products():
    if not owner_only():
        return owner_denied()

    conn = db()

    rows = conn.execute("""
        SELECT
            sp.id,
            sp.seller_id,
            u.name AS seller_name,
            sp.name,
            sp.description,
            sp.category,
            sp.price,
            sp.stock,
            sp.approval_status,
            sp.active,
            sp.photo_url,
            sp.created_at
        FROM seller_products sp
        LEFT JOIN users u
            ON u.id=sp.seller_id
        ORDER BY sp.id DESC
        LIMIT 500
    """).fetchall()

    conn.close()

    return jsonify({
        "ok": True,
        "products": json_rows(rows)
    })


@owner_super_bp.post("/product/<int:product_id>/<action>")
def product_action(product_id, action):
    if not owner_only():
        return owner_denied()

    if action not in ("approve", "reject"):
        return jsonify({
            "ok": False,
            "error": "Invalid product action"
        }), 400

    conn = db()

    product = conn.execute("""
        SELECT
            sp.id,
            sp.name,
            sp.seller_id,
            sp.price,
            sp.stock
        FROM seller_products sp
        WHERE sp.id=?
    """, (product_id,)).fetchone()

    if not product:
        conn.close()
        return jsonify({
            "ok": False,
            "error": "Product not found"
        }), 404

    status = "approved" if action == "approve" else "rejected"
    active = 1 if action == "approve" else 0

    conn.execute("""
        UPDATE seller_products
        SET approval_status=?, active=?
        WHERE id=?
    """, (
        status,
        active,
        product_id
    ))

    notify(
        conn,
        product["seller_id"],
        "PRODUCT REVIEW",
        f"Product '{product['name']}' was {status} by Owner.",
        "product_decision"
    )

    audit(
        conn,
        f"product_{action}",
        "seller_product",
        product_id,
        f"seller_id={product['seller_id']}"
    )

    conn.commit()
    conn.close()

    return jsonify({
        "ok": True,
        "message": f"Product {status}",
        "product_id": product_id,
        "approval_status": status,
        "active": active
    })


# =========================================================
# PRODUCT EDIT
# =========================================================

@owner_super_bp.post("/product/<int:product_id>/edit")
def product_edit(product_id):
    if not owner_only():
        return owner_denied()

    data = request.get_json(silent=True) or {}

    allowed = [
        "name",
        "description",
        "category",
        "price",
        "stock",
        "active"
    ]

    fields = []
    values = []

    for key in allowed:
        if key in data:
            fields.append(f"{key}=?")
            values.append(data[key])

    if not fields:
        return jsonify({
            "ok": False,
            "error": "No changes supplied"
        }), 400

    values.append(product_id)

    conn = db()

    cur = conn.execute(
        "UPDATE seller_products SET "
        + ",".join(fields)
        + " WHERE id=?",
        values
    )

    if cur.rowcount == 0:
        conn.close()
        return jsonify({
            "ok": False,
            "error": "Product not found"
        }), 404

    audit(
        conn,
        "edit_product",
        "seller_product",
        product_id,
        str(data)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "ok": True,
        "message": "Product updated"
    })


# =========================================================
# BOOKINGS
# =========================================================

@owner_super_bp.get("/api/bookings")
def bookings():
    if not owner_only():
        return owner_denied()

    conn = db()

    rows = conn.execute("""
        SELECT
            b.id,
            b.service_id,
            s.name AS service_name,
            b.customer_id,
            c.name AS customer_name,
            b.technician_id,
            t.name AS technician_name,
            b.status,
            b.address,
            b.technician_lat,
            b.technician_lng,
            b.location_updated_at,
            b.created_at
        FROM bookings b
        LEFT JOIN services s
            ON s.id=b.service_id
        LEFT JOIN users c
            ON c.id=b.customer_id
        LEFT JOIN users t
            ON t.id=b.technician_id
        ORDER BY b.id DESC
        LIMIT 500
    """).fetchall()

    conn.close()

    return jsonify({
        "ok": True,
        "bookings": json_rows(rows)
    })


@owner_super_bp.post("/booking/<int:booking_id>/status")
def booking_status(booking_id):
    if not owner_only():
        return owner_denied()

    data = request.get_json(silent=True) or {}
    status = str(data.get("status", "")).strip()

    allowed = {
        "pending",
        "accepted",
        "in_progress",
        "completed",
        "cancelled",
        "rejected"
    }

    if status not in allowed:
        return jsonify({
            "ok": False,
            "error": "Invalid booking status"
        }), 400

    conn = db()

    booking = conn.execute(
        "SELECT id,customer_id,technician_id "
        "FROM bookings WHERE id=?",
        (booking_id,)
    ).fetchone()

    if not booking:
        conn.close()
        return jsonify({
            "ok": False,
            "error": "Booking not found"
        }), 404

    conn.execute(
        "UPDATE bookings SET status=? WHERE id=?",
        (status, booking_id)
    )

    notify(
        conn,
        booking["customer_id"],
        "BOOKING UPDATE",
        f"Booking #{booking_id} status: {status}",
        "booking_status"
    )

    if booking["technician_id"]:
        notify(
            conn,
            booking["technician_id"],
            "BOOKING UPDATE",
            f"Booking #{booking_id} status: {status}",
            "booking_status"
        )

    audit(
        conn,
        "booking_status",
        "booking",
        booking_id,
        status
    )

    conn.commit()
    conn.close()

    return jsonify({
        "ok": True,
        "booking_id": booking_id,
        "status": status
    })


# =========================================================
# ASSIGN TECHNICIAN
# =========================================================

@owner_super_bp.post("/booking/<int:booking_id>/assign")
def booking_assign(booking_id):
    if not owner_only():
        return owner_denied()

    data = request.get_json(silent=True) or {}

    try:
        technician_id = int(data.get("technician_id"))
    except Exception:
        return jsonify({
            "ok": False,
            "error": "Technician ID required"
        }), 400

    conn = db()

    technician = conn.execute(
        "SELECT id,name FROM users "
        "WHERE id=? AND role='technician' "
        "AND status='approved'",
        (technician_id,)
    ).fetchone()

    if not technician:
        conn.close()
        return jsonify({
            "ok": False,
            "error": "Approved technician not found"
        }), 404

    booking = conn.execute(
        "SELECT id,customer_id FROM bookings WHERE id=?",
        (booking_id,)
    ).fetchone()

    if not booking:
        conn.close()
        return jsonify({
            "ok": False,
            "error": "Booking not found"
        }), 404

    conn.execute("""
        UPDATE bookings
        SET technician_id=?, status='accepted'
        WHERE id=?
    """, (
        technician_id,
        booking_id
    ))

    notify(
        conn,
        technician_id,
        "NEW JOB ASSIGNED",
        f"Booking #{booking_id} assigned to you.",
        "job_assignment"
    )

    notify(
        conn,
        booking["customer_id"],
        "TECHNICIAN ASSIGNED",
        f"Technician {technician['name']} assigned to booking #{booking_id}.",
        "technician_assigned"
    )

    audit(
        conn,
        "assign_technician",
        "booking",
        booking_id,
        f"technician_id={technician_id}"
    )

    conn.commit()
    conn.close()

    return jsonify({
        "ok": True,
        "booking_id": booking_id,
        "technician_id": technician_id
    })


# =========================================================
# ORDERS
# =========================================================

@owner_super_bp.get("/api/orders")
def orders():
    if not owner_only():
        return owner_denied()

    conn = db()

    if not table_exists(conn, "orders"):
        conn.close()
        return jsonify({
            "ok": True,
            "orders": []
        })

    rows = conn.execute(
        "SELECT * FROM orders "
        "ORDER BY id DESC LIMIT 500"
    ).fetchall()

    conn.close()

    return jsonify({
        "ok": True,
        "orders": json_rows(rows)
    })


@owner_super_bp.post("/order/<int:order_id>/status")
def order_status(order_id):
    if not owner_only():
        return owner_denied()

    data = request.get_json(silent=True) or {}
    status = str(data.get("status", "")).strip()

    allowed = {
        "pending",
        "processing",
        "confirmed",
        "shipped",
        "delivered",
        "cancelled",
        "returned",
        "refunded"
    }

    if status not in allowed:
        return jsonify({
            "ok": False,
            "error": "Invalid order status"
        }), 400

    conn = db()

    if not table_exists(conn, "orders"):
        conn.close()
        return jsonify({
            "ok": False,
            "error": "Orders table missing"
        }), 500

    cols = [
        x["name"]
        for x in conn.execute(
            "PRAGMA table_info(orders)"
        ).fetchall()
    ]

    # Existing production schema uses order_status.
    # Support both order_status and status safely.
    if "order_status" in cols:
        status_column = "order_status"
    elif "status" in cols:
        status_column = "status"
    else:
        conn.close()
        return jsonify({
            "ok": False,
            "error": "Orders status field missing"
        }), 500

    cur = conn.execute(
        f"UPDATE orders SET {status_column}=? WHERE id=?",
        (status, order_id)
    )

    if cur.rowcount == 0:
        conn.close()
        return jsonify({
            "ok": False,
            "error": "Order not found"
        }), 404

    audit(
        conn,
        "order_status",
        "order",
        order_id,
        status
    )

    conn.commit()
    conn.close()

    return jsonify({
        "ok": True,
        "order_id": order_id,
        "status": status
    })


# =========================================================
# PAYMENTS
# =========================================================

@owner_super_bp.get("/api/payments")
def payments():
    if not owner_only():
        return owner_denied()

    conn = db()

    if not table_exists(conn, "payments"):
        conn.close()
        return jsonify({
            "ok": True,
            "payments": []
        })

    rows = conn.execute(
        "SELECT * FROM payments "
        "ORDER BY id DESC LIMIT 500"
    ).fetchall()

    conn.close()

    return jsonify({
        "ok": True,
        "payments": json_rows(rows)
    })


# =========================================================
# REFUNDS
# =========================================================

@owner_super_bp.get("/api/refunds")
def refunds():
    if not owner_only():
        return owner_denied()

    conn = db()

    if not table_exists(conn, "refunds"):
        conn.close()
        return jsonify({
            "ok": True,
            "refunds": []
        })

    rows = conn.execute("""
        SELECT
            r.*,
            p.transaction_id,
            p.customer_id,
            u.name AS customer_name
        FROM refunds r
        LEFT JOIN payments p
            ON p.id=r.payment_id
        LEFT JOIN users u
            ON u.id=p.customer_id
        ORDER BY r.id DESC
        LIMIT 500
    """).fetchall()

    conn.close()

    return jsonify({
        "ok": True,
        "refunds": json_rows(rows)
    })


@owner_super_bp.post("/refund/<int:refund_id>/<action>")
def refund_action(refund_id, action):
    if not owner_only():
        return owner_denied()

    if action not in ("approve", "reject"):
        return jsonify({
            "ok": False,
            "error": "Invalid refund action"
        }), 400

    conn = db()

    refund = conn.execute(
        "SELECT * FROM refunds WHERE id=?",
        (refund_id,)
    ).fetchone()

    if not refund:
        conn.close()
        return jsonify({
            "ok": False,
            "error": "Refund not found"
        }), 404

    status = "approved" if action == "approve" else "rejected"

    conn.execute(
        "UPDATE refunds SET status=? WHERE id=?",
        (status, refund_id)
    )

    if table_exists(conn, "payments"):
        paycols = [
            x["name"]
            for x in conn.execute(
                "PRAGMA table_info(payments)"
            ).fetchall()
        ]

        if "refund_status" in paycols and refund["payment_id"]:
            conn.execute(
                "UPDATE payments SET refund_status=? "
                "WHERE id=?",
                (status, refund["payment_id"])
            )

    audit(
        conn,
        f"refund_{action}",
        "refund",
        refund_id,
        f"status={status}"
    )

    conn.commit()
    conn.close()

    return jsonify({
        "ok": True,
        "refund_id": refund_id,
        "status": status
    })


# =========================================================
# GENERIC READ CENTERS
# =========================================================

@owner_super_bp.get("/api/<resource>")
def generic_resource(resource):
    if not owner_only():
        return owner_denied()

    allowed = {
        "complaints": "complaints",
        "reviews": "reviews",
        "kyc": "kyc_documents",
        "support": "support_tickets",
        "notifications": "notifications",
        "security": "security_events",
        "audit": "audit_logs",
        "commissions": "commissions",
        "services": "services",
        "permissions": "owner_permissions"
    }

    table = allowed.get(resource)

    if not table:
        return jsonify({
            "ok": False,
            "error": "Unknown resource"
        }), 404

    conn = db()

    if not table_exists(conn, table):
        conn.close()
        return jsonify({
            "ok": True,
            resource: []
        })

    rows = conn.execute(
        f"SELECT * FROM {table} "
        "ORDER BY id DESC LIMIT 500"
    ).fetchall()

    conn.close()

    return jsonify({
        "ok": True,
        resource: json_rows(rows)
    })


# =========================================================
# NOTIFICATION READ
# =========================================================

@owner_super_bp.post("/notification/<int:notification_id>/read")
def notification_read(notification_id):
    if not owner_only():
        return owner_denied()

    conn = db()

    if not table_exists(conn, "notifications"):
        conn.close()
        return jsonify({
            "ok": False,
            "error": "Notifications table missing"
        }), 500

    cols = [
        x["name"]
        for x in conn.execute(
            "PRAGMA table_info(notifications)"
        ).fetchall()
    ]

    if "is_read" not in cols:
        conn.close()
        return jsonify({
            "ok": False,
            "error": "is_read field missing"
        }), 500

    conn.execute(
        "UPDATE notifications SET is_read=1 WHERE id=?",
        (notification_id,)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "ok": True,
        "message": "Notification marked read"
    })


# =========================================================
# SETTINGS
# =========================================================

@owner_super_bp.get("/api/settings")
def settings_get():
    if not owner_only():
        return owner_denied()

    conn = db()

    if not table_exists(conn, "app_settings"):
        conn.close()
        return jsonify({
            "ok": True,
            "settings": []
        })

    rows = conn.execute(
        "SELECT * FROM app_settings "
        "ORDER BY id ASC"
    ).fetchall()

    conn.close()

    return jsonify({
        "ok": True,
        "settings": json_rows(rows)
    })


@owner_super_bp.post("/settings")
def settings_save():
    if not owner_only():
        return owner_denied()

    data = request.get_json(silent=True) or {}

    conn = db()

    if not table_exists(conn, "app_settings"):
        conn.close()
        return jsonify({
            "ok": False,
            "error": "Settings table missing"
        }), 500

    cols = [
        x["name"]
        for x in conn.execute(
            "PRAGMA table_info(app_settings)"
        ).fetchall()
    ]

    key_col = "key" if "key" in cols else None
    value_col = "value" if "value" in cols else None

    if not key_col or not value_col:
        conn.close()
        return jsonify({
            "ok": False,
            "error": "Settings schema not compatible"
        }), 500

    changed = 0

    for key, value in data.items():

        row = conn.execute(
            f"SELECT id FROM app_settings "
            f"WHERE {key_col}=?",
            (key,)
        ).fetchone()

        if row:
            conn.execute(
                f"UPDATE app_settings "
                f"SET {value_col}=? WHERE id=?",
                (str(value), row["id"])
            )
        else:
            conn.execute(
                f"INSERT INTO app_settings "
                f"({key_col},{value_col}) VALUES (?,?)",
                (key, str(value))
            )

        changed += 1

    audit(
        conn,
        "owner_settings_update",
        "settings",
        None,
        str(data)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "ok": True,
        "changed": changed
    })


# =========================================================
# ANALYTICS
# =========================================================

@owner_super_bp.get("/api/analytics")
def analytics():
    if not owner_only():
        return owner_denied()

    conn = db()

    def count(table):
        try:
            return conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
        except Exception:
            return 0

    result = {
        "users": count("users"),
        "technicians": count("users"),
        "sellers": count("users"),
        "bookings": count("bookings"),
        "products": count("seller_products"),
        "orders": count("orders"),
        "payments": count("payments"),
        "complaints": count("complaints"),
        "reviews": count("reviews"),
        "notifications": count("notifications"),
        "security_events": count("security_events")
    }

    try:
        result["technicians"] = conn.execute(
            "SELECT COUNT(*) FROM users "
            "WHERE role='technician'"
        ).fetchone()[0]
    except Exception:
        pass

    try:
        result["sellers"] = conn.execute(
            "SELECT COUNT(*) FROM users "
            "WHERE role='seller'"
        ).fetchone()[0]
    except Exception:
        pass

    conn.close()

    return jsonify({
        "ok": True,
        "analytics": result
    })
