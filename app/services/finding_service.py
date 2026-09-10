from datetime import datetime, timedelta, timezone

from flask import current_app

from app.extensions import db
from app.models.finding import Finding
from app.models.finding_photo import FindingPhoto
from app.repositories.finding_repository import FindingRepository
from app.repositories.photo_repository import PhotoRepository
from app.services.photo_service import process_image, check_magic_bytes, delete_photo_files
from app.utils.validators import validate_lat_lon, validate_description, validate_location_name

REMOVE_THRESHOLD = 3
TRUSTED_REMOVE_THRESHOLD = 2
SUSPICIOUS_WINDOW_MINUTES = 60
SUSPICIOUS_VOTE_COUNT = 5


class FindingService:

    @staticmethod
    def create_finding(data, files, config, creator_fingerprint=None):
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

        now = datetime.now(timezone.utc)
        finding = Finding(
            category_id=category_id,
            sub_type=sub_type,
            description=description,
            location_name=location_name,
            lat=lat,
            lon=lon,
            status="pending",
            creator_fingerprint=creator_fingerprint,
        )

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

        return finding, {"photo_errors": photo_errors if photo_errors else None}

    @staticmethod
    def get_finding(finding_id):
        return FindingRepository.get_by_id(finding_id)

    @staticmethod
    def report_finding(finding_id):
        finding = FindingRepository.get_by_id(finding_id)
        if not finding:
            return None, "not found"
        from app.models.report import Report
        report = Report(finding_id=finding_id, reason="user report")
        db.session.add(report)
        finding.reports_count = (finding.reports_count or 0) + 1
        db.session.commit()
        return finding, None

    @staticmethod
    def find_nearby(lat, lon, radius_m=None):
        if radius_m is None:
            radius_m = current_app.config.get("DEDUP_RADIUS_METERS", 30)
        return FindingRepository.get_published_near(lat, lon, radius_m)

    @staticmethod
    def delete_finding(finding_id):
        finding = FindingRepository.get_by_id(finding_id)
        if not finding:
            return False
        config = current_app.config
        for photo in finding.photos.all():
            delete_photo_files(photo, config)
            db.session.delete(photo)
        from app.models.report import Report
        from app.models.vote import Vote
        Report.query.filter_by(finding_id=finding_id).delete()
        Vote.query.filter_by(finding_id=finding_id).delete()
        db.session.delete(finding)
        db.session.commit()
        return True

    @staticmethod
    def vote(finding_id, fingerprint, vote_type):
        from app.repositories.vote_repository import VoteRepository

        finding = FindingRepository.get_by_id(finding_id)
        if not finding:
            return None, "not found"

        recent = VoteRepository.get_recent_by_finding_and_fingerprint(finding_id, fingerprint)
        if recent:
            return None, "вы уже голосовали"

        suspicious_count = VoteRepository.count_votes_in_window(
            finding_id, vote_type, SUSPICIOUS_WINDOW_MINUTES
        )
        is_trusted = suspicious_count < SUSPICIOUS_VOTE_COUNT

        VoteRepository.create(finding_id, fingerprint, vote_type, is_trusted=is_trusted)
        
        confirmed, removed = VoteRepository.count_by_type(finding_id, trusted_only=False)
        confirmed_trusted, removed_trusted = VoteRepository.count_by_type(finding_id, trusted_only=True)
        confirmed_others = VoteRepository.count_confirmed_excluding_creator(finding_id, finding.creator_fingerprint)

        should_hide = False
        if removed_trusted >= TRUSTED_REMOVE_THRESHOLD:
            should_hide = True
        elif removed >= REMOVE_THRESHOLD and suspicious_count < SUSPICIOUS_VOTE_COUNT:
            should_hide = True

        if should_hide and finding.status != "hidden":
            finding.status = "hidden"
            finding.hidden_at = datetime.now(timezone.utc)
            db.session.commit()

        return {
            "confirmed": confirmed,
            "confirmed_others": confirmed_others,
            "removed": removed,
            "finding_status": finding.status,
        }, None
