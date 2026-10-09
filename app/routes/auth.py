from flask import Blueprint, request, jsonify, render_template

from app.auth import hash_password, verify_password, login_user, logout_user
from app.database.db import get_db

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.post("/register")
def register():
    # OWNER_ONLY_REGISTRATION_LOCK
    return jsonify({"error": "Account creation is available only through the Owner Panel."}), 403

    data = request.get_json(silent=True) or {}

    name = str(data.get("name", "")).strip()
    phone = str(data.get("phone", "")).strip()
    password = str(data.get("password", ""))
    role = str(data.get("role", "customer")).strip().lower()

    address = str(data.get("address", "")).strip()
    city = str(data.get("city", "")).strip()
    pincode = str(data.get("pincode", "")).strip()

    skill = str(data.get("skill", "")).strip()
    experience = str(data.get("experience", "")).strip()

    business_name = str(data.get("business", "")).strip()
    gstin = str(data.get("gst", "")).strip().upper()
    pan = str(data.get("pan", "")).strip().upper()
    product_category = str(data.get("category", "")).strip()

    if not name or not phone or not password:
        return jsonify({
            "error": "Name, phone and password are required"
        }), 400

    if role not in {"customer", "technician", "seller"}:
        return jsonify({
            "error": "Invalid registration role"
        }), 400

    if len(password) < 8:
        return jsonify({
            "error": "Password must be at least 8 characters"
        }), 400

    if not phone.isdigit() or len(phone) != 10:
        return jsonify({
            "error": "Enter a valid 10 digit mobile number"
        }), 400

    if not address or not city or not pincode:
        return jsonify({
            "error": "Address, city and PIN code are required"
        }), 400

    if not pincode.isdigit() or len(pincode) != 6:
        return jsonify({
            "error": "Enter a valid 6 digit PIN code"
        }), 400

    if role == "technician":
        if not skill or not experience:
            return jsonify({
                "error": "Technician skill and experience are required"
            }), 400

    if role == "seller":
        if not business_name or not pan or not product_category:
            return jsonify({
                "error": "Business name, PAN and product category are required"
            }), 400

    conn = get_db()

    existing = conn.execute(
        "SELECT id FROM users WHERE phone = ?",
        (phone,)
    ).fetchone()

    if existing:
        conn.close()

        return jsonify({
            "error": "Phone number already registered"
        }), 409

    password_hash = hash_password(password)

    status = "approved" if role == "customer" else "pending"

    cursor = conn.execute(
        """
        INSERT INTO users (
            name,
            phone,
            password_hash,
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
            product_category
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            phone,
            password_hash,
            role,
            status,
            address,
            city,
            pincode,
            skill or None,
            experience or None,
            business_name or None,
            gstin or None,
            pan or None,
            product_category or None
        )
    )

    conn.commit()

    user_id = cursor.lastrowid

    conn.close()

    return jsonify({
        "message": "Registration successful",
        "user_id": user_id,
        "role": role,
        "status": status
    }), 201


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    data = request.get_json(silent=True) or {}

    phone = str(data.get("phone", "")).strip()
    password = str(data.get("password", ""))

    if not phone or not password:
        return jsonify({
            "error": "Phone and password are required"
        }), 400

    conn = get_db()

    user = conn.execute(
        """
        SELECT
            id,
            name,
            phone,
            password_hash,
            role,
            status
        FROM users
        WHERE phone = ?
        """,
        (phone,)
    ).fetchone()

    conn.close()

    if not user:
        return jsonify({
            "error": "Invalid phone or password"
        }), 401

    if not verify_password(
        password,
        user["password_hash"]
    ):
        return jsonify({
            "error": "Invalid phone or password"
        }), 401

    if user["status"] != "approved":
        return jsonify({
            "error": "Account is pending approval"
        }), 403

    login_user(user)

    return jsonify({
        "message": "Login successful",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "phone": user["phone"],
            "role": user["role"]
        }
    })


@auth_bp.post("/logout")
def logout():
    logout_user()

    return jsonify({
        "message": "Logout successful"
    })
