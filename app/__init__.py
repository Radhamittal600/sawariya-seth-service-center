import os

from flask import Flask
from werkzeug.security import generate_password_hash

from app.database.db import get_db, init_db


def bootstrap_owner(app):
    """Only reset owner credentials when explicitly configured."""

    phone = os.environ.get("OWNER_BOOTSTRAP_PHONE", "").strip()
    password = os.environ.get("OWNER_BOOTSTRAP_PASSWORD", "")
    name = os.environ.get("OWNER_BOOTSTRAP_NAME", "Chetan Mittal").strip()

    if not phone or not password:
        return

    if not phone.isdigit() or len(phone) != 10 or len(password) < 12:
        app.logger.error("Owner bootstrap skipped: invalid configuration.")
        return

    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT id, role FROM users WHERE phone = ?", (phone,)
        ).fetchone()

        if existing and existing["role"] != "owner":
            app.logger.error("Owner bootstrap skipped: phone belongs to a non-owner.")
            return

        owner = existing or conn.execute(
            "SELECT id FROM users WHERE role = 'owner' ORDER BY id LIMIT 1"
        ).fetchone()

        password_hash = generate_password_hash(password)

        if owner:
            conn.execute(
                """UPDATE users
                   SET name = ?, phone = ?, password_hash = ?,
                       role = 'owner', status = 'approved'
                   WHERE id = ?""",
                (name, phone, password_hash, owner["id"])
            )
        else:
            conn.execute(
                """INSERT INTO users
                   (name, phone, password_hash, role, status)
                   VALUES (?, ?, ?, 'owner', 'approved')""",
                (name, phone, password_hash)
            )

        conn.commit()
        app.logger.info("Owner bootstrap completed.")
    except Exception:
        conn.rollback()
        app.logger.exception("Owner bootstrap failed.")
    finally:
        conn.close()


def create_app():
    app = Flask(__name__)

    from app.config import Config
    app.config.from_object(Config)

    init_db()
    bootstrap_owner(app)

    from app.routes.auth import auth_bp
    from app.routes.bookings import bookings_bp
    from app.routes.main import main_bp
    from app.routes.owner import owner_bp
    from app.routes.owner_actions import owner_actions_bp
    from app.routes.owner_analytics import owner_analytics_bp
    from app.routes.owner_assignment import owner_assignment_bp
    from app.routes.owner_command import owner_command_bp
    from app.routes.owner_marketplace import owner_marketplace_bp
    from app.routes.owner_master import owner_master_bp
    from app.routes.owner_master_v2 import owner_master_v2_bp
    from app.routes.owner_notifications import owner_notifications_bp
    from app.routes.owner_operations import owner_operations_bp
    from app.routes.owner_security import owner_security_bp
    from app.routes.owner_settings import owner_settings_bp
    from app.routes.owner_super import owner_super_bp
    from app.routes.owner_trust import owner_trust_bp
    from app.routes.owner_users import owner_users_bp
    from app.routes.payments import payments_bp
    from app.routes.seller_marketplace import seller_marketplace_bp
    from app.routes.services import services_bp
    from app.routes.technician import technician_bp
    from app.routes.video_calls import video_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(bookings_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(owner_bp)
    app.register_blueprint(owner_actions_bp)
    app.register_blueprint(owner_analytics_bp)
    app.register_blueprint(owner_assignment_bp)
    app.register_blueprint(owner_command_bp)
    app.register_blueprint(owner_marketplace_bp)
    app.register_blueprint(owner_master_bp)
    app.register_blueprint(owner_master_v2_bp)
    app.register_blueprint(owner_notifications_bp)
    app.register_blueprint(owner_operations_bp)
    app.register_blueprint(owner_security_bp)
    app.register_blueprint(owner_settings_bp)
    app.register_blueprint(owner_super_bp)
    app.register_blueprint(owner_trust_bp)
    app.register_blueprint(owner_users_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(seller_marketplace_bp)
    app.register_blueprint(services_bp)
    app.register_blueprint(technician_bp)
    app.register_blueprint(video_bp)

    return app
