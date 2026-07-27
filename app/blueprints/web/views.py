from flask import render_template
from app.repositories.finding_repository import FindingRepository
from app.repositories.category_repository import CategoryRepository


@web_bp.route("/")
def index():
    total = FindingRepository.count_published()
    categories = CategoryRepository.get_all()
    return render_template("index.html", total_findings=total, categories=categories)


@web_bp.route("/finding/<finding_id>")
def finding_detail(finding_id):
    finding = FindingRepository.get_by_id(finding_id)
    if not finding:
        return render_template("errors/404.html"), 404
    return render_template("finding_detail.html", finding=finding)


@web_bp.route("/privacy")
def privacy():
    return render_template("privacy.html")


@web_bp.route("/noscript")
def noscript():
    total = FindingRepository.count_published()
    return render_template("noscript.html", total_findings=total)
