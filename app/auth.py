from functools import wraps

from flask import current_app, g, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .db import query_one

ROLE_RANK = {"kid": 0, "parent": 1, "teacher": 2, "creator": 2, "admin": 3, "super_admin": 4}


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="auth")


def make_token(user_id):
    return _serializer().dumps({"uid": user_id})


def read_token(token):
    try:
        return _serializer().loads(token, max_age=current_app.config["TOKEN_MAX_AGE"])["uid"]
    except (BadSignature, SignatureExpired, KeyError):
        return None


def public_user(row):
    if not row:
        return None
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"],
        "emoji": row["emoji"],
        "status": row["status"],
        "created": row["created"],
    }


def load_user():
    header = request.headers.get("Authorization", "")
    token = header[7:] if header.startswith("Bearer ") else request.args.get("token", "")
    g.user = None
    if token:
        uid = read_token(token)
        if uid:
            row = query_one("SELECT * FROM users WHERE id=?", (uid,))
            if row and row["status"] == "active":
                g.user = row
    return g.user


def login_required(role=None):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            user = load_user()
            if not user:
                return jsonify(error="Please sign in", status=401), 401
            if role and ROLE_RANK.get(user["role"], 0) < ROLE_RANK[role]:
                return jsonify(error="You do not have access to this", status=403), 403
            return fn(*a, **kw)

        return wrapper

    return deco


def optional_user(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        load_user()
        return fn(*a, **kw)

    return wrapper
