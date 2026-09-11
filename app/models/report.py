from app.extensions import db


class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    finding_id = db.Column(db.String(36), db.ForeignKey("findings.id", ondelete="CASCADE"), nullable=False)
    reason = db.Column(db.String(512), nullable=False, default="")
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
