import uuid

from app.extensions import db


class Finding(db.Model):
    __tablename__ = "findings"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    sub_type = db.Column(db.String(64), nullable=True)
    description = db.Column(db.Text, nullable=False, default="")
    location_name = db.Column(db.String(256), nullable=False, default="")
    lat = db.Column(db.Numeric(9, 6), nullable=False)
    lon = db.Column(db.Numeric(9, 6), nullable=False)
    status = db.Column(db.String(16), nullable=False, default="pending", index=True)
    edit_token_hash = db.Column(db.String(128), nullable=True)
    reports_count = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    published_at = db.Column(db.DateTime, nullable=True)
    hidden_at = db.Column(db.DateTime, nullable=True)

    photos = db.relationship(
        "FindingPhoto", backref="finding", lazy="dynamic", order_by="FindingPhoto.sort_order"
    )
    report_entries = db.relationship("Report", backref="finding", lazy="dynamic")

    __table_args__ = (
        db.Index("ix_findings_status_published", "status", "published_at"),
        db.Index("ix_findings_coords", "lat", "lon"),
    )

    def to_dict(self, include_photos=True, include_edit_token=False):
        from app.extensions import db as _db
        cat = _db.session.get(Category, self.category_id)
        d = {
            "id": self.id,
            "category_id": self.category_id,
            "category_title": cat.title if cat else "",
            "sub_type": self.sub_type,
            "description": self.description,
            "location_name": self.location_name,
            "lat": float(self.lat),
            "lon": float(self.lon),
            "status": self.status,
            "reports_count": self.reports_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }
        if include_photos:
            d["photos"] = [p.to_dict() for p in self.photos.all()]
        return d

    def to_marker_dict(self):
        return {
            "id": self.id,
            "category_id": self.category_id,
            "sub_type": self.sub_type,
            "lat": float(self.lat),
            "lon": float(self.lon),
            "status": self.status,
            "location_name": self.location_name,
            "thumb_url": self.photos.first().thumb_url if self.photos.first() else None,
        }


from app.models.category import Category
