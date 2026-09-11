from datetime import datetime, timedelta, timezone

from flask import current_app

from app.extensions import db
from app.models.finding import Finding
from app.models.finding_photo import FindingPhoto
from app.services.photo_service import get_storage


def cleanup_rejected():
    days = current_app.config.get("CLEANUP_REJECTED_DAYS", 7)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    findings = Finding.query.filter(
        Finding.status.in_(["rejected", "removed"]),
        Finding.created_at < cutoff,
    ).all()
    storage = get_storage()
    count = 0
    for f in findings:
        for photo in f.photos.all():
            for path in [photo.web_path, photo.thumb_path, photo.original_path]:
                if path:
                    storage.delete(path)
            db.session.delete(photo)
        db.session.delete(f)
        count += 1
    db.session.commit()
    return count


def cleanup_pending():
    days = current_app.config.get("CLEANUP_PENDING_DAYS", 30)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    findings = Finding.query.filter(
        Finding.status == "pending",
        Finding.created_at < cutoff,
    ).all()
    storage = get_storage()
    count = 0
    for f in findings:
        for photo in f.photos.all():
            for path in [photo.web_path, photo.thumb_path, photo.original_path]:
                if path:
                    storage.delete(path)
            db.session.delete(photo)
        db.session.delete(f)
        count += 1
    db.session.commit()
    return count


def cleanup_orphans():
    hours = current_app.config.get("CLEANUP_ORPHAN_HOURS", 24)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    finding_ids = db.session.query(Finding.id).subquery()
    orphan_photos = FindingPhoto.query.filter(
        FindingPhoto.created_at < cutoff,
        ~FindingPhoto.finding_id.in_(db.session.query(finding_ids))
    ).all()
    storage = get_storage()
    count = 0
    for photo in orphan_photos:
        for path in [photo.web_path, photo.thumb_path, photo.original_path]:
            if path:
                storage.delete(path)
        db.session.delete(photo)
        count += 1
    db.session.commit()
    return count
