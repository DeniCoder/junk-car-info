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
    status = db.Column(db.String(16), nullable=False, default="pending", index=True)  # pending, published, hidden, hidden_pending
    creator_fingerprint = db.Column(db.String(64), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    reports_count = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    published_at = db.Column(db.DateTime, nullable=True)
    hidden_at = db.Column(db.DateTime, nullable=True)
    removal_proof_photo = db.Column(db.String(256), nullable=True)  # фото-доказательство удаления
    is_archived = db.Column(db.Boolean, default=False, nullable=False, index=True)  # архивировано ли

    photos = db.relationship(
        "FindingPhoto", backref="finding", lazy="dynamic", order_by="FindingPhoto.sort_order"
    )
    report_entries = db.relationship("Report", backref="finding", lazy="dynamic")
    user = db.relationship("User", backref="findings")

    @property
    def confirmed_count_others(self):
        from app.repositories.vote_repository import VoteRepository
        return VoteRepository.count_confirmed_excluding_creator(self.id, self.creator_fingerprint)

    __table_args__ = (
        db.Index("ix_findings_status_published", "status", "published_at"),
        db.Index("ix_findings_coords", "lat", "lon"),
    )

    def to_dict(self, include_photos=True):
        from app.extensions import db as _db
        from app.models.category import Category as _Cat
        cat = _db.session.get(_Cat, self.category_id)
        from app.repositories.vote_repository import VoteRepository
        confirmed, removed = VoteRepository.count_by_type(self.id)
        confirmed_others = VoteRepository.count_confirmed_excluding_creator(self.id, self.creator_fingerprint)
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
            "confirmed_count": confirmed,
            "confirmed_count_others": confirmed_others,
            "removed_count": removed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "is_archived": self.is_archived,
            "removal_proof_photo": self.removal_proof_photo,
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
