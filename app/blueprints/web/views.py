from flask import render_template, current_app, request
from app.blueprints.web import web_bp
from app.repositories.finding_repository import FindingRepository
from app.repositories.category_repository import CategoryRepository
from app.models.site_content import SiteContent


@web_bp.route("/")
def index():
    total = FindingRepository.count_published()
    categories = CategoryRepository.get_all()
    return render_template("index.html", total_findings=total, categories=categories,
                           config=current_app.config)


@web_bp.route("/finding/<finding_id>")
def finding_detail(finding_id):
    finding = FindingRepository.get_by_id(finding_id)
    if not finding:
        return render_template("errors/404.html"), 404
    return render_template("finding_detail.html", finding=finding)


@web_bp.route("/privacy")
def privacy():
    return render_template("privacy.html")


@web_bp.route("/contacts")
def contacts():
    page = SiteContent.query.filter_by(slug="contacts").first()
    return render_template("contacts.html", page=page)


@web_bp.route("/complaint")
def complaint():
    finding_id = request.args.get("finding_id", "")
    return render_template("complaint.html", finding_id=finding_id)


@web_bp.route("/noscript")
def noscript():
    total = FindingRepository.count_published()
    return render_template("noscript.html", total_findings=total)
