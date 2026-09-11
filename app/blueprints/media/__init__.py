from flask import Blueprint

media_bp = Blueprint("media", __name__)

from app.blueprints.media import views  # noqa: E402, F401 — register routes
