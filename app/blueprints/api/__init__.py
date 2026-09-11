from flask import Blueprint

api_bp = Blueprint("api", __name__)

from app.blueprints.api import findings  # noqa: E402, F401 — register routes
