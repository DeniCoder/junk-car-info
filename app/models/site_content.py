from app.extensions import db


class SiteContent(db.Model):
    __tablename__ = "site_content"

    slug = db.Column(db.String(64), primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    content_md = db.Column(db.Text, nullable=False, default="")
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    def to_dict(self):
        return {
            "slug": self.slug,
            "title": self.title,
            "content_md": self.content_md,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
