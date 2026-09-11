from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

db = SQLAlchemy()
migrate = Migrate()
limiter = Limiter(key_func=get_remote_address)
talisman = Talisman()


class AdminRateLimiter:
    """Rate limiter for admin actions to prevent brute force attacks."""
    
    @staticmethod
    def limit_login_attempts(f):
        from functools import wraps
        from flask import request, current_app, session, redirect, url_for
        from datetime import datetime, timedelta, timezone
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method == "POST":
                key = f"admin_login_attempts_{request.remote_addr}"
                attempts = session.get(key, {"count": 0, "locked_until": None})
                
                if attempts.get("locked_until"):
                    locked_until = datetime.fromisoformat(attempts["locked_until"])
                    if datetime.now(timezone.utc) < locked_until:
                        remaining = (locked_until - datetime.now(timezone.utc)).seconds // 60
                        return redirect(url_for("admin.login", error=f"Слишком много попыток. Попробуйте через {remaining} мин."))
                    else:
                        session[key] = {"count": 0, "locked_until": None}
                        attempts = session[key]
                
                attempts["count"] = attempts.get("count", 0) + 1
                
                if attempts["count"] > 5:
                    attempts["locked_until"] = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
                    session[key] = attempts
                    return redirect(url_for("admin.login", error="Слишком много попыток. Доступ заблокирован на 15 минут."))
                
                session[key] = attempts
            
            return f(*args, **kwargs)
        return decorated_function
    
    @staticmethod
    def reset_on_success(f):
        from functools import wraps
        from flask import request, session
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            result = f(*args, **kwargs)
            if request.method == "POST" and result.status_code == 302:
                key = f"admin_login_attempts_{request.remote_addr}"
                session.pop(key, None)
            return result
        return decorated_function
