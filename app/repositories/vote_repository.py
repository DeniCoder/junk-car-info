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
    def count_by_type(finding_id, trusted_only=False):
        query = Vote.query.filter_by(finding_id=finding_id)
        if trusted_only:
            query = query.filter_by(is_trusted=True)
        confirmed = query.filter_by(vote_type="confirmed").count()
        removed = query.filter_by(vote_type="removed").count()
        return confirmed, removed

    @staticmethod
    def count_confirmed_excluding_creator(finding_id, creator_fingerprint, trusted_only=False):
        query = Vote.query.filter(
            Vote.finding_id == finding_id,
            Vote.vote_type == "confirmed",
        )
        if creator_fingerprint:
            query = query.filter(Vote.fingerprint != creator_fingerprint)
        if trusted_only:
            query = query.filter(Vote.is_trusted == True)
        return query.count()

    @staticmethod
    def count_votes_in_window(finding_id, vote_type, window_minutes=60):
        """Count votes of a specific type within a time window to detect suspicious activity."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        return Vote.query.filter(
            Vote.finding_id == finding_id,
            Vote.vote_type == vote_type,
            Vote.created_at > cutoff,
        ).count()

    @staticmethod
    def create(finding_id, fingerprint, vote_type, is_trusted=False):
        vote = Vote(finding_id=finding_id, fingerprint=fingerprint, vote_type=vote_type, is_trusted=is_trusted)
        db.session.add(vote)
        db.session.commit()
        return vote
