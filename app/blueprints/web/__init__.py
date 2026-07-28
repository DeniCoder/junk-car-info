from flask import Blueprint

web_bp = Blueprint("web", __name__, template_folder="../templates")

from app.blueprints.web import views  # noqa: E402, F401 — register routes
