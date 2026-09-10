from flask import request, session, redirect, url_for, render_template, current_app, send_file, abort
from sqlalchemy import func

from app.blueprints.admin import admin_bp
from app.extensions import db, AdminRateLimiter
from app.models.finding import Finding
from app.models.category import Category
from app.models.site_content import SiteContent


def check_admin():
    token = session.get("admin_token")
    if not token or token != current_app.config.get("ADMIN_TOKEN"):
        return False
    return True


@admin_bp.route("/login", methods=["GET", "POST"])
@AdminRateLimiter.limit_login_attempts
@AdminRateLimiter.reset_on_success
def login():
    if request.method == "POST":
        token = request.form.get("token", "")
        if token and token == current_app.config.get("ADMIN_TOKEN"):
            session["admin_token"] = token
            return redirect(url_for("admin.dashboard"))
        error = request.args.get("error") or "Invalid token"
        return render_template("admin/login.html", error=error)
    error = request.args.get("error")
    return render_template("admin/login.html", error=error)


@admin_bp.route("/logout")
def logout():
    session.pop("admin_token", None)
    return redirect(url_for("admin.login"))


@admin_bp.route("/")
def dashboard():
    if not check_admin():
        return redirect(url_for("admin.login"))

    total = Finding.query.count()
    published = Finding.query.filter_by(status="published").count()
    hidden = Finding.query.filter_by(status="hidden").count()
    rejected = Finding.query.filter_by(status="rejected").count()

    by_category = db.session.query(
        Category.title, func.count(Finding.id)
    ).join(Finding, Finding.category_id == Category.id
    ).group_by(Category.title).all()

    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    recent_count = Finding.query.filter(Finding.created_at >= thirty_days_ago).count()

    return render_template("admin/dashboard.html",
        total=total, published=published, hidden=hidden, rejected=rejected,
        by_category=by_category, recent_count=recent_count)


@admin_bp.route("/reports")
def reports():
    if not check_admin():
        return redirect(url_for("admin.login"))

    category_id = request.args.get("category_id", type=int)
    status = request.args.get("status", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    search = request.args.get("search", "")
    page = request.args.get("page", 1, type=int)

    q = Finding.query

    if category_id:
        q = q.filter_by(category_id=category_id)
    if status:
        q = q.filter_by(status=status)
    if date_from:
        try:
            q = q.filter(Finding.created_at >= datetime.strptime(date_from, "%Y-%m-%d"))
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            q = q.filter(Finding.created_at <= dt)
        except ValueError:
            pass
    if search:
        q = q.filter(Finding.location_name.ilike(f"%{search}%"))

    pagination = q.order_by(Finding.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    categories = Category.query.all()

    return render_template("admin/reports.html",
        findings=pagination.items, pagination=pagination, categories=categories,
        filtered_total=pagination.total,
        f_category_id=category_id or "", f_status=status,
        f_date_from=date_from, f_date_to=date_to, f_search=search)


@admin_bp.route("/reports/pdf")
def reports_pdf():
    if not check_admin():
        return redirect(url_for("admin.login"))

    category_id = request.args.get("category_id", type=int)
    status = request.args.get("status", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    search = request.args.get("search", "")

    q = Finding.query
    if category_id:
        q = q.filter_by(category_id=category_id)
    if status:
        q = q.filter_by(status=status)
    if date_from:
        try:
            q = q.filter(Finding.created_at >= datetime.strptime(date_from, "%Y-%m-%d"))
        except ValueError:
            pass
    if date_to:
        try:
            q = q.filter(Finding.created_at <= datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59))
        except ValueError:
            pass
    if search:
        q = q.filter(Finding.location_name.ilike(f"%{search}%"))

    findings = q.order_by(Finding.created_at.desc()).all()

    from fpdf import FPDF
    from fpdf.enums import XPos, YPos
    from io import BytesIO
    import os

    pdf = FPDF(orientation="L", format="A4")

    font_path = os.path.join("C:", os.sep, "Windows", "Fonts", "arial.ttf")
    font_bold = os.path.join("C:", os.sep, "Windows", "Fonts", "arialbd.ttf")
    if os.path.exists(font_path):
        pdf.add_font("Arial", "", font_path, uni=True)
        if os.path.exists(font_bold):
            pdf.add_font("Arial", "B", font_bold, uni=True)
        else:
            pdf.add_font("Arial", "B", font_path, uni=True)
        font_family = "Arial"
    else:
        font_family = "Helvetica"

    pdf.add_page()
    pdf.set_font(font_family, "B", 16)
    pdf.cell(0, 12, "Junk Car Info — Отчёт", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font(font_family, "", 10)
    pdf.cell(0, 8, f"Всего находок: {len(findings)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    pdf.set_font(font_family, "B", 8)
    headers = ["ID", "Категория", "Место", "Статус", "Дата", "Жалоб"]
    widths = [35, 40, 100, 30, 35, 25]
    for i, h in enumerate(headers):
        pdf.cell(widths[i], 8, h, border=1)
    pdf.ln()

    pdf.set_font(font_family, "", 7)
    for f in findings:
        cat = db.session.get(Category, f.category_id)
        cat_name = cat.title[:15] if cat else "N/A"
        loc = (f.location_name or "-")[:40]
        date_str = f.created_at.strftime("%d.%m.%Y") if f.created_at else "-"
        row = [f.id[:12], cat_name, loc, f.status, date_str, str(f.reports_count or 0)]
        for i, val in enumerate(row):
            pdf.cell(widths[i], 6, val, border=1)
        pdf.ln()

    output = BytesIO()
    output.write(pdf.output())
    output.seek(0)

    return send_file(output, mimetype="application/pdf",
                     as_attachment=True, download_name="findings_report.pdf")


@admin_bp.route("/content/<slug>", methods=["GET", "POST"])
def edit_content(slug):
    if not check_admin():
        return redirect(url_for("admin.login"))

    page = db.session.get(SiteContent, slug)
    if not page:
        abort(404)

    if request.method == "POST":
        page.title = request.form.get("title", page.title)
        page.content_md = request.form.get("content_md", page.content_md)
        db.session.commit()
        return redirect(url_for("admin.edit_content", slug=slug))

    return render_template("admin/edit_content.html", page=page)


@admin_bp.route("/finding/<finding_id>/delete", methods=["POST"])
def delete(finding_id):
    if not check_admin():
        return redirect(url_for("admin.login"))

    from app.services.finding_service import FindingService
    FindingService.delete_finding(finding_id)
    return redirect(url_for("admin.reports"))
