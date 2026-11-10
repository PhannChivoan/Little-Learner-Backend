import hashlib
import json
import os
import platform
import sys
import time
import uuid

from flask import Blueprint, current_app, g, jsonify, request, send_from_directory
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from .. import storage
from ..auth import ROLE_RANK, login_required, public_user
from ..db import execute, now, query, query_one

bp = Blueprint("admin", __name__, url_prefix="/api")

STARTED = time.time()

COLLECTIONS = {
    "templates": {"read": "creator", "write": "admin"},
    "themes": {"read": "creator", "write": "admin"},
    "assets": {"read": "creator", "write": "creator"},
    "moderation": {"read": "admin", "write": "admin"},
    "support": {"read": "admin", "write": "admin"},
    "announcements": {"read": "admin", "write": "admin"},
    "rewards": {"read": "admin", "write": "admin"},
    "billing": {"read": "admin", "write": "admin"},
    "reports": {"read": "admin", "write": "admin"},
    "i18n": {"read": "admin", "write": "admin"},
    "settings": {"read": "admin", "write": "admin"},
    "classes": {"read": "teacher", "write": "teacher"},
    "assignments": {"read": "teacher", "write": "teacher"},
    "collections": {"read": "creator", "write": "creator"},
}

ROLES = {"kid", "parent", "teacher", "creator", "admin", "super_admin"}


def allowed(coll, mode):
    spec = COLLECTIONS.get(coll)
    if not spec:
        return None
    return ROLE_RANK.get(g.user["role"], 0) >= ROLE_RANK[spec[mode]]


def doc_out(row):
    data = json.loads(row["data"])
    data["id"] = row["id"]
    data["created"] = row["created"]
    data["updated"] = row["updated"]
    return data


def paging(total):
    per = request.args.get("per", "")
    if not per.isdigit() or int(per) < 1:
        return 1, 0, 1
    per = min(int(per), 200)
    pages = max(1, -(-total // per))
    page = request.args.get("page", "1")
    page = min(max(int(page) if page.isdigit() else 1, 1), pages)
    return page, per, pages


def guard(coll, mode):
    ok = allowed(coll, mode)
    if ok is None:
        return jsonify(error="Unknown collection"), 404
    if not ok:
        return jsonify(error="You do not have access to this", status=403), 403
    return None


@bp.get("/admin/<coll>")
@login_required()
def list_docs(coll):
    denied = guard(coll, "read")
    if denied:
        return denied
    rows = query("SELECT * FROM docs WHERE coll=? ORDER BY id ASC", (coll,))
    items = [doc_out(r) for r in rows]
    q = (request.args.get("q") or "").strip().lower()
    if q:
        items = [i for i in items if q in json.dumps(i, ensure_ascii=False).lower()]
    for key, value in request.args.items():
        if key in ("q", "limit", "token", "page", "per", "order"):
            continue
        items = [i for i in items if str(i.get(key)).lower() == value.lower()]
    if request.args.get("order") == "desc":
        items.reverse()
    limit = request.args.get("limit")
    if limit and limit.isdigit():
        items = items[: int(limit)]
    total = len(items)
    page, per, pages = paging(total)
    if per:
        items = items[(page - 1) * per : page * per]
    return jsonify(items=items, total=total, page=page, pages=pages)


@bp.post("/admin/<coll>")
@login_required()
def create_doc(coll):
    denied = guard(coll, "write")
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    data = {k: v for k, v in data.items() if k not in ("id", "created", "updated")}
    stamp = now()
    did = execute("INSERT INTO docs(coll,data,created,updated) VALUES(?,?,?,?)", (coll, json.dumps(data, ensure_ascii=False), stamp, stamp))
    return jsonify(item=doc_out(query_one("SELECT * FROM docs WHERE id=?", (did,)))), 201


@bp.get("/admin/<coll>/<int:did>")
@login_required()
def get_doc(coll, did):
    denied = guard(coll, "read")
    if denied:
        return denied
    row = query_one("SELECT * FROM docs WHERE id=? AND coll=?", (did, coll))
    if not row:
        return jsonify(error="Not found"), 404
    return jsonify(item=doc_out(row))


@bp.route("/admin/<coll>/<int:did>", methods=["PUT", "PATCH"])
@login_required()
def update_doc(coll, did):
    denied = guard(coll, "write")
    if denied:
        return denied
    row = query_one("SELECT * FROM docs WHERE id=? AND coll=?", (did, coll))
    if not row:
        return jsonify(error="Not found"), 404
    data = request.get_json(silent=True) or {}
    current = json.loads(row["data"])
    if request.method == "PUT":
        current = {}
    current.update({k: v for k, v in data.items() if k not in ("id", "created", "updated")})
    execute("UPDATE docs SET data=?, updated=? WHERE id=?", (json.dumps(current, ensure_ascii=False), now(), did))
    return jsonify(item=doc_out(query_one("SELECT * FROM docs WHERE id=?", (did,))))


@bp.delete("/admin/<coll>/<int:did>")
@login_required()
def delete_doc(coll, did):
    denied = guard(coll, "write")
    if denied:
        return denied
    if coll == "assets" and storage.configured():
        row = query_one("SELECT * FROM docs WHERE id=? AND coll=?", (did, coll))
        item = json.loads(row["data"]) if row else {}
        if item.get("storage") == "cloudinary" and item.get("publicId"):
            try:
                storage.remove(item["publicId"], item.get("resourceType"))
            except Exception:
                pass
    execute("DELETE FROM docs WHERE id=? AND coll=?", (did, coll))
    return jsonify(ok=True)


@bp.get("/admin/users")
@login_required("admin")
def list_users():
    sql, args = "SELECT * FROM users", []
    where = []
    if request.args.get("role"):
        where.append("role=?")
        args.append(request.args["role"])
    if request.args.get("status"):
        where.append("status=?")
        args.append(request.args["status"])
    if request.args.get("q"):
        where.append("(LOWER(name) LIKE ? OR LOWER(email) LIKE ?)")
        args += [f"%{request.args['q'].lower()}%"] * 2
    if where:
        sql += " WHERE " + " AND ".join(where)
    total = query_one(sql.replace("SELECT *", "SELECT COUNT(*) AS n", 1), args)["n"]
    page, per, pages = paging(total)
    tail = " LIMIT ? OFFSET ?" if per else ""
    extra = [per, (page - 1) * per] if per else []
    rows = query(sql + " ORDER BY id ASC" + tail, [*args, *extra])
    return jsonify(users=[public_user(r) for r in rows], total=total, page=page, pages=pages)


@bp.post("/admin/users")
@login_required("admin")
def create_user():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    role = data.get("role") if data.get("role") in ROLES else "kid"
    if not (data.get("name") or "").strip() or "@" not in email or len(data.get("password") or "") < 6:
        return jsonify(error="Name, email and a password of 6+ characters are required"), 400
    if role in ("admin", "super_admin") and g.user["role"] != "super_admin":
        return jsonify(error="Only a super admin can create admins"), 403
    if query_one("SELECT id FROM users WHERE email=?", (email,)):
        return jsonify(error="This email is already registered"), 409
    uid = execute(
        "INSERT INTO users(name,email,password_hash,role,emoji,status,created) VALUES(?,?,?,?,?,?,?)",
        (data["name"].strip(), email, generate_password_hash(data["password"]), role, data.get("emoji") or "🐻", "active", now()),
    )
    return jsonify(user=public_user(query_one("SELECT * FROM users WHERE id=?", (uid,)))), 201


@bp.route("/admin/users/<int:uid>", methods=["PUT", "PATCH"])
@login_required("admin")
def update_user(uid):
    user = query_one("SELECT * FROM users WHERE id=?", (uid,))
    if not user:
        return jsonify(error="User not found"), 404
    data = request.get_json(silent=True) or {}
    role = data.get("role", user["role"])
    if role not in ROLES:
        return jsonify(error="Unknown role"), 400
    if (role in ("admin", "super_admin") or user["role"] in ("admin", "super_admin")) and g.user["role"] != "super_admin":
        return jsonify(error="Only a super admin can change admins"), 403
    status = data.get("status", user["status"])
    if status not in ("active", "suspended"):
        return jsonify(error="Unknown status"), 400
    if uid == g.user["id"] and (status != "active" or role != user["role"]):
        return jsonify(error="You cannot change your own role or status"), 400
    execute(
        "UPDATE users SET name=?, emoji=?, role=?, status=? WHERE id=?",
        (data.get("name", user["name"]), data.get("emoji", user["emoji"]), role, status, uid),
    )
    if data.get("password"):
        execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(data["password"]), uid))
    return jsonify(user=public_user(query_one("SELECT * FROM users WHERE id=?", (uid,))))


@bp.delete("/admin/users/<int:uid>")
@login_required("admin")
def delete_user(uid):
    user = query_one("SELECT * FROM users WHERE id=?", (uid,))
    if not user:
        return jsonify(error="User not found"), 404
    if uid == g.user["id"]:
        return jsonify(error="You cannot delete yourself"), 400
    if user["role"] in ("admin", "super_admin") and g.user["role"] != "super_admin":
        return jsonify(error="Only a super admin can delete admins"), 403
    execute("DELETE FROM users WHERE id=?", (uid,))
    return jsonify(ok=True)


@bp.get("/admin/games")
@login_required("admin")
def admin_games():
    from .games import serialize

    where, args = [], []
    if request.args.get("status"):
        where.append("status=?")
        args.append(request.args["status"])
    if request.args.get("q"):
        where.append("(LOWER(title) LIKE ? OR LOWER(author) LIKE ?)")
        args += [f"%{request.args['q'].lower()}%"] * 2
    sql = "SELECT * FROM games" + (" WHERE " + " AND ".join(where) if where else "")
    total = query_one(sql.replace("SELECT *", "SELECT COUNT(*) AS n", 1), args)["n"]
    page, per, pages = paging(total)
    tail = " LIMIT ? OFFSET ?" if per else ""
    extra = [per, (page - 1) * per] if per else []
    rows = query(sql + " ORDER BY updated DESC" + tail, [*args, *extra])
    return jsonify(games=[serialize(r) for r in rows], total=total, page=page, pages=pages)


@bp.route("/admin/games/<int:gid>", methods=["PATCH"])
@login_required("admin")
def admin_game_flags(gid):
    row = query_one("SELECT * FROM games WHERE id=?", (gid,))
    if not row:
        return jsonify(error="Game not found"), 404
    data = request.get_json(silent=True) or {}
    featured = 1 if data.get("featured", bool(row["featured"])) else 0
    status = data.get("status", row["status"])
    visibility = data.get("visibility", row["visibility"])
    if status not in ("draft", "published", "hidden") or visibility not in ("private", "link", "public"):
        return jsonify(error="Invalid status or visibility"), 400
    execute("UPDATE games SET featured=?, status=?, visibility=?, updated=? WHERE id=?", (featured, status, visibility, now(), gid))
    return jsonify(ok=True)


def count(sql, args=()):
    return query_one(sql, args)["n"]


@bp.get("/admin/dashboard")
@login_required("admin")
def dashboard():
    data = {
        "users": count("SELECT COUNT(*) AS n FROM users"),
        "activeUsers": count("SELECT COUNT(*) AS n FROM users WHERE status='active'"),
        "games": count("SELECT COUNT(*) AS n FROM games"),
        "published": count("SELECT COUNT(*) AS n FROM games WHERE status='published'"),
        "drafts": count("SELECT COUNT(*) AS n FROM games WHERE status='draft'"),
        "plays": count("SELECT COALESCE(SUM(plays),0) AS n FROM games"),
        "results": count("SELECT COUNT(*) AS n FROM results"),
        "liveSessions": count("SELECT COUNT(*) AS n FROM live_sessions"),
        "openTickets": count("SELECT COUNT(*) AS n FROM docs WHERE coll='support' AND data LIKE '%\"status\": \"open\"%'"),
        "pendingModeration": count("SELECT COUNT(*) AS n FROM docs WHERE coll='moderation' AND data LIKE '%\"status\": \"pending\"%'"),
    }
    top = query("SELECT id,title,emoji,plays,rating FROM games WHERE status='published' ORDER BY plays DESC LIMIT 5")
    recent = query("SELECT r.player, r.score, r.created, g.title FROM results r JOIN games g ON g.id=r.game_id ORDER BY r.id DESC LIMIT 8")
    roles = query("SELECT role, COUNT(*) AS n FROM users GROUP BY role")
    return jsonify(stats=data, topGames=[dict(r) for r in top], recentResults=[dict(r) for r in recent], roles={r["role"]: r["n"] for r in roles})


@bp.get("/admin/reports/summary")
@login_required("admin")
def reports_summary():
    by_subject = query("SELECT subject, COUNT(*) AS games, COALESCE(SUM(plays),0) AS plays FROM games WHERE status='published' GROUP BY subject ORDER BY plays DESC")
    daily = query("SELECT substr(created,1,10) AS day, COUNT(*) AS plays, CAST(COALESCE(AVG(score),0) AS DOUBLE PRECISION) AS \"avgScore\" FROM results GROUP BY day ORDER BY day DESC LIMIT 14")
    accuracy = query_one("SELECT COALESCE(SUM(correct),0) AS c, COALESCE(SUM(total),0) AS t FROM results")
    return jsonify(
        bySubject=[dict(r) for r in by_subject],
        daily=[dict(r) for r in daily],
        accuracy=round(accuracy["c"] / accuracy["t"] * 100, 1) if accuracy["t"] else 0,
    )


@bp.get("/admin/system")
@login_required("admin")
def system():
    size = query_one("SELECT pg_database_size(current_database()) AS n")["n"]
    return jsonify(
        status="ok",
        uptimeSeconds=int(time.time() - STARTED),
        python=sys.version.split()[0],
        platform=platform.platform(),
        databaseBytes=size,
        database="PostgreSQL",
        tables={t: count(f"SELECT COUNT(*) AS n FROM {t}") for t in ("users", "games", "results", "live_sessions", "docs")},
        time=now(),
    )


@bp.post("/assets/upload")
@login_required("creator")
def upload_asset():
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify(error="Choose a file"), 400
    ext = os.path.splitext(secure_filename(file.filename))[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".mp3", ".wav", ".ogg"):
        return jsonify(error="Only images and audio files are allowed"), 400
    data = file.read()
    digest = hashlib.sha256(data).hexdigest()
    original = secure_filename(file.filename)
    for row in query("SELECT * FROM docs WHERE coll='assets'"):
        item = json.loads(row["data"])
        same_name = (item.get("name") or "").lower() == original.lower()
        same_file = item.get("hash") == digest
        if not same_file and not item.get("hash") and item.get("url", "").startswith("/"):
            path = os.path.join(current_app.config["UPLOAD_FOLDER"], os.path.basename(item["url"]))
            if os.path.exists(path):
                with open(path, "rb") as fh:
                    same_file = hashlib.sha256(fh.read()).hexdigest() == digest
        if same_name or same_file:
            return jsonify(item=doc_out(row), duplicate=True), 200
    kind = "audio" if ext in (".mp3", ".wav", ".ogg") else "image"
    stored = {}
    if storage.configured():
        try:
            stored = storage.upload(data, original)
        except Exception as error:
            return jsonify(error=f"Cloudinary upload failed: {error}"), 502
        url = stored["url"]
    else:
        name = f"{uuid.uuid4().hex}{ext}"
        with open(os.path.join(current_app.config["UPLOAD_FOLDER"], name), "wb") as fh:
            fh.write(data)
        url = f"/api/uploads/{name}"
    stamp = now()
    item = {"name": original, "kind": kind, "emoji": "🔊" if kind == "audio" else "🖼️", "tags": ["upload"], "url": url, "hash": digest}
    if stored:
        item["storage"] = "cloudinary"
        item["publicId"] = stored["public_id"]
        item["resourceType"] = stored["resource_type"]
    did = execute("INSERT INTO docs(coll,data,created,updated) VALUES(?,?,?,?)", ("assets", json.dumps(item, ensure_ascii=False), stamp, stamp))
    return jsonify(item=doc_out(query_one("SELECT * FROM docs WHERE id=?", (did,)))), 201


@bp.get("/uploads/<path:name>")
def uploaded(name):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], name)
