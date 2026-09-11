import os
import click

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, session
from flask_babel import Babel, lazy_gettext as _l

from app.config import Config
from app.extensions import db, migrate, limiter, talisman, login_manager
from app.models.user import User


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Инициализация Flask-Babel для интернационализации
    babel = Babel(app)
    
    def get_locale():
        """Определяет язык пользователя на основе приоритетов:
        1. Язык в сессии (выбранный пользователем)
        2. Язык браузера из Accept-Language header
        3. Язык по умолчанию из конфига
        """
        if 'language' in session:
            return session['language']
        return request.accept_languages.best_match(app.config.get('LANGUAGES', ['ru']))
    
    babel.init_app(app, locale_selector=get_locale)

    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    login_manager.init_app(app)
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
    from app.blueprints.auth import auth_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(media_bp, url_prefix="/media")
    app.register_blueprint(user_bp, url_prefix="/user")
    app.register_blueprint(auth_bp, url_prefix="/auth")

    from app.utils.security import csrf_init
    csrf_init(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    register_error_handlers(app)

    os.makedirs(app.config["MEDIA_ROOT"], exist_ok=True)

    @app.cli.command("create-admin")
    @click.option("--username", prompt=True, help="Administrator username.")
    @click.option("--email", prompt=True, help="Administrator email.")
    @click.password_option(confirmation_prompt=True)
    def create_admin(username, email, password):
        """Create an administrator account for the local instance."""
        username = username.strip()
        email = email.strip().lower()
        if User.query.filter((User.username == username) | (User.email == email)).first():
            raise click.ClickException("A user with this username or email already exists.")
        user = User(username=username, email=email, is_admin=True, is_active=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Administrator '{username}' created.")

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
