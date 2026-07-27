import secrets
from datetime import datetime, timezone

from flask import current_app

from app.extensions import db
from app.models.finding import Finding
from app.models.finding_photo import FindingPhoto
from app.repositories.finding_repository import FindingRepository
from app.repositories.photo_repository import PhotoRepository
from app.services.photo_service import process_image, check_magic_bytes, delete_photo_files
from app.utils.security import hash_token, verify_token
from app.utils.validators import validate_lat_lon, validate_description, validate_location_name


class FindingService:

    @staticmethod
    def create_finding(data, files, config):
        category_id = data.get("category_id")
        if not category_id:
            return None, {"category_id": "required"}
        try:
            category_id = int(category_id)
        except (ValueError, TypeError):
            return None, {"category_id": "must be an integer"}

        lat, lon, coord_errors = validate_lat_lon(data.get("lat"), data.get("lon"))
        if coord_errors:
            return None, {"coordinates": coord_errors}

        description = validate_description(data.get("description", ""))
        location_name = validate_location_name(data.get("location_name", ""))
        sub_type = data.get("sub_type", "").strip() if data.get("sub_type") else None

        token = secrets.token_urlsafe(32)
        token_hash = hash_token(token)

        finding = Finding(
            category_id=category_id,
            sub_type=sub_type,
            description=description,
            location_name=location_name,
            lat=lat,
            lon=lon,
            status="pending" if not config.get("AUTO_PUBLISH", False) else "published",
            edit_token_hash=token_hash,
        )
        if config.get("AUTO_PUBLISH", False):
            finding.published_at = datetime.now(timezone.utc)

        FindingRepository.create(finding)

        photo_errors = []
        max_files = config.get("MAX_UPLOAD_FILES", 6)
        if files and len(files) > max_files:
            return finding, {"files": f"maximum {max_files} files allowed"}

        for i, f in enumerate(files[:max_files]):
            file_data = f.read()
            if len(file_data) > config.get("MAX_FILE_SIZE_MB", 8) * 1024 * 1024:
                photo_errors.append({"index": i, "error": "file too large"})
                continue

            file_type = check_magic_bytes(file_data)
            if not file_type:
                photo_errors.append({"index": i, "error": "invalid file type"})
                continue

            result, err = process_image(file_data, finding.id, config)
            if err:
                photo_errors.append({"index": i, "error": err})
                continue

            photo = FindingPhoto(
                finding_id=finding.id,
                sort_order=i,
                **result,
            )
            PhotoRepository.create(photo)

        return finding, {"token": token, "photo_errors": photo_errors if photo_errors else None}

    @staticmethod
    def get_finding(finding_id):
        return FindingRepository.get_by_id(finding_id)

    @staticmethod
    def update_status(finding_id, token, new_status):
        finding = FindingRepository.get_by_id(finding_id)
        if not finding:
            return None, "not found"
        if not finding.edit_token_hash:
            return None, "editing not available"
        if not verify_token(token, finding.edit_token_hash):
            return None, "invalid token"
        if new_status not in ("published", "removed"):
            return None, "invalid status"
        updated = FindingRepository.update_status(finding_id, new_status)
        return updated, None

    @staticmethod
    def report_finding(finding_id):
        finding = FindingRepository.get_by_id(finding_id)
        if not finding:
            return None, "not found"
        from app.models.report import Report
        report = Report(finding_id=finding_id, reason="user report")
        from app.extensions import db
        db.session.add(report)
        finding.reports_count = (finding.reports_count or 0) + 1
        if finding.reports_count >= 5 and finding.status == "published":
            finding.status = "hidden"
            finding.hidden_at = datetime.now(timezone.utc)
        db.session.commit()
        return finding, None

    @staticmethod
    def find_nearby(lat, lon, radius_m=None):
        if radius_m is None:
            radius_m = current_app.config.get("DEDUP_RADIUS_METERS", 30)
        return FindingRepository.get_published_near(lat, lon, radius_m)

    @staticmethod
    def moderate(finding_id, action):
        if action == "approve":
            return FindingRepository.update_status(finding_id, "published")
        elif action == "reject":
            return FindingRepository.update_status(finding_id, "rejected")
        elif action == "remove":
            return FindingRepository.update_status(finding_id, "removed")
        return None

    @staticmethod
    def delete_finding(finding_id):
        finding = FindingRepository.get_by_id(finding_id)
        if not finding:
            return False
        config = current_app.config
        for photo in finding.photos.all():
            delete_photo_files(photo, config)
            db.session.delete(photo)
        db.session.delete(finding)
        db.session.commit()
        return True
