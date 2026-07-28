from flask import Blueprint

admin_bp = Blueprint("admin", __name__, template_folder="../templates")

from app.blueprints.admin import views  # noqa: E402, F401 — register routes
