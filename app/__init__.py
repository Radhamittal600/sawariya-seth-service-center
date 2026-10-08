from app.routes.owner_master_v2 import owner_master_v2_bp
from flask import Flask
from app.database.db import init_db


from app.routes.seller_marketplace import seller_marketplace_bp


def create_app():
    try:
        from app.routes.owner_super import owner_super_bp
    except Exception:
        owner_super_bp = None

    app = Flask(__name__)

    app.register_blueprint(owner_master_v2_bp)
    app.register_blueprint(seller_marketplace_bp)

    app.config["APP_NAME"] = "Sawariya Seth Service Center"
    app.config["VERSION"] = "1.0.0"

    app.config["SECRET_KEY"] = "change-this-later"

    init_db()

    from app.routes.main import main_bp
    app.register_blueprint(main_bp)

    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.routes.owner import owner_bp
    app.register_blueprint(owner_bp)

    from app.routes.services import services_bp
    app.register_blueprint(services_bp)

    from app.routes.bookings import bookings_bp
    app.register_blueprint(bookings_bp)

    from app.routes.technician import technician_bp
    app.register_blueprint(technician_bp)
    from app.routes.payments import payments_bp
    app.register_blueprint(payments_bp)

    from app.routes.owner_operations import owner_operations_bp
    app.register_blueprint(owner_operations_bp)

    from app.routes.owner_marketplace import owner_marketplace_bp
    app.register_blueprint(owner_marketplace_bp)

    from app.routes.owner_trust import owner_trust_bp
    app.register_blueprint(owner_trust_bp)

    from app.routes.owner_security import owner_security_bp
    app.register_blueprint(owner_security_bp)

    from app.routes.owner_settings import owner_settings_bp
    app.register_blueprint(owner_settings_bp)

    from app.routes.owner_analytics import owner_analytics_bp
    app.register_blueprint(owner_analytics_bp)

    from app.routes.owner_notifications import owner_notifications_bp
    from app.routes.owner_command import owner_command_bp
    from app.routes.owner_users import owner_users_bp
    from app.routes.owner_master import owner_master_bp
    from app.routes.owner_actions import owner_actions_bp
    from app.routes.owner_assignment import owner_assignment_bp
    from app.routes.video_calls import video_bp
    app.register_blueprint(owner_assignment_bp)
    app.register_blueprint(video_bp)
    app.register_blueprint(owner_actions_bp)
    app.register_blueprint(owner_master_bp)
    app.register_blueprint(owner_users_bp)
    app.register_blueprint(owner_command_bp)
    app.register_blueprint(owner_notifications_bp)

    # OWNER A-Z MASTER CONTROL
    try:
        if owner_super_bp is not None:
            app.register_blueprint(owner_super_bp)
    except Exception as e:
        app.logger.exception("Owner Super Blueprint registration failed: %s", e)

    return app

