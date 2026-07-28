from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models.vote import Vote


class VoteRepository:

    @staticmethod
    def get_recent_by_finding_and_fingerprint(finding_id, fingerprint, hours=24):
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return Vote.query.filter(
            Vote.finding_id == finding_id,
            Vote.fingerprint == fingerprint,
            Vote.created_at > cutoff,
        ).first()

    @staticmethod
    def count_by_type(finding_id):
        confirmed = Vote.query.filter_by(finding_id=finding_id, vote_type="confirmed").count()
        removed = Vote.query.filter_by(finding_id=finding_id, vote_type="removed").count()
        return confirmed, removed

    @staticmethod
    def count_confirmed_excluding_creator(finding_id, creator_fingerprint):
        if not creator_fingerprint:
            return Vote.query.filter_by(finding_id=finding_id, vote_type="confirmed").count()
        return Vote.query.filter(
            Vote.finding_id == finding_id,
            Vote.vote_type == "confirmed",
            Vote.fingerprint != creator_fingerprint,
        ).count()

    @staticmethod
    def create(finding_id, fingerprint, vote_type):
        vote = Vote(finding_id=finding_id, fingerprint=fingerprint, vote_type=vote_type)
        db.session.add(vote)
        db.session.commit()
        return vote
