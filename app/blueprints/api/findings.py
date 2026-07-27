from flask import request, jsonify, current_app
from app.extensions import limiter
from app.repositories.finding_repository import FindingRepository
from app.repositories.category_repository import CategoryRepository
from app.services.finding_service import FindingService
from app.utils.security import validate_csrf_token


@api_bp.route("/findings", methods=["POST"])
@limiter.limit("10/hour")
def create_finding():
    files = request.files.getlist("photos")
    files = [f for f in files if f.filename]

    if len(files) > current_app.config.get("MAX_UPLOAD_FILES", 6):
        return jsonify({"error": f"maximum {current_app.config['MAX_UPLOAD_FILES']} files allowed"}), 400

    form_data = request.form.to_dict()

    finding, errors = FindingService.create_finding(form_data, files, current_app.config)
    if errors and not finding:
        return jsonify({"errors": errors}), 400

    nearby = FindingService.find_nearby(finding.lat, finding.lon)
    warning = None
    if nearby:
        warning = f"Found {len(nearby)} finding(s) within {current_app.config.get('DEDUP_RADIUS_METERS', 30)}m. Are you sure this is a new discovery?"

    response = {
        "id": finding.id,
        "token": errors.get("token") if isinstance(errors, dict) else None,
        "status": finding.status,
        "moderation_notice": "Your finding is pending moderation review." if finding.status == "pending" else None,
        "duplicate_warning": warning,
    }
    if isinstance(errors, dict) and errors.get("photo_errors"):
        response["photo_errors"] = errors["photo_errors"]

    return jsonify(response), 201


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


@api_bp.route("/findings/<finding_id>/status", methods=["PATCH"])
@limiter.limit("30/hour")
def update_finding_status(finding_id):
    data = request.get_json(silent=True) or {}
    token = data.get("token")
    new_status = data.get("status")

    if not token or not new_status:
        return jsonify({"error": "token and status required"}), 400

    finding, error = FindingService.update_status(finding_id, token, new_status)
    if error:
        return jsonify({"error": error}), 400

    return jsonify(finding.to_dict(include_photos=False))


@api_bp.route("/findings/<finding_id>/report", methods=["POST"])
@limiter.limit("20/hour")
def report_finding(finding_id):
    finding, error = FindingService.report_finding(finding_id)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"status": "reported", "reports_count": finding.reports_count})


@api_bp.route("/categories", methods=["GET"])
def list_categories():
    cats = CategoryRepository.get_all()
    return jsonify({"categories": [c.to_dict() for c in cats]})
