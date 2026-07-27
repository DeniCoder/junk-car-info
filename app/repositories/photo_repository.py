from app.extensions import db
from app.models.finding_photo import FindingPhoto


class PhotoRepository:

    @staticmethod
    def create(photo):
        db.session.add(photo)
        db.session.commit()
        return photo

    @staticmethod
    def get_by_id(photo_id):
        return db.session.get(FindingPhoto, photo_id)

    @staticmethod
    def get_by_finding(finding_id):
        return FindingPhoto.query.filter_by(finding_id=finding_id).order_by(FindingPhoto.sort_order).all()

    @staticmethod
    def get_orphaned(older_than_hours=24):
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
        return FindingPhoto.query.filter(
            FindingPhoto.created_at < cutoff
        ).filter(
            ~FindingPhoto.finding_id.in_(
                db.session.query(db.text("findings.id"))
            )
        ).all()

    @staticmethod
    def delete(photo):
        db.session.delete(photo)
        db.session.commit()
