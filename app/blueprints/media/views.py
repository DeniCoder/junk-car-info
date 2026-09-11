import os
from flask import send_from_directory, current_app, abort

from app.blueprints.media import media_bp


@media_bp.route("/file/<path:filepath>")
def serve_file(filepath):
    media_root = current_app.config["MEDIA_ROOT"]
    safe = os.path.normpath(filepath)
    if ".." in safe or safe.startswith("/"):
        abort(403)
    full = os.path.join(media_root, safe)
    if not os.path.isfile(full):
        abort(404)
    directory = os.path.dirname(full)
    filename = os.path.basename(full)
    resp = send_from_directory(directory, filename)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp
