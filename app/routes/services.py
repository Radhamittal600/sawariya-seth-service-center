from flask import Blueprint, jsonify, request

from app.auth import role_required
from app.database.db import get_db


services_bp = Blueprint(
    "services",
    __name__,
    url_prefix="/services"
)


@services_bp.get("")
def list_services():
    conn = get_db()

    services = conn.execute(
        """
        SELECT id, name, description, active
        FROM services
        WHERE active = 1
        ORDER BY id
        """
    ).fetchall()

    conn.close()

    return jsonify({
        "services": [dict(service) for service in services]
    })


@services_bp.post("")
@role_required("owner")
def create_service():
    data = request.get_json(silent=True) or {}

    name = str(data.get("name", "")).strip()
    description = str(data.get("description", "")).strip()

    if not name:
        return jsonify({
            "error": "Service name is required"
        }), 400

    conn = get_db()

    cursor = conn.execute(
        """
        INSERT INTO services (name, description)
        VALUES (?, ?)
        """,
        (name, description),
    )

    conn.commit()

    service_id = cursor.lastrowid
    conn.close()

    return jsonify({
        "message": "Service created",
        "service_id": service_id
    }), 201


@services_bp.delete("/<int:service_id>")
@role_required("owner")
def delete_service(service_id):
    conn = get_db()

    conn.execute(
        "UPDATE services SET active = 0 WHERE id = ?",
        (service_id,),
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Service disabled",
        "service_id": service_id
    })
