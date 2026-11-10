import os

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from . import db
from .routes import admin, auth, games, live, me, play


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    uploads = os.environ.get("UPLOAD_FOLDER") or os.path.join(root, "uploads")
    os.makedirs(uploads, exist_ok=True)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "little-learner-dev-secret"),
        UPLOAD_FOLDER=uploads,
        TOKEN_MAX_AGE=60 * 60 * 24 * 7,
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,
    )
    if config:
        app.config.update(config)

    origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()] or "*"
    CORS(app, resources={r"/api/*": {"origins": origins}}, expose_headers=["Authorization"])
    db.init_app(app)
    with app.app_context():
        db.init_db()

    for module in (auth, games, play, live, me, admin):
        app.register_blueprint(module.bp)

    @app.get("/api/health")
    def health():
        return jsonify(status="ok", service="little-learner-backend")

    @app.get("/")
    def index():
        return jsonify(name="Little Learner Backend", docs="/api/health")

    @app.errorhandler(HTTPException)
    def http_error(e):
        return jsonify(error=e.description, status=e.code), e.code

    @app.errorhandler(Exception)
    def server_error(e):
        app.logger.exception(e)
        return jsonify(error="Server error", status=500), 500

    return app
