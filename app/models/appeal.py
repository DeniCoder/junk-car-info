from app.extensions import db
from datetime import datetime


class Appeal(db.Model):
    __tablename__ = "appeals"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    finding_id = db.Column(db.String(36), db.ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(16), nullable=False, default="pending", index=True)  # pending, approved, rejected
    admin_comment = db.Column(db.Text, nullable=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    finding = db.relationship("Finding", backref="appeals")
    reviewer = db.relationship("User", foreign_keys=[reviewed_by], backref="reviewed_appeals")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "finding_id": self.finding_id,
            "reason": self.reason,
            "status": self.status,
            "admin_comment": self.admin_comment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
        }

    def __repr__(self):
        return f'<Appeal {self.id} for Finding {self.finding_id}>'
