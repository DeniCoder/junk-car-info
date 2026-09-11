from app.extensions import db
from datetime import datetime


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(256), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(32), nullable=False, default="info")  # info, success, warning, error
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    related_finding_id = db.Column(db.String(36), db.ForeignKey("findings.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False, index=True)

    finding = db.relationship("Finding", backref="notifications")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "message": self.message,
            "type": self.notification_type,
            "is_read": self.is_read,
            "related_finding_id": self.related_finding_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Notification {self.id} for User {self.user_id}>'
