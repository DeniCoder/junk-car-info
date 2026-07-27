from app.extensions import db
from app.models.report import Report
from app.models.finding import Finding


class ReportRepository:

    @staticmethod
    def create(report):
        db.session.add(report)
        db.session.commit()
        return report

    @staticmethod
    def get_by_finding(finding_id):
        return Report.query.filter_by(finding_id=finding_id).all()

    @staticmethod
    def count_for_finding(finding_id):
        return Report.query.filter_by(finding_id=finding_id).count()

    @staticmethod
    def get_all(page=1, per_page=20):
        return Report.query.order_by(Report.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
