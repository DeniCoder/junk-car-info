from flask import request, session, redirect, url_for, render_template, current_app, send_file, abort, jsonify, flash
from datetime import datetime, timezone, timedelta
from sqlalchemy import func
import json

from app.blueprints.admin import admin_bp
from app.extensions import db, AdminRateLimiter
from app.models.finding import Finding
from app.models.category import Category
from app.models.site_content import SiteContent
from app.models.user import User
from app.models.notification import Notification
from app.models.appeal import Appeal
from app.models.audit_log import AuditLog


def check_admin():
    # Check for legacy admin token OR new user-based admin
    if session.get("admin_token") and session.get("admin_token") == current_app.config.get("ADMIN_TOKEN"):
        return True
    from flask_login import current_user
    if current_user.is_authenticated and current_user.is_admin:
        return True
    if session.get('user_id'):
        user = User.query.get(session['user_id'])
        if user and user.is_admin:
            return True
    return False


def get_current_admin_user():
    """Get the current admin user object for audit logging."""
    from flask_login import current_user
    if current_user.is_authenticated and current_user.is_admin:
        return current_user
    if session.get('user_id'):
        return User.query.get(session['user_id'])
    return None


def log_admin_action(action, entity_type, entity_id, old_value=None, new_value=None):
    """Log admin action to audit trail."""
    admin_user = get_current_admin_user()
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')[:512]
    
    audit_entry = AuditLog(
        admin_user_id=admin_user.id if admin_user else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=json.dumps(old_value) if old_value else None,
        new_value=json.dumps(new_value) if new_value else None,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.session.add(audit_entry)
    try:
        db.session.commit()
    except:
        db.session.rollback()


@admin_bp.route("/login", methods=["GET", "POST"])
@AdminRateLimiter.limit_login_attempts
@AdminRateLimiter.reset_on_success
def login():
    from flask_login import current_user

    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin.dashboard"))
        flash("This account does not have administrator access.", "error")
        return redirect(url_for("web.index"))

    # Administration uses the regular account login rather than a separate
    # shared token, so the access path is consistent for every user.
    return redirect(url_for("auth.login", next=url_for("admin.dashboard")))


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
    admin_comment = data.get("admin_comment", "")
    
    if new_status not in ["published", "hidden", "rejected", "pending", "hidden_pending"]:
        return jsonify({"error": "invalid status"}), 400
    
    finding = Finding.query.get(finding_id)
    if not finding:
        return jsonify({"error": "not found"}), 404
    
    old_status = finding.status
    old_data = {"status": old_status}
    
    finding.status = new_status
    if new_status == "published" and not finding.published_at:
        finding.published_at = datetime.now(timezone.utc)
    elif new_status in ["hidden", "rejected", "hidden_pending"] and not finding.hidden_at:
        finding.hidden_at = datetime.now(timezone.utc)
    
    # If hiding with comment, create notification for user
    if new_status in ["hidden", "rejected"] and finding.user_id and admin_comment:
        notification = Notification(
            user_id=finding.user_id,
            title="Статус жалобы изменён",
            message=f"Ваша жалоба '{finding.location_name}' была {new_status}. Комментарий администратора: {admin_comment}",
            notification_type="warning",
            related_finding_id=finding.id
        )
        db.session.add(notification)
    
    db.session.commit()
    
    # Log action for audit trail
    log_admin_action(
        action="status_change",
        entity_type="finding",
        entity_id=finding_id,
        old_value=old_data,
        new_value={"status": new_status, "admin_comment": admin_comment}
    )
    
    current_app.logger.info(f"Admin changed finding {finding_id} status from {old_status} to {new_status}")
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            "status": "success",
            "finding_id": finding_id,
            "old_status": old_status,
            "new_status": new_status
        })
    
    flash(f"Статус изменён на {new_status}", "success")
    return redirect(url_for("admin.reports"))


@admin_bp.route("/appeals")
def appeals_list():
    """List all appeals pending review."""
    if not check_admin():
        return redirect(url_for("admin.login"))
    
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    status_filter = request.args.get("status", "pending")
    
    q = Appeal.query
    if status_filter:
        q = q.filter_by(status=status_filter)
    
    pagination = q.order_by(Appeal.created_at.desc()).paginate(page=page, per_page=min(per_page, 100), error_out=False)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        appeals_data = []
        for appeal in pagination.items:
            finding = Finding.query.get(appeal.finding_id)
            user = User.query.get(appeal.user_id)
            appeals_data.append({
                "id": appeal.id,
                "finding_id": appeal.finding_id,
                "location_name": finding.location_name if finding else "N/A",
                "username": user.username if user else "Unknown",
                "reason": appeal.reason,
                "status": appeal.status,
                "created_at": appeal.created_at.strftime('%d.%m.%Y %H:%M') if appeal.created_at else "—",
            })
        return jsonify({
            "appeals": appeals_data,
            "total": pagination.total,
            "page": pagination.page,
            "pages": pagination.pages,
        })
    
    return render_template("admin/appeals.html", 
                          appeals=pagination.items, 
                          pagination=pagination,
                          current_status=status_filter)


@admin_bp.route("/appeal/<int:appeal_id>/review", methods=["POST"])
def review_appeal(appeal_id):
    """Review an appeal and make a decision."""
    if not check_admin():
        return redirect(url_for("admin.login"))
    
    appeal = Appeal.query.get(appeal_id)
    if not appeal:
        return jsonify({"error": "not found"}), 404
    
    data = request.get_json(silent=True) or {}
    decision = data.get("decision")  # approve or reject
    admin_comment = data.get("admin_comment", "")
    
    if decision not in ["approve", "reject"]:
        return jsonify({"error": "invalid decision"}), 400
    
    old_status = appeal.status
    appeal.status = "approved" if decision == "approve" else "rejected"
    appeal.admin_comment = admin_comment
    appeal.reviewed_by = get_current_admin_user().id if get_current_admin_user() else None
    appeal.reviewed_at = datetime.now(timezone.utc)
    
    # If approved, restore the finding
    if decision == "approve":
        finding = Finding.query.get(appeal.finding_id)
        if finding:
            finding.status = "published"
            finding.is_archived = False
            notification_msg = f"Ваша апелляция по объекту '{finding.location_name}' одобрена. Объект восстановлен."
        else:
            notification_msg = f"Ваша апелляция одобрена."
    else:
        finding = Finding.query.get(appeal.finding_id)
        notification_msg = f"Ваша апелляция по объекту '{finding.location_name if finding else ''}' отклонена. Комментарий: {admin_comment}"
    
    # Notify user
    if appeal.user_id:
        notification = Notification(
            user_id=appeal.user_id,
            title="Решение по апелляции",
            message=notification_msg,
            notification_type="success" if decision == "approve" else "warning",
            related_finding_id=appeal.finding_id
        )
        db.session.add(notification)
    
    db.session.commit()
    
    # Log action
    log_admin_action(
        action="appeal_review",
        entity_type="appeal",
        entity_id=str(appeal_id),
        old_value={"status": old_status},
        new_value={"status": appeal.status, "decision": decision, "admin_comment": admin_comment}
    )
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            "status": "success",
            "appeal_id": appeal_id,
            "decision": decision
        })
    
    flash(f"Апелляция {decision}d", "success")
    return redirect(url_for("admin.appeals_list"))


@admin_bp.route("/audit-logs")
def audit_logs():
    """View audit logs of admin actions."""
    if not check_admin():
        return redirect(url_for("admin.login"))
    
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    action_filter = request.args.get("action", "")
    entity_type_filter = request.args.get("entity_type", "")
    
    q = AuditLog.query
    if action_filter:
        q = q.filter_by(action=action_filter)
    if entity_type_filter:
        q = q.filter_by(entity_type=entity_type_filter)
    
    pagination = q.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=min(per_page, 100), error_out=False)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        logs_data = []
        for log in pagination.items:
            admin = User.query.get(log.admin_user_id) if log.admin_user_id else None
            logs_data.append({
                "id": log.id,
                "admin_username": admin.username if admin else "System",
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "ip_address": log.ip_address,
                "created_at": log.created_at.strftime('%d.%m.%Y %H:%M:%S') if log.created_at else "—",
            })
        return jsonify({
            "logs": logs_data,
            "total": pagination.total,
            "page": pagination.page,
            "pages": pagination.pages,
        })
    
    return render_template("admin/audit_logs.html", 
                          logs=pagination.items, 
                          pagination=pagination,
                          current_action=action_filter,
                          current_entity_type=entity_type_filter)


@admin_bp.route("/reports/csv")
def reports_csv():
    """Export findings to CSV."""
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
    
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Категория", "Место", "Статус", "Дата создания", "Жалоб", "Координаты"])
    
    for f in findings:
        cat = db.session.get(Category, f.category_id)
        cat_name = cat.title if cat else "N/A"
        writer.writerow([
            f.id,
            cat_name,
            f.location_name or "-",
            f.status,
            f.created_at.strftime("%d.%m.%Y %H:%M") if f.created_at else "-",
            f.reports_count or 0,
            f"{f.lat}, {f.lon}"
        ])
    
    output.seek(0)
    
    return send_file(
        output.getvalue().encode('utf-8-sig'),
        mimetype="text/csv",
        as_attachment=True,
        download_name="findings_export.csv"
    )


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
