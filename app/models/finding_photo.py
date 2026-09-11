import uuid

from app.extensions import db


class FindingPhoto(db.Model):
    __tablename__ = "finding_photos"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    finding_id = db.Column(db.String(36), db.ForeignKey("findings.id", ondelete="CASCADE"), nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    web_path = db.Column(db.String(512), nullable=False)
    thumb_path = db.Column(db.String(512), nullable=False)
    original_path = db.Column(db.String(512), nullable=True)
    mime = db.Column(db.String(16), nullable=False)
    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    bytes = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    __table_args__ = (
        db.Index("ix_finding_photos_finding_sort", "finding_id", "sort_order"),
    )

    @property
    def thumb_url(self):
        return f"/media/file/{self.thumb_path}" if self.thumb_path else None

    @property
    def web_url(self):
        return f"/media/file/{self.web_path}" if self.web_path else None

    @property
    def original_url(self):
        if self.original_path:
            return f"/media/file/{self.original_path}"
        return None

    def to_dict(self):
        return {
            "id": self.id,
            "sort_order": self.sort_order,
            "web_url": self.web_url,
            "thumb_url": self.thumb_url,
            "original_url": self.original_url,
            "mime": self.mime,
            "width": self.width,
            "height": self.height,
            "bytes": self.bytes,
        }
