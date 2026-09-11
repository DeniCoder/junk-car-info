from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from . import user_bp
from app import db
from app.models.finding import Finding
from app.models.appeal import Appeal
from app.models.notification import Notification
from app.utils.security import validate_csrf_token

@user_bp.route('/profile')
@login_required
def profile():
    """Личный кабинет пользователя - список жалоб"""
    findings = Finding.query.filter_by(user_id=current_user.id).order_by(Finding.created_at.desc()).all()
    
    # Подсчет непрочитанных уведомлений
    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    
    return render_template('user/profile.html', findings=findings, unread_count=unread_count)

@user_bp.route('/notifications')
@login_required
def notifications():
    """Страница уведомлений"""
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    
    return render_template('user/notifications.html', notifications=notifications, unread_count=unread_count)

@user_bp.route('/notifications/mark-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Отметить уведомление как прочитанное"""
    if not validate_csrf_token():
        flash('Invalid CSRF token. Refresh the page and try again.', 'danger')
        return redirect(url_for('user.notifications'))
    notification = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first_or_404()
    notification.is_read = True
    db.session.commit()
    return redirect(url_for('user.notifications'))

@user_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Отметить все уведомления как прочитанные"""
    if not validate_csrf_token():
        flash('Invalid CSRF token. Refresh the page and try again.', 'danger')
        return redirect(url_for('user.notifications'))
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return redirect(url_for('user.notifications'))

@user_bp.route('/findings/<finding_id>/appeal', methods=['POST'])
@login_required
def submit_appeal(finding_id):
    """Подать апелляцию на решение по жалобе"""
    if not validate_csrf_token():
        flash('Invalid CSRF token. Refresh the page and try again.', 'danger')
        return redirect(url_for('user.profile'))
    finding = Finding.query.filter_by(id=finding_id, user_id=current_user.id).first_or_404()
    
    if finding.status not in ['rejected', 'hidden']:
        flash('Апелляцию можно подать только на отклоненные или скрытые жалобы.', 'warning')
        return redirect(url_for('user.profile'))
    
    if Appeal.query.filter_by(finding_id=finding.id, user_id=current_user.id, status='pending').first():
        flash('Апелляция уже подана для этой жалобы.', 'warning')
        return redirect(url_for('user.profile'))
    
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('Необходимо указать причину апелляции.', 'danger')
        return redirect(url_for('user.profile'))
    
    appeal = Appeal(
        finding_id=finding.id,
        user_id=current_user.id,
        reason=reason,
        status='pending'
    )
    
    db.session.add(appeal)
    db.session.commit()
    
    flash('Апелляция успешно подана и ожидает рассмотрения.', 'success')
    return redirect(url_for('user.profile'))
