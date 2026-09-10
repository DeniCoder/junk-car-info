from app.extensions import db


class Vote(db.Model):
    __tablename__ = "votes"

    id = db.Column(db.Integer, primary_key=True)
    finding_id = db.Column(db.String(36), db.ForeignKey("findings.id", ondelete="CASCADE"), nullable=False)
    fingerprint = db.Column(db.String(64), nullable=False)
    vote_type = db.Column(db.String(16), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    is_trusted = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (
        db.Index("ix_votes_finding_fingerprint", "finding_id", "fingerprint"),
        db.Index("ix_votes_trusted", "is_trusted", "vote_type"),
    )
