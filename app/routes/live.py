import json
import random

from flask import Blueprint, g, jsonify, request

from ..auth import login_required
from ..db import execute, now, query, query_one

bp = Blueprint("live", __name__, url_prefix="/api/live")


def new_pin():
    while True:
        pin = f"{random.randint(0, 999999):06d}"
        if not query_one("SELECT id FROM live_sessions WHERE pin=?", (pin,)):
            return pin


def state(session):
    players = query("SELECT id,name,emoji,score FROM live_players WHERE session_id=? ORDER BY score DESC, id ASC", (session["id"],))
    return {
        "pin": session["pin"],
        "gameId": session["game_id"],
        "mode": session["mode"],
        "status": session["status"],
        "current": session["current"],
        "players": [dict(p) for p in players],
    }


@bp.post("/sessions")
@login_required("teacher")
def create_session():
    data = request.get_json(silent=True) or {}
    game = query_one("SELECT id FROM games WHERE id=?", (int(data.get("gameId") or 0),))
    if not game:
        return jsonify(error="Game not found"), 404
    sid = execute(
        "INSERT INTO live_sessions(pin,game_id,host_id,mode,created) VALUES(?,?,?,?,?)",
        (new_pin(), game["id"], g.user["id"], data.get("mode") or "classic", now()),
    )
    return jsonify(session=state(query_one("SELECT * FROM live_sessions WHERE id=?", (sid,)))), 201


@bp.post("/join")
def join():
    data = request.get_json(silent=True) or {}
    session = query_one("SELECT * FROM live_sessions WHERE pin=? AND status!='ended'", (str(data.get("pin") or "").strip(),))
    if not session:
        return jsonify(error="That PIN does not match a live game"), 404
    name = (data.get("name") or "").strip()[:30]
    if not name:
        return jsonify(error="Enter a nickname"), 400
    if query_one("SELECT id FROM live_players WHERE session_id=? AND LOWER(name)=LOWER(?)", (session["id"], name)):
        return jsonify(error="That nickname is taken"), 409
    pid = execute("INSERT INTO live_players(session_id,name,emoji,created) VALUES(?,?,?,?)", (session["id"], name, data.get("emoji") or "🐻", now()))
    return jsonify(playerId=pid, session=state(session)), 201


@bp.get("/sessions/<pin>")
def get_session(pin):
    session = query_one("SELECT * FROM live_sessions WHERE pin=?", (pin,))
    if not session:
        return jsonify(error="Session not found"), 404
    return jsonify(session=state(session))


@bp.post("/sessions/<pin>/<action>")
@login_required("teacher")
def control(pin, action):
    session = query_one("SELECT * FROM live_sessions WHERE pin=?", (pin,))
    if not session:
        return jsonify(error="Session not found"), 404
    if session["host_id"] != g.user["id"] and g.user["role"] not in ("admin", "super_admin"):
        return jsonify(error="Only the host can do this"), 403
    if action == "start":
        execute("UPDATE live_sessions SET status='playing', current=0 WHERE id=?", (session["id"],))
    elif action == "next":
        execute("UPDATE live_sessions SET current=current+1 WHERE id=?", (session["id"],))
    elif action == "end":
        execute("UPDATE live_sessions SET status='ended' WHERE id=?", (session["id"],))
    else:
        return jsonify(error="Unknown action"), 400
    return jsonify(session=state(query_one("SELECT * FROM live_sessions WHERE id=?", (session["id"],))))


@bp.post("/sessions/<pin>/answer")
def answer(pin):
    session = query_one("SELECT * FROM live_sessions WHERE pin=? AND status='playing'", (pin,))
    data = request.get_json(silent=True) or {}
    if not session:
        return jsonify(error="This game is not running"), 404
    player = query_one("SELECT * FROM live_players WHERE id=? AND session_id=?", (int(data.get("playerId") or 0), session["id"]))
    if not player:
        return jsonify(error="Player not found"), 404
    game = query_one("SELECT questions FROM games WHERE id=?", (session["game_id"],))
    questions = json.loads(game["questions"] or "[]")
    if session["current"] >= len(questions):
        return jsonify(error="No more questions"), 400
    q = questions[session["current"]]
    correct = int(data.get("choice", -1)) == q["c"]
    points = int(q.get("p", 500)) if correct else 0
    if points:
        left = max(0.0, min(1.0, float(data.get("timeLeft", 0.5))))
        points = int(points * (0.5 + 0.5 * left))
        execute("UPDATE live_players SET score=score+? WHERE id=?", (points, player["id"]))
    return jsonify(correct=correct, points=points, answer=q["c"])
