from flask import Blueprint, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from ..auth import login_required, make_token, public_user
from ..db import execute, now, query_one

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

SELF_ROLES = {"kid", "parent", "teacher", "creator"}


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = data.get("role") if data.get("role") in SELF_ROLES else "kid"
    if not name or "@" not in email or len(password) < 6:
        return jsonify(error="Name, a valid email and a password of 6+ characters are required"), 400
    if query_one("SELECT id FROM users WHERE email=?", (email,)):
        return jsonify(error="This email is already registered"), 409
    uid = execute(
        "INSERT INTO users(name,email,password_hash,role,emoji,status,created) VALUES(?,?,?,?,?,?,?)",
        (name, email, generate_password_hash(password), role, data.get("emoji") or "🐻", "active", now()),
    )
    user = query_one("SELECT * FROM users WHERE id=?", (uid,))
    return jsonify(token=make_token(uid), user=public_user(user)), 201


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    user = query_one("SELECT * FROM users WHERE email=?", (email,))
    if not user or not check_password_hash(user["password_hash"], data.get("password") or ""):
        return jsonify(error="Wrong email or password"), 401
    if user["status"] != "active":
        return jsonify(error="This account is suspended"), 403
    return jsonify(token=make_token(user["id"]), user=public_user(user))


@bp.get("/me")
@login_required()
def me():
    return jsonify(user=public_user(g.user))


@bp.put("/me")
@login_required()
def update_me():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or g.user["name"]).strip()
    emoji = data.get("emoji") or g.user["emoji"]
    execute("UPDATE users SET name=?, emoji=? WHERE id=?", (name, emoji, g.user["id"]))
    if data.get("password"):
        if len(data["password"]) < 6:
            return jsonify(error="Password must be 6+ characters"), 400
        execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(data["password"]), g.user["id"]))
    return jsonify(user=public_user(query_one("SELECT * FROM users WHERE id=?", (g.user["id"],))))
