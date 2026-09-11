import hashlib
import traceback
from functools import wraps

from flask import request, jsonify, current_app, session
from app.blueprints.api import api_bp
from app.extensions import limiter
from app.repositories.finding_repository import FindingRepository
from app.repositories.category_repository import CategoryRepository
from app.services.finding_service import FindingService
from app.utils.security import validate_csrf_token


def get_fingerprint():
    raw = (request.remote_addr or "0.0.0.0") + (request.user_agent.string or "")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def csrf_protect(f):
    """Decorator to protect API endpoints from CSRF attacks."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            if not validate_csrf_token():
                return jsonify({"error": "CSRF token missing or invalid"}), 403
        return f(*args, **kwargs)
    return decorated_function


@api_bp.route("/findings", methods=["POST"])
@limiter.limit("5/hour")
@csrf_protect
def create_finding():
    try:
        files = request.files.getlist("photos")
        files = [f for f in files if f.filename]

        if len(files) > current_app.config.get("MAX_UPLOAD_FILES", 6):
            return jsonify({"error": f"maximum {current_app.config['MAX_UPLOAD_FILES']} files allowed"}), 400

        form_data = request.form.to_dict()
        fingerprint = get_fingerprint()

        finding, errors = FindingService.create_finding(form_data, files, current_app.config, creator_fingerprint=fingerprint)
        if errors and not finding:
            return jsonify({"errors": errors}), 400

        nearby = FindingService.find_nearby(finding.lat, finding.lon)
        warning = None
        if nearby:
            warning = f"Found {len(nearby)} finding(s) within {current_app.config.get('DEDUP_RADIUS_METERS', 30)}m. Are you sure this is a new discovery?"

        response = {
            "id": finding.id,
            "status": finding.status,
            "moderation_notice": "Ожидает подтверждения от 3 пользователей." if finding.status == "pending" else None,
            "duplicate_warning": warning,
        }
        if isinstance(errors, dict) and errors.get("photo_errors"):
            response["photo_errors"] = errors["photo_errors"]

        return jsonify(response), 201
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "internal server error"}), 500


@api_bp.route("/findings", methods=["GET"])
def list_findings():
    bbox = request.args.get("bbox")
    if not bbox:
        return jsonify({"error": "bbox parameter required (south,west,north,east)"}), 400

    try:
        parts = [float(x.strip()) for x in bbox.split(",")]
        if len(parts) != 4:
            raise ValueError
        south, west, north, east = parts
    except (ValueError, TypeError):
        return jsonify({"error": "invalid bbox format"}), 400

    category_id = request.args.get("category_id", type=int)
    status = request.args.get("status", "published")

    findings = FindingRepository.get_published_in_bbox(
        south=south, west=west, north=north, east=east,
        category_id=category_id, status=status,
    )

    markers = [f.to_marker_dict() for f in findings]
    return jsonify({"findings": markers, "count": len(markers)})


@api_bp.route("/findings/<finding_id>", methods=["GET"])
def get_finding(finding_id):
    finding = FindingRepository.get_by_id(finding_id)
    if not finding:
        return jsonify({"error": "not found"}), 404
    return jsonify(finding.to_dict())


@api_bp.route("/findings/<finding_id>/vote", methods=["POST"])
@limiter.limit("30/hour")
@csrf_protect
def vote_finding(finding_id):
    data = request.get_json(silent=True) or {}
    vote_type = data.get("vote_type")
    if not vote_type:
        return jsonify({"error": "vote_type required (confirmed or removed)"}), 400

    fingerprint = get_fingerprint()
    result, error = FindingService.vote(finding_id, fingerprint, vote_type)
    if error:
        return jsonify({"error": error}), 400

    return jsonify(result)


@api_bp.route("/findings/<finding_id>/report", methods=["POST"])
@limiter.limit("20/hour")
@csrf_protect
def report_finding(finding_id):
    finding, error = FindingService.report_finding(finding_id)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"status": "reported", "reports_count": finding.reports_count})


@api_bp.route("/categories", methods=["GET"])
def list_categories():
    cats = CategoryRepository.get_all()
    return jsonify({"categories": [c.to_dict() for c in cats]})


@api_bp.route("/geocode", methods=["GET"])
def geocode():
    import urllib.request
    import urllib.parse
    import json as py_json

    q = request.args.get("q", "")
    if len(q) < 2:
        return jsonify({"results": []})
    
    # Получаем язык из сессии
    lang = session.get('language', 'ru')
    
    # Убираем ограничение countrycodes=ru для мирового поиска
    # Photon provides a reliable worldwide fallback for city search.
    url = f"https://photon.komoot.io/api/?q={urllib.parse.quote(q)}&limit=5&lang={urllib.parse.quote(lang)}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "junk-car-info/1.0 (contact: admin@junkcar.example.com)",
        "Accept-Language": lang,
    })
    try:
        # Ignore a stale system proxy: it is common in local Windows setups
        # and otherwise makes a functioning public geocoder look unavailable.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=5) as resp:
            data = py_json.loads(resp.read().decode("utf-8"))
        results = []
        for feature in data.get("features", []):
            coordinates = feature.get("geometry", {}).get("coordinates", [])
            if len(coordinates) < 2:
                continue
            properties = feature.get("properties", {})
            label = ", ".join(filter(None, [
                properties.get("name"), properties.get("city"), properties.get("country"),
            ]))
            results.append({
                "lat": str(coordinates[1]),
                "lon": str(coordinates[0]),
                "display_name": label or q,
            })
        return jsonify({"results": results, "provider": "photon"})
    except Exception:
        return jsonify({"results": []})
