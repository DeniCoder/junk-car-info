import os

from dotenv import load_dotenv
load_dotenv()

from flask import Flask

from app.config import Config
from app.extensions import db, migrate, limiter, talisman


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    talisman.init_app(
        app,
        content_security_policy=app.config["CONTENT_SECURITY_POLICY"],
        force_https=False,
        session_cookie_secure=False,
    )

    from app.blueprints.web import web_bp
    from app.blueprints.api import api_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.media import media_bp
    from app.blueprints.user import user_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(media_bp, url_prefix="/media")
    app.register_blueprint(user_bp, url_prefix="/user")

    from app.utils.security import csrf_init
    csrf_init(app)

    register_error_handlers(app)

    os.makedirs(app.config["MEDIA_ROOT"], exist_ok=True)

    return app


def register_error_handlers(app):
    from flask import render_template, jsonify

    @app.errorhandler(404)
    def not_found(e):
        if __import__("flask").request.path.startswith("/api/"):
            return jsonify({"error": "not found"}), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def too_large(e):
        if __import__("flask").request.path.startswith("/api/"):
            return jsonify({"error": "file too large"}), 413
        return render_template("errors/413.html"), 413

    @app.errorhandler(429)
    def rate_limited(e):
        if __import__("flask").request.path.startswith("/api/"):
            return jsonify({"error": "rate limit exceeded"}), 429
        return render_template("errors/429.html"), 429

    @app.errorhandler(500)
    def server_error(e):
        if __import__("flask").request.path.startswith("/api/"):
            return jsonify({"error": "internal server error"}), 500
        return render_template("errors/500.html"), 500
