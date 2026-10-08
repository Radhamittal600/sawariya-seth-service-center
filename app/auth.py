from functools import wraps
from flask import session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

from app.database.db import get_db


ROLES = {
    "customer",
    "technician",
    "seller",
    "owner",
}


def hash_password(password):
    return generate_password_hash(password)


def verify_password(password, password_hash):
    return check_password_hash(password_hash, password)


def get_current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    conn = get_db()

    user = conn.execute(
        """
        SELECT id, name, phone, role, status
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()

    conn.close()

    return user


def login_user(user):
    session.clear()
    session["user_id"] = user["id"]
    session["role"] = user["role"]


def logout_user():
    session.clear()


def role_required(*allowed_roles):
    def decorator(view_function):

        @wraps(view_function)
        def wrapper(*args, **kwargs):
            user = get_current_user()

            if not user:
                return jsonify({
                    "error": "Login required"
                }), 401

            if user["status"] != "approved":
                return jsonify({
                    "error": "Account is not approved"
                }), 403

            if user["role"] not in allowed_roles:
                return jsonify({
                    "error": "Permission denied"
                }), 403

            return view_function(*args, **kwargs)

        return wrapper

    return decorator
