from flask import render_template, current_app, request, session, redirect, url_for, flash, jsonify
from app.blueprints.web import web_bp
from app.repositories.finding_repository import FindingRepository
from app.repositories.category_repository import CategoryRepository
from app.models.site_content import SiteContent
from app.models.user import User
from app.models.notification import Notification
from app.models.appeal import Appeal
from app.extensions import db
from functools import wraps


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите для доступа к этой странице.', 'warning')
            return redirect(url_for('web.login'))
        return f(*args, **kwargs)
    return decorated_function


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


@web_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        if not username or not password:
            flash("Введите имя пользователя и пароль.", "error")
            return render_template("login.html")
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password) and user.is_active:
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            from datetime import datetime
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash(f"Добро пожаловать, {user.username}!", "success")
            next_page = request.args.get('next')
            return redirect(next_page or url_for('web.profile'))
        else:
            flash("Неверное имя пользователя или пароль.", "error")
    
    return render_template("login.html")


@web_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        if not username or not email or not password:
            flash("Все поля обязательны для заполнения.", "error")
            return render_template("register.html")
        
        if password != confirm_password:
            flash("Пароли не совпадают.", "error")
            return render_template("register.html")
        
        if len(password) < 6:
            flash("Пароль должен быть не менее 6 символов.", "error")
            return render_template("register.html")
        
        if User.query.filter_by(username=username).first():
            flash("Имя пользователя уже занято.", "error")
            return render_template("register.html")
        
        if User.query.filter_by(email=email).first():
            flash("Email уже зарегистрирован.", "error")
            return render_template("register.html")
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash("Регистрация успешна! Теперь вы можете войти.", "success")
        return redirect(url_for('web.login'))
    
    return render_template("register.html")


@web_bp.route("/logout")
def logout():
    session.clear()
    flash("Вы вышли из системы.", "info")
    return redirect(url_for('web.index'))


@web_bp.route("/profile")
@login_required
def profile():
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('web.login'))
    
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
    notification = Notification.query.filter_by(id=notif_id, user_id=session['user_id']).first()
    if notification:
        notification.is_read = True
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False}), 404


@web_bp.route("/notifications/mark-all-read", methods=["POST"])
@login_required
def mark_all_notifications_read():
    Notification.query.filter_by(user_id=session['user_id'], is_read=False).update({"is_read": True})
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
    
    existing_appeal = Appeal.query.filter_by(finding_id=finding_id, user_id=session['user_id'], status='pending').first()
    if existing_appeal:
        flash("У вас уже есть ожидающая рассмотрения апелляция для этого объекта.", "warning")
        return redirect(url_for('web.profile'))
    
    appeal = Appeal(
        user_id=session['user_id'],
        finding_id=finding_id,
        reason=reason
    )
    db.session.add(appeal)
    
    notification = Notification(
        user_id=session['user_id'],
        title="Апелляция подана",
        message=f"Ваша апелляция для объекта {finding.location_name} принята на рассмотрение.",
        notification_type="info",
        related_finding_id=finding_id
    )
    db.session.add(notification)
    
    db.session.commit()
    flash("Апелляция успешно подана.", "success")
    return redirect(url_for('web.profile'))
