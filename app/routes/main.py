from flask import Blueprint, jsonify, render_template

from app.auth import role_required, get_current_user
from app.database.db import get_db


main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def home():
    return render_template("home.html")


@main_bp.get("/login")
def login_page():
    return render_template("login.html")


@main_bp.get("/register")
def register_page():
    return render_template("register.html")


@main_bp.get("/customer")
@role_required("customer")
def customer_dashboard():
    user = get_current_user()
    return render_template(
        "customer.html",
        user=user
    )



@main_bp.get("/video-call")
@role_required("technician")
def video_call_page():
    return render_template("video_call.html")





@main_bp.get("/video-room/<int:call_id>")
def video_room(call_id):
    user = get_current_user()
    if not user:
        return jsonify({"error": "Login required"}), 401

    conn = get_db()
    call = conn.execute("""
        SELECT caller_id, technician_id, status
        FROM video_calls
        WHERE id = ?
    """, (call_id,)).fetchone()
    conn.close()

    if not call:
        return jsonify({"error": "Call not found"}), 404

    if user["id"] not in (call["caller_id"], call["technician_id"]):
        return jsonify({"error": "Permission denied"}), 403

    if call["status"] not in ("requested", "accepted"):
        return jsonify({"error": "This call is no longer active"}), 400

    role = "technician" if user["id"] == call["technician_id"] else "caller"

    return render_template(
        "video_room.html",
        call_id=call_id,
        role=role
    )

@main_bp.get("/health")
def health():
    return jsonify({
        "status": "healthy",
        "backend": "connected"
    })

# ================= SELLER DASHBOARD =================

@main_bp.get("/seller-dashboard")
def seller_dashboard():
    from flask import session, redirect, url_for

    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    if session.get("role") != "seller":
        return redirect(url_for("main.home"))

    return render_template("seller.html")
