import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or os.environ.get(
        "FLASK_SECRET_KEY", "dev-only-change-this-before-deployment"
    )
    DEBUG = False
    TESTING = False
