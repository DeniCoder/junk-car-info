from app.extensions import db
from datetime import datetime


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    admin_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = db.Column(db.String(64), nullable=False, index=True)  # create, update, delete, publish, hide, reject, etc.
    entity_type = db.Column(db.String(32), nullable=False, index=True)  # finding, user, category, etc.
    entity_id = db.Column(db.String(64), nullable=False, index=True)
    old_value = db.Column(db.Text, nullable=True)  # JSON representation of old data
    new_value = db.Column(db.Text, nullable=True)  # JSON representation of new data
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False, index=True)

    admin = db.relationship("User", backref="audit_logs")

    def to_dict(self):
        return {
            "id": self.id,
            "admin_user_id": self.admin_user_id,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<AuditLog {self.id} - {self.action} on {self.entity_type}>'
