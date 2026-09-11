from flask import render_template, current_app, request, session, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.blueprints.web import web_bp
from app.repositories.finding_repository import FindingRepository
from app.repositories.category_repository import CategoryRepository
from app.models.site_content import SiteContent
from app.models.user import User
from app.models.notification import Notification
from app.models.appeal import Appeal
from app.extensions import db
from functools import wraps

# Поддерживаемые языки
SUPPORTED_LANGUAGES = {
    'ru': 'Русский',
    'en': 'English',
    'zh': '中文',
    'es': 'Español'
}


@web_bp.before_app_request
def load_language():
    """Загрузка языка из cookie или session"""
    if 'language' not in session:
        lang = request.cookies.get('language')
        if lang and lang in SUPPORTED_LANGUAGES:
            session['language'] = lang
        else:
            # Определяем язык браузера
            browser_lang = request.accept_languages.best_match(SUPPORTED_LANGUAGES.keys())
            session['language'] = browser_lang or 'ru'


@web_bp.route("/set-language/<lang_code>")
def set_language(lang_code):
    """Установка языка пользователя"""
    if lang_code in SUPPORTED_LANGUAGES:
        session['language'] = lang_code
        # Сохраняем в cookie на 1 год
        response = redirect(request.referrer or url_for('web.index'))
        response.set_cookie('language', lang_code, max_age=31536000)
        return response
    return redirect(url_for('web.index'))


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
    """Политика конфиденциальности - редирект на русскую версию"""
    return redirect(url_for('web.privacy_ru'))


@web_bp.route("/privacy/ru")
def privacy_ru():
    """Политика конфиденциальности для РФ (152-ФЗ)"""
    return render_template("legal/privacy_ru.html")


@web_bp.route("/privacy/en")
def privacy_en():
    """Privacy Policy for EU/International (GDPR)"""
    return render_template("legal/privacy_en.html")


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


@web_bp.route("/profile")
@login_required
def profile():
    user = current_user
    user_findings = user.findings.order_by(User.findings.property.columns[0].desc()).all()
    notifications = user.notifications.limit(20).all()
    unread_count = Notification.query.filter_by(user_id=user.id, is_read=False).count()
    
    return render_template("profile.html", 
                          user=user, 
                          findings=user_findings, 
                          notifications=notifications,
                          unread_count=unread_count)


@web_bp.route("/notifications/mark-read/<int:notif_id>", methods=["POST"])
@login_required
def mark_notification_read(notif_id):
    notification = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first()
    if notification:
        notification.is_read = True
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False}), 404


@web_bp.route("/notifications/mark-all-read", methods=["POST"])
@login_required
def mark_all_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"success": True})


@web_bp.route("/appeal/submit/<finding_id>", methods=["POST"])
@login_required
def submit_appeal(finding_id):
    finding = FindingRepository.get_by_id(finding_id)
    if not finding:
        return jsonify({"error": "Объект не найден"}), 404
    
    reason = request.form.get("reason", "").strip()
    if not reason:
        flash("Укажите причину апелляции.", "error")
        return redirect(url_for('web.profile'))
    
    existing_appeal = Appeal.query.filter_by(finding_id=finding_id, user_id=current_user.id, status='pending').first()
    if existing_appeal:
        flash("У вас уже есть ожидающая рассмотрения апелляция для этого объекта.", "warning")
        return redirect(url_for('web.profile'))
    
    appeal = Appeal(
        user_id=current_user.id,
        finding_id=finding_id,
        reason=reason
    )
    db.session.add(appeal)
    
    notification = Notification(
        user_id=current_user.id,
        title="Апелляция подана",
        message=f"Ваша апелляция для объекта {finding.location_name} принята на рассмотрение.",
        notification_type="info",
        related_finding_id=finding_id
    )
    db.session.add(notification)
    
    db.session.commit()
    flash("Апелляция успешно подана.", "success")
    return redirect(url_for('web.profile'))


@web_bp.route("/privacy-policy")
def privacy_policy():
    """Политика конфиденциальности (152-ФЗ РФ) - редирект"""
    return redirect(url_for('web.privacy_ru'))


@web_bp.route("/terms")
def terms():
    """Условия использования - редирект"""
    return redirect(url_for('web.terms_ru'))


@web_bp.route("/terms/ru")
def terms_ru():
    """Условия использования для РФ"""
    return render_template("legal/terms_ru.html")


@web_bp.route("/cookie-policy")
def cookie_policy():
    """Политика использования cookie"""
    # Временная заглушка, будет создан отдельный файл
    return render_template("legal/cookie_policy.html")
