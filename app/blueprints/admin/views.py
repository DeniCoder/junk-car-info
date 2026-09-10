from flask import request, session, redirect, url_for, render_template, current_app, send_file, abort, jsonify
from datetime import datetime, timezone, timedelta
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
    per_page = request.args.get("per_page", 20, type=int)

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

    pagination = q.order_by(Finding.created_at.desc()).paginate(page=page, per_page=min(per_page, 100), error_out=False)
    categories = Category.query.all()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        findings_data = []
        for f in pagination.items:
            cat_title = f.category.title if f.category else "—"
            thumb_url = f.photos.first().thumb_url if f.photos.first() else None
            findings_data.append({
                "id": f.id,
                "short_id": f.id[:8],
                "category": cat_title,
                "location_name": f.location_name or "—",
                "status": f.status,
                "created_at": f.created_at.strftime('%d.%m.%Y %H:%M') if f.created_at else "—",
                "reports_count": f.reports_count or 0,
                "thumb_url": thumb_url,
                "detail_url": url_for('finding_detail', finding_id=f.id),
            })
        return jsonify({
            "findings": findings_data,
            "total": pagination.total,
            "page": pagination.page,
            "pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
        })

    return render_template("admin/reports.html",
        findings=pagination.items, pagination=pagination, categories=categories,
        filtered_total=pagination.total,
        f_category_id=category_id or "", f_status=status,
        f_date_from=date_from, f_date_to=date_to, f_search=search,
        current_per_page=per_page)


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
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"status": "deleted", "finding_id": finding_id})
    
    return redirect(url_for("admin.reports"))


@admin_bp.route("/finding/<finding_id>/toggle_status", methods=["POST"])
def toggle_status(finding_id):
    """Admin endpoint to manually change finding status (publish/hide/reject)."""
    if not check_admin():
        return redirect(url_for("admin.login"))
    
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    
    if new_status not in ["published", "hidden", "rejected", "pending"]:
        return jsonify({"error": "invalid status"}), 400
    
    finding = Finding.query.get(finding_id)
    if not finding:
        return jsonify({"error": "not found"}), 404
    
    old_status = finding.status
    finding.status = new_status
    if new_status == "published" and not finding.published_at:
        finding.published_at = datetime.now(timezone.utc)
    elif new_status in ["hidden", "rejected"] and not finding.hidden_at:
        finding.hidden_at = datetime.now(timezone.utc)
    
    db.session.commit()
    
    # Log action for audit trail (could be extended with full logging system)
    current_app.logger.info(f"Admin changed finding {finding_id} status from {old_status} to {new_status}")
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            "status": "success",
            "finding_id": finding_id,
            "old_status": old_status,
            "new_status": new_status
        })
    
    return redirect(url_for("admin.reports"))


@admin_bp.route("/stats", methods=["GET"])
def stats():
    """Enhanced statistics endpoint with detailed breakdown."""
    if not check_admin():
        return redirect(url_for("admin.login"))
    
    # Total counts by status
    total = Finding.query.count()
    status_counts = db.session.query(
        Finding.status, func.count(Finding.id)
    ).group_by(Finding.status).all()
    
    # Recent activity (last 7 days)
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_findings = Finding.query.filter(Finding.created_at >= seven_days_ago).count()
    
    # By category breakdown
    by_category = db.session.query(
        Category.id, Category.title, func.count(Finding.id)
    ).join(Finding, Finding.category_id == Category.id
    ).group_by(Category.id, Category.title).all()
    
    # Status trend (last 14 days)
    fourteen_days_ago = datetime.now(timezone.utc) - timedelta(days=14)
    daily_stats = db.session.query(
        func.date(Finding.created_at), Finding.status, func.count(Finding.id)
    ).filter(Finding.created_at >= fourteen_days_ago
    ).group_by(func.date(Finding.created_at), Finding.status).order_by(func.date(Finding.created_at)).all()
    
    # Top reported findings
    top_reported = Finding.query.order_by(Finding.reports_count.desc()).limit(10).all()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            "total": total,
            "by_status": {status: count for status, count in status_counts},
            "recent_7days": recent_findings,
            "by_category": [{"id": c[0], "title": c[1], "count": c[2]} for c in by_category],
            "daily_trend": [{"date": str(d), "status": s, "count": c} for d, s, c in daily_stats],
            "top_reported": [{"id": f.id, "location": f.location_name, "reports": f.reports_count} for f in top_reported],
        })
    
    return render_template("admin/stats.html",
        total=total,
        by_status=dict(status_counts),
        recent_7days=recent_findings,
        by_category=by_category,
        daily_stats=daily_stats,
        top_reported=top_reported)
