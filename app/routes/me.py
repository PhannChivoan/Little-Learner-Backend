import json
import random

from flask import Blueprint, g, jsonify, request

from ..auth import login_required, public_user
from ..db import execute, now, query, query_one
from .games import serialize

bp = Blueprint("me", __name__, url_prefix="/api")


def stats_for(uid):
    row = query_one(
        "SELECT COUNT(*) AS games, COALESCE(SUM(score),0) AS points, COALESCE(SUM(correct),0) AS correct, COALESCE(SUM(total),0) AS total FROM results WHERE user_id=?",
        (uid,),
    )
    spent = query_one("SELECT COALESCE(SUM(cost),0) AS n FROM purchases WHERE user_id=?", (uid,))["n"]
    earned = row["points"] // 10
    best = query_one("SELECT COUNT(*) AS n FROM results WHERE user_id=? AND total>0 AND correct=total", (uid,))["n"]
    days = [r["d"] for r in query("SELECT DISTINCT substr(created,1,10) AS d FROM results WHERE user_id=? ORDER BY d DESC LIMIT 30", (uid,))]
    return {
        "games": row["games"],
        "points": row["points"],
        "correct": row["correct"],
        "total": row["total"],
        "accuracy": round(row["correct"] / row["total"] * 100) if row["total"] else 0,
        "stars": earned - spent,
        "earned": earned,
        "perfect": best,
        "activeDays": len(days),
        "level": 1 + row["points"] // 2000,
        "levelProgress": row["points"] % 2000 / 20,
    }


@bp.get("/me/overview")
@login_required()
def overview():
    history = query(
        "SELECT r.id, r.score, r.correct, r.total, r.created, g.id AS game_id, g.title, g.emoji, g.gradient FROM results r JOIN games g ON g.id=r.game_id "
        "WHERE r.user_id=? ORDER BY r.id DESC LIMIT 10",
        (g.user["id"],),
    )
    return jsonify(user=public_user(g.user), stats=stats_for(g.user["id"]), history=[dict(r) for r in history])


@bp.get("/me/analytics")
@login_required()
def analytics():
    uid = g.user["id"]
    subjects = query(
        "SELECT g.subject AS subject, COUNT(*) AS plays, SUM(r.correct) AS correct, SUM(r.total) AS total FROM results r JOIN games g ON g.id=r.game_id WHERE r.user_id=? GROUP BY g.subject ORDER BY plays DESC",
        (uid,),
    )
    daily = query("SELECT substr(created,1,10) AS day, SUM(score) AS points, COUNT(*) AS plays FROM results WHERE user_id=? GROUP BY day ORDER BY day DESC LIMIT 14", (uid,))
    weak = query(
        "SELECT g.id, g.title, g.emoji, CAST(ROUND(100.0*SUM(r.correct)/NULLIF(SUM(r.total),0)) AS DOUBLE PRECISION) AS accuracy FROM results r JOIN games g ON g.id=r.game_id WHERE r.user_id=? GROUP BY g.id HAVING SUM(r.total) > 0 ORDER BY accuracy ASC LIMIT 5",
        (uid,),
    )
    return jsonify(
        stats=stats_for(uid),
        subjects=[{"subject": r["subject"], "plays": r["plays"], "accuracy": round((r["correct"] or 0) / r["total"] * 100) if r["total"] else 0} for r in subjects],
        daily=[dict(r) for r in reversed(daily)],
        weak=[dict(r) for r in weak],
    )


@bp.get("/rewards")
def list_rewards():
    rows = query("SELECT id, data FROM docs WHERE coll='rewards' ORDER BY id")
    items = []
    for r in rows:
        d = json.loads(r["data"])
        if d.get("active", True):
            d["id"] = r["id"]
            items.append(d)
    return jsonify(items=items)


@bp.get("/me/rewards")
@login_required()
def my_rewards():
    owned = [r["reward_id"] for r in query("SELECT reward_id FROM purchases WHERE user_id=?", (g.user["id"],))]
    return jsonify(owned=owned, stars=stats_for(g.user["id"])["stars"])


@bp.post("/rewards/<int:rid>/buy")
@login_required()
def buy_reward(rid):
    row = query_one("SELECT data FROM docs WHERE id=? AND coll='rewards'", (rid,))
    if not row:
        return jsonify(error="Reward not found"), 404
    d = json.loads(row["data"])
    if not d.get("active", True):
        return jsonify(error="This reward is not available"), 400
    if query_one("SELECT id FROM purchases WHERE user_id=? AND reward_id=?", (g.user["id"], rid)):
        return jsonify(error="You already have this"), 409
    cost = int(d.get("cost") or 0)
    stars = stats_for(g.user["id"])["stars"]
    if stars < cost:
        return jsonify(error=f"You need {cost - stars} more stars"), 400
    execute("INSERT INTO purchases(user_id,reward_id,cost,created) VALUES(?,?,?,?)", (g.user["id"], rid, cost, now()))
    return jsonify(stars=stars - cost)


@bp.get("/me/library")
@login_required()
def library():
    rows = query("SELECT g.* FROM games g JOIN saved_games s ON s.game_id=g.id WHERE s.user_id=? ORDER BY s.created DESC", (g.user["id"],))
    return jsonify(games=[serialize(r) for r in rows])


@bp.post("/me/library/<int:gid>")
@login_required()
def save_game(gid):
    if not query_one("SELECT id FROM games WHERE id=?", (gid,)):
        return jsonify(error="Game not found"), 404
    if not query_one("SELECT 1 FROM saved_games WHERE user_id=? AND game_id=?", (g.user["id"], gid)):
        execute("INSERT INTO saved_games(user_id,game_id,created) VALUES(?,?,?)", (g.user["id"], gid, now()))
    return jsonify(ok=True)


@bp.delete("/me/library/<int:gid>")
@login_required()
def unsave_game(gid):
    execute("DELETE FROM saved_games WHERE user_id=? AND game_id=?", (g.user["id"], gid))
    return jsonify(ok=True)


def class_out(row, with_members=False):
    members = query(
        "SELECT u.id, u.name, u.emoji FROM class_members m JOIN users u ON u.id=m.user_id WHERE m.class_id=? ORDER BY u.name",
        (row["id"],),
    )
    out = {"id": row["id"], "name": row["name"], "code": row["code"], "teacherId": row["teacher_id"], "students": len(members), "created": row["created"]}
    if with_members:
        people = []
        for m in members:
            s = stats_for(m["id"])
            people.append({"id": m["id"], "name": m["name"], "emoji": m["emoji"], "games": s["games"], "points": s["points"], "accuracy": s["accuracy"]})
        out["members"] = people
    return out


@bp.get("/classes")
@login_required()
def my_classes():
    if g.user["role"] in ("teacher", "admin", "super_admin"):
        rows = query("SELECT * FROM classrooms WHERE teacher_id=? ORDER BY id DESC", (g.user["id"],))
    else:
        rows = query("SELECT c.* FROM classrooms c JOIN class_members m ON m.class_id=c.id WHERE m.user_id=? ORDER BY c.id DESC", (g.user["id"],))
    return jsonify(classes=[class_out(r) for r in rows])


@bp.post("/classes")
@login_required("teacher")
def create_class():
    name = ((request.get_json(silent=True) or {}).get("name") or "").strip()
    if not name:
        return jsonify(error="Give the class a name"), 400
    while True:
        code = "".join(random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
        if not query_one("SELECT id FROM classrooms WHERE code=?", (code,)):
            break
    cid = execute("INSERT INTO classrooms(name,teacher_id,code,created) VALUES(?,?,?,?)", (name, g.user["id"], code, now()))
    return jsonify(class_=class_out(query_one("SELECT * FROM classrooms WHERE id=?", (cid,)))), 201


@bp.post("/classes/join")
@login_required()
def join_class():
    code = ((request.get_json(silent=True) or {}).get("code") or "").strip().upper()
    row = query_one("SELECT * FROM classrooms WHERE code=?", (code,))
    if not row:
        return jsonify(error="That class code does not exist"), 404
    if not query_one("SELECT 1 FROM class_members WHERE class_id=? AND user_id=?", (row["id"], g.user["id"])):
        execute("INSERT INTO class_members(class_id,user_id,created) VALUES(?,?,?)", (row["id"], g.user["id"], now()))
    return jsonify(class_=class_out(row))


@bp.get("/classes/<int:cid>")
@login_required()
def get_class(cid):
    row = query_one("SELECT * FROM classrooms WHERE id=?", (cid,))
    if not row:
        return jsonify(error="Class not found"), 404
    is_member = query_one("SELECT 1 FROM class_members WHERE class_id=? AND user_id=?", (cid, g.user["id"]))
    if row["teacher_id"] != g.user["id"] and not is_member and g.user["role"] not in ("admin", "super_admin"):
        return jsonify(error="Class not found"), 404
    return jsonify(class_=class_out(row, True))


@bp.delete("/classes/<int:cid>")
@login_required("teacher")
def delete_class(cid):
    row = query_one("SELECT * FROM classrooms WHERE id=?", (cid,))
    if not row or (row["teacher_id"] != g.user["id"] and g.user["role"] not in ("admin", "super_admin")):
        return jsonify(error="Class not found"), 404
    execute("DELETE FROM class_members WHERE class_id=?", (cid,))
    execute("DELETE FROM classrooms WHERE id=?", (cid,))
    return jsonify(ok=True)


@bp.delete("/classes/<int:cid>/members/<int:uid>")
@login_required("teacher")
def remove_member(cid, uid):
    row = query_one("SELECT * FROM classrooms WHERE id=?", (cid,))
    if not row or row["teacher_id"] != g.user["id"]:
        return jsonify(error="Class not found"), 404
    execute("DELETE FROM class_members WHERE class_id=? AND user_id=?", (cid, uid))
    return jsonify(ok=True)


@bp.get("/announcements")
def announcements():
    rows = query("SELECT id, data, created FROM docs WHERE coll='announcements' ORDER BY id DESC LIMIT 20")
    items = []
    for r in rows:
        d = json.loads(r["data"])
        if d.get("status") == "sent":
            d["id"] = r["id"]
            d["created"] = r["created"]
            items.append(d)
    return jsonify(items=items)


def can_see_class(row):
    if row["teacher_id"] == g.user["id"] or g.user["role"] in ("admin", "super_admin"):
        return True
    return bool(query_one("SELECT 1 FROM class_members WHERE class_id=? AND user_id=?", (row["id"], g.user["id"])))


@bp.get("/classes/<int:cid>/assignments")
@login_required()
def list_assignments(cid):
    row = query_one("SELECT * FROM classrooms WHERE id=?", (cid,))
    if not row or not can_see_class(row):
        return jsonify(error="Class not found"), 404
    members = [m["user_id"] for m in query("SELECT user_id FROM class_members WHERE class_id=?", (cid,))]
    out = []
    for a in query("SELECT * FROM assignments WHERE class_id=? ORDER BY id DESC", (cid,)):
        game = query_one("SELECT id,title,emoji FROM games WHERE id=?", (a["game_id"],))
        done = 0
        mine = False
        for uid in members:
            has = query_one("SELECT 1 FROM results WHERE user_id=? AND game_id=? AND created>=?", (uid, a["game_id"], a["created"]))
            done += 1 if has else 0
            if uid == g.user["id"]:
                mine = bool(has)
        out.append({
            "id": a["id"],
            "gameId": a["game_id"],
            "title": a["title"],
            "due": a["due"],
            "created": a["created"],
            "game": dict(game) if game else None,
            "done": done,
            "students": len(members),
            "mine": mine,
        })
    return jsonify(assignments=out)


@bp.post("/classes/<int:cid>/assignments")
@login_required("teacher")
def create_assignment(cid):
    row = query_one("SELECT * FROM classrooms WHERE id=?", (cid,))
    if not row or row["teacher_id"] != g.user["id"]:
        return jsonify(error="Class not found"), 404
    data = request.get_json(silent=True) or {}
    game = query_one("SELECT * FROM games WHERE id=?", (int(data.get("gameId") or 0),))
    if not game:
        return jsonify(error="Pick a game"), 400
    execute(
        "INSERT INTO assignments(class_id,game_id,title,due,created) VALUES(?,?,?,?,?)",
        (cid, game["id"], (data.get("title") or game["title"]).strip(), data.get("due") or "", now()),
    )
    return jsonify(ok=True), 201


@bp.delete("/assignments/<int:aid>")
@login_required("teacher")
def delete_assignment(aid):
    a = query_one("SELECT a.*, c.teacher_id FROM assignments a JOIN classrooms c ON c.id=a.class_id WHERE a.id=?", (aid,))
    if not a or a["teacher_id"] != g.user["id"]:
        return jsonify(error="Not found"), 404
    execute("DELETE FROM assignments WHERE id=?", (aid,))
    return jsonify(ok=True)


@bp.get("/games/by-author/<name>")
def games_by_author(name):
    rows = query("SELECT * FROM games WHERE author=? AND status='published' AND visibility='public' ORDER BY plays DESC", (name,))
    return jsonify(games=[serialize(r) for r in rows])
