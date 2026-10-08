from flask import Blueprint, jsonify, request
from app.auth import role_required
from app.database.db import get_db

owner_settings_bp = Blueprint(
    "owner_settings",
    __name__,
    url_prefix="/owner/settings"
)


@owner_settings_bp.get("")
@role_required("owner")
def get_settings():

    conn = get_db()

    rows = conn.execute(
        """
        SELECT setting_key, setting_value, updated_at
        FROM app_settings
        ORDER BY setting_key
        """
    ).fetchall()

    conn.close()

    return jsonify({
        "settings": [dict(row) for row in rows]
    })


@owner_settings_bp.post("/update")
@role_required("owner")
def update_setting():

    data = request.get_json(silent=True) or {}

    key = str(data.get("key", "")).strip()
    value = str(data.get("value", "")).strip()

    if not key:
        return jsonify({
            "error": "Setting key is required"
        }), 400

    conn = get_db()

    existing = conn.execute(
        """
        SELECT id
        FROM app_settings
        WHERE setting_key=?
        """,
        (key,)
    ).fetchone()

    if existing:
        conn.execute(
            """
            UPDATE app_settings
            SET setting_value=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE setting_key=?
            """,
            (value, key)
        )
    else:
        conn.execute(
            """
            INSERT INTO app_settings
            (setting_key, setting_value)
            VALUES (?,?)
            """,
            (key, value)
        )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Setting updated",
        "key": key,
        "value": value
    })


@owner_settings_bp.post("/commission")
@role_required("owner")
def update_commission():

    data = request.get_json(silent=True) or {}

    try:
        percentage = float(data.get("percentage"))
    except (TypeError, ValueError):
        return jsonify({
            "error": "Valid commission percentage is required"
        }), 400

    if percentage < 0 or percentage > 100:
        return jsonify({
            "error": "Commission must be between 0 and 100"
        }), 400

    conn = get_db()

    conn.execute(
        """
        UPDATE app_settings
        SET setting_value=?,
            updated_at=CURRENT_TIMESTAMP
        WHERE setting_key='commission_percentage'
        """,
        (str(percentage),)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Commission updated",
        "percentage": percentage
    })


@owner_settings_bp.post("/maintenance")
@role_required("owner")
def maintenance_mode():

    data = request.get_json(silent=True) or {}

    enabled = bool(data.get("enabled"))

    value = "1" if enabled else "0"

    conn = get_db()

    conn.execute(
        """
        UPDATE app_settings
        SET setting_value=?,
            updated_at=CURRENT_TIMESTAMP
        WHERE setting_key='maintenance_mode'
        """,
        (value,)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Maintenance mode updated",
        "enabled": enabled
    })
