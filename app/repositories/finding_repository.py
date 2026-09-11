from datetime import datetime, timedelta, timezone

from sqlalchemy import func, text

from app.extensions import db
from app.models.finding import Finding
from app.models.finding_photo import FindingPhoto


class FindingRepository:

    @staticmethod
    def create(finding):
        db.session.add(finding)
        db.session.commit()
        return finding

    @staticmethod
    def get_by_id(finding_id):
        return db.session.get(Finding, finding_id)

    @staticmethod
    def get_published_in_bbox(south, west, north, east, category_id=None, status="published", limit=500):
        q = Finding.query.filter(
            Finding.status.in_(["published", "pending"]),
            Finding.lat >= south,
            Finding.lat <= north,
            Finding.lon >= west,
            Finding.lon <= east,
        )
        if category_id:
            q = q.filter_by(category_id=category_id)
        return q.order_by(Finding.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_published_near(lat, lon, radius_m, category_id=None):
        from app.utils.validators import haversine_distance
        lat_f, lon_f = float(lat), float(lon)
        candidates = Finding.query.filter(
            Finding.status == "published",
            Finding.lat.between(lat_f - 0.01, lat_f + 0.01),
            Finding.lon.between(lon_f - 0.01, lon_f + 0.01),
        ).all()
        nearby = []
        for f in candidates:
            dist = haversine_distance(float(lat), float(lon), float(f.lat), float(f.lon))
            if dist <= radius_m:
                if category_id is None or f.category_id == category_id:
                    nearby.append(f)
        return nearby

    @staticmethod
    def update_status(finding_id, status):
        f = db.session.get(Finding, finding_id)
        if f:
            f.status = status
            if status == "published" and not f.published_at:
                f.published_at = datetime.now(timezone.utc)
            elif status in ("removed", "rejected"):
                f.hidden_at = datetime.now(timezone.utc)
            db.session.commit()
        return f

    @staticmethod
    def increment_reports(finding_id):
        f = db.session.get(Finding, finding_id)
        if f:
            f.reports_count = Finding.reports_count + 1
            db.session.commit()
        return f

    @staticmethod
    def get_pending_moderation(page=1, per_page=20):
        q = Finding.query.filter_by(status="pending").order_by(Finding.created_at.desc())
        return q.paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def get_by_status(status, page=1, per_page=20):
        q = Finding.query.filter_by(status=status).order_by(Finding.created_at.desc())
        return q.paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def count_published():
        return Finding.query.filter(Finding.status.in_(["published", "pending"])).count()

    @staticmethod
    def delete(finding):
        db.session.delete(finding)
        db.session.commit()
