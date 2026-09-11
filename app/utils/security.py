import hashlib
import os
import secrets

from flask import session, request


_csrf_tokens = {}


def generate_token():
    return secrets.token_urlsafe(32)


def hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_token(token, token_hash):
    return hash_token(token) == token_hash


def generate_csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = generate_token()
    return session["_csrf_token"]


def validate_csrf_token():
    # Keep compatibility with the field name used by the authentication forms.
    token = (
        request.form.get("_csrf_token")
        or request.form.get("csrf_token")
        or request.headers.get("X-CSRF-Token")
    )
    if not token or token != session.get("_csrf_token"):
        return False
    return True


def csrf_init(app):
    app.jinja_env.globals["csrf_token"] = generate_csrf_token
