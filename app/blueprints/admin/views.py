from flask import Blueprint, request, session, redirect, url_for, render_template, current_app

admin_bp = Blueprint("admin", __name__, template_folder="../templates")


def check_admin():
    token = session.get("admin_token")
    if not token or token != current_app.config.get("ADMIN_TOKEN"):
        return False
    return True


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        token = request.form.get("token", "")
        if token and token == current_app.config.get("ADMIN_TOKEN"):
            session["admin_token"] = token
            return redirect(url_for("admin.dashboard"))
        return render_template("admin/login.html", error="Invalid token")
    return render_template("admin/login.html")


@admin_bp.route("/logout")
def logout():
    session.pop("admin_token", None)
    return redirect(url_for("admin.login"))


@admin_bp.route("/")
def dashboard():
    if not check_admin():
        return redirect(url_for("admin.login"))

    from app.repositories.finding_repository import FindingRepository
    from app.repositories.report_repository import ReportRepository

    page = request.args.get("page", 1, type=int)
    status_filter = request.args.get("status", "pending")

    if status_filter == "all":
        pagination = FindingRepository.get_by_status("pending", page=page)
        findings = []
        for s in ["pending", "published", "rejected", "removed", "hidden"]:
            p = FindingRepository.get_by_status(s, page=page, per_page=50)
            findings.extend(p.items)
    else:
        pagination = FindingRepository.get_by_status(status_filter, page=page)
        findings = pagination.items

    total_pending = FindingRepository.get_by_status("pending", per_page=10000).total

    return render_template(
        "admin/dashboard.html",
        findings=findings,
        pagination=pagination,
        status_filter=status_filter,
        total_pending=total_pending,
    )


@admin_bp.route("/finding/<finding_id>/<action>", methods=["POST"])
def moderate(finding_id, action):
    if not check_admin():
        return redirect(url_for("admin.login"))

    from app.services.finding_service import FindingService
    FindingService.moderate(finding_id, action)
    return redirect(url_for("admin.dashboard", status_filter=request.args.get("status_filter", "pending")))


@admin_bp.route("/finding/<finding_id>/delete", methods=["POST"])
def delete(finding_id):
    if not check_admin():
        return redirect(url_for("admin.login"))

    from app.services.finding_service import FindingService
    FindingService.delete_finding(finding_id)
    return redirect(url_for("admin.dashboard"))
