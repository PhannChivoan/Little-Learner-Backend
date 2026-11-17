import json
import random
import time

import pymysql
from flask import Blueprint, current_app, g, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from ..auth import login_required
from ..db import execute, get_db, now, query, query_one

bp = Blueprint("live", __name__, url_prefix="/api/live")

INTRO_SECONDS = 3.0
BOARD_SECONDS = 11.0
LIVE_TYPES = ("quiz", "truefalse")
PLAYING = ("intro", "question", "leaderboard")


def new_pin():
    while True:
        pin = f"{random.randint(0, 999999):06d}"
        if not query_one("SELECT id FROM live_sessions WHERE pin=?", (pin,)):
            return pin


def player_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="live-player")


def make_player_token(player_id):
    return player_serializer().dumps({"pid": player_id})


def read_player_token(token):
    try:
        return player_serializer().loads(str(token or ""), max_age=60 * 60 * 12)["pid"]
    except (BadSignature, SignatureExpired, KeyError):
        return None


def live_questions(game):
    try:
        raw = json.loads(game["questions"] or "[]")
    except ValueError:
        raw = []
    out = []
    for q in raw:
        if (q.get("type") or "quiz") not in LIVE_TYPES:
            continue
        options = [(i, str(a)) for i, a in enumerate(q.get("a") or []) if str(a).strip()]
        correct = next((n for n, (i, _) in enumerate(options) if i == q.get("c", 0)), None)
        if len(options) < 2 or correct is None or not str(q.get("q") or "").strip():
            continue
        try:
            seconds = int(q.get("t") or 20)
        except (TypeError, ValueError):
            seconds = 20
        out.append({"text": str(q["q"]), "img": str(q.get("img") or ""), "options": [a for _, a in options], "correct": correct, "t": max(5, min(120, seconds))})
    return out


def game_row(session):
    return query_one("SELECT * FROM games WHERE id=?", (session["game_id"],))


def session_questions(session):
    game = game_row(session)
    return live_questions(game) if game else []


def ensure_state(session):
    row = query_one("SELECT * FROM live_state WHERE session_id=?", (session["id"],))
    if row:
        return row
    execute("INSERT IGNORE INTO live_state(session_id, phase, q_index, phase_started, seq) VALUES(?,?,?,?,0)", (session["id"], "lobby", 0, time.time()))
    return query_one("SELECT * FROM live_state WHERE session_id=?", (session["id"],))


def move(session, state, phase, index, started):
    cur = get_db().execute(
        "UPDATE live_state SET phase=?, q_index=?, phase_started=?, paused_at=NULL, seq=seq+1 WHERE session_id=? AND seq=?",
        (phase, index, started, session["id"], state["seq"]),
    )
    if cur.rowcount != 1:
        return False
    status = "ended" if phase == "finished" else "lobby" if phase == "lobby" else "playing"
    execute("UPDATE live_sessions SET status=?, current=? WHERE id=?", (status, index, session["id"]))
    return True


def answered_count(session, index):
    return query_one("SELECT COUNT(*) AS n FROM live_answers WHERE session_id=? AND q_index=?", (session["id"], index))["n"]


def player_count(session):
    return query_one("SELECT COUNT(*) AS n FROM live_players WHERE session_id=?", (session["id"],))["n"]


def tick(session):
    for _ in range(8):
        state = ensure_state(session)
        phase = state["phase"]
        if phase not in PLAYING or state["paused_at"] is not None:
            return state
        questions = session_questions(session)
        total = len(questions)
        index = state["q_index"]
        if not total or index >= total:
            if move(session, state, "finished", max(0, total - 1), time.time()):
                return ensure_state(session)
            continue
        started = state["phase_started"]
        elapsed = time.time() - started
        target = None
        if phase == "intro" and elapsed >= INTRO_SECONDS:
            target = ("question", index, started + INTRO_SECONDS)
        elif phase == "question":
            limit = questions[index]["t"]
            players = player_count(session)
            if elapsed >= limit:
                target = ("leaderboard", index, started + limit)
            elif players and answered_count(session, index) >= players:
                target = ("leaderboard", index, time.time())
        elif phase == "leaderboard" and elapsed >= BOARD_SECONDS:
            target = ("intro", index + 1, started + BOARD_SECONDS) if index + 1 < total else ("finished", index, started + BOARD_SECONDS)
        if not target:
            return state
        if not move(session, state, *target):
            continue
    return ensure_state(session)


def standings(session, index, phase):
    players = query("SELECT id, name, emoji FROM live_players WHERE session_id=? ORDER BY id ASC", (session["id"],))
    rows = query("SELECT player_id, q_index, choice, correct, points, bonus FROM live_answers WHERE session_id=?", (session["id"],))
    by_player = {}
    for row in rows:
        by_player.setdefault(row["player_id"], {})[row["q_index"]] = row
    after = index if phase in ("leaderboard", "finished") else index - 1
    before = after - 1 if phase in ("leaderboard", "finished") else after

    def total_through(pid, upto):
        return sum(a["points"] + a["bonus"] for q, a in by_player.get(pid, {}).items() if q <= upto)

    def streak_through(pid, upto):
        count = 0
        for q in range(upto, -1, -1):
            a = by_player.get(pid, {}).get(q)
            if a and a["correct"]:
                count += 1
            else:
                break
        return count

    entries = []
    for p in players:
        mine = by_player.get(p["id"], {})
        current = mine.get(index)
        entries.append({
            "id": p["id"], "name": p["name"], "emoji": p["emoji"],
            "score": total_through(p["id"], after), "prevScore": total_through(p["id"], before),
            "streak": streak_through(p["id"], after),
            "answered": current is not None,
            "delta": (current["points"] + current["bonus"]) if current and phase in ("leaderboard", "finished") else 0,
        })
    for key, rank_key in (("score", "rank"), ("prevScore", "prevRank")):
        ordered = sorted(entries, key=lambda e: (-e[key], e["id"]))
        for place, e in enumerate(ordered, 1):
            e[rank_key] = place
    entries.sort(key=lambda e: e["rank"])
    return entries, by_player


def build(session, viewer=None):
    state = tick(session)
    game = game_row(session)
    questions = live_questions(game) if game else []
    total = len(questions)
    phase = state["phase"]
    index = min(state["q_index"], max(0, total - 1)) if total else 0
    paused = state["paused_at"] is not None
    reference = state["paused_at"] if paused else time.time()
    elapsed = max(0.0, reference - state["phase_started"])
    duration = INTRO_SECONDS if phase == "intro" else questions[index]["t"] if phase == "question" and questions else BOARD_SECONDS if phase == "leaderboard" else 0
    remaining = max(0.0, duration - elapsed) if duration else 0
    entries, by_player = standings(session, index, phase)
    host_row = query_one("SELECT name FROM users WHERE id=?", (session["host_id"],)) if session["host_id"] else None
    settings = {}
    try:
        settings = (json.loads(game["config"]) or {}).get("settings", {}) if game and game["config"] else {}
    except ValueError:
        settings = {}
    out = {
        "pin": session["pin"], "gameId": session["game_id"], "hostName": host_row["name"] if host_row else "", "phase": phase, "paused": paused,
        "index": index, "total": total, "duration": duration, "remaining": round(remaining, 2),
        "status": "ended" if phase == "finished" else "lobby" if phase == "lobby" else "playing",
        "game": {"title": game["title"] if game else "", "emoji": game["emoji"] if game else "🎮", "skin": game["skin"] if game else "jungle", "track": settings.get("track", "happy"), "musicUrl": settings.get("musicUrl", ""), "dark": settings.get("dark", True)},
        "players": entries, "playerCount": len(entries),
        "answered": sum(1 for e in entries if e["answered"]),
    }
    if phase in PLAYING and questions:
        q = questions[index]
        out["question"] = {"index": index, "total": total, "text": q["text"], "img": q["img"], "options": q["options"], "t": q["t"]}
        if phase == "leaderboard":
            counts = [0] * len(q["options"])
            for pid_rows in by_player.values():
                a = pid_rows.get(index)
                if a and 0 <= a["choice"] < len(counts):
                    counts[a["choice"]] += 1
            out["reveal"] = {"correct": q["correct"], "counts": counts}
    if phase == "finished":
        out["reveal"] = None
    if viewer:
        mine = by_player.get(viewer, {}).get(index)
        entry = next((e for e in entries if e["id"] == viewer), None)
        out["me"] = {
            "id": viewer, "answered": mine is not None, "choice": mine["choice"] if mine else None,
            "rank": entry["rank"] if entry else None, "prevRank": entry["prevRank"] if entry else None,
            "score": entry["score"] if entry else 0, "prevScore": entry["prevScore"] if entry else 0,
            "streak": entry["streak"] if entry else 0,
        }
        if phase in ("leaderboard", "finished"):
            out["me"]["correct"] = bool(mine and mine["correct"])
            out["me"]["points"] = mine["points"] if mine else 0
            out["me"]["bonus"] = mine["bonus"] if mine else 0
    return out


def find_session(pin):
    return query_one("SELECT * FROM live_sessions WHERE pin=?", (str(pin),))


def is_host(session):
    return g.user and (session["host_id"] == g.user["id"] or g.user["role"] in ("admin", "super_admin"))


@bp.post("/sessions")
@login_required("teacher")
def create_session():
    data = request.get_json(silent=True) or {}
    game = query_one("SELECT * FROM games WHERE id=?", (int(data.get("gameId") or 0),))
    if not game:
        return jsonify(error="Game not found"), 404
    if not live_questions(game):
        return jsonify(error="This game has no multiple-choice questions, so it cannot be played live. Live games use Quiz and True / False questions."), 400
    sid = execute(
        "INSERT INTO live_sessions(pin,game_id,host_id,mode,created) VALUES(?,?,?,?,?)",
        (new_pin(), game["id"], g.user["id"], data.get("mode") or "classic", now()),
    )
    session = query_one("SELECT * FROM live_sessions WHERE id=?", (sid,))
    ensure_state(session)
    return jsonify(session=build(session)), 201


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
    pid = execute("INSERT INTO live_players(session_id,name,emoji,created) VALUES(?,?,?,?)", (session["id"], name, str(data.get("emoji") or "🐻")[:16], now()))
    return jsonify(playerId=pid, token=make_player_token(pid), session=build(session, pid)), 201


@bp.get("/sessions/<pin>")
def get_session(pin):
    session = find_session(pin)
    if not session:
        return jsonify(error="Session not found"), 404
    viewer = None
    player = request.args.get("player", "")
    if player.isdigit() and query_one("SELECT id FROM live_players WHERE id=? AND session_id=?", (int(player), session["id"])):
        viewer = int(player)
    return jsonify(session=build(session, viewer))


def reset_scores(session):
    execute(
        "UPDATE live_players lp SET lp.score = COALESCE((SELECT SUM(a.points + a.bonus) FROM live_answers a WHERE a.player_id = lp.id), 0) WHERE lp.session_id=?",
        (session["id"],),
    )


@bp.post("/sessions/<pin>/<action>")
@login_required("teacher")
def control(pin, action):
    session = find_session(pin)
    if not session:
        return jsonify(error="Session not found"), 404
    if not is_host(session):
        return jsonify(error="Only the host can do this"), 403
    if action not in ("start", "pause", "resume", "next", "prev", "end"):
        return jsonify(error="Unknown action"), 400
    state = tick(session)
    phase, index = state["phase"], state["q_index"]
    total = len(session_questions(session))
    clock = time.time()
    if action == "start":
        if phase == "lobby":
            if not total:
                return jsonify(error="This game has no questions for live play"), 400
            move(session, state, "intro", 0, clock)
    elif action == "pause":
        if phase in PLAYING and state["paused_at"] is None:
            execute("UPDATE live_state SET paused_at=? WHERE session_id=?", (clock, session["id"]))
    elif action == "resume":
        if state["paused_at"] is not None:
            execute("UPDATE live_state SET phase_started=?, paused_at=NULL WHERE session_id=?", (state["phase_started"] + (clock - state["paused_at"]), session["id"]))
    elif action == "next":
        if phase == "intro":
            move(session, state, "question", index, clock)
        elif phase == "question":
            move(session, state, "leaderboard", index, clock)
        elif phase == "leaderboard":
            if index + 1 < total:
                move(session, state, "intro", index + 1, clock)
            else:
                move(session, state, "finished", index, clock)
    elif action == "prev":
        if phase in PLAYING or phase == "finished":
            target = max(0, index - 1) if phase != "finished" else max(0, total - 1)
            execute("DELETE FROM live_answers WHERE session_id=? AND q_index>=?", (session["id"], target))
            reset_scores(session)
            move(session, state, "intro", target, clock)
    elif action == "end":
        if phase != "finished":
            move(session, state, "finished", index, clock)
    return jsonify(session=build(session))


@bp.post("/sessions/<pin>/answer")
def answer(pin):
    session = find_session(pin)
    data = request.get_json(silent=True) or {}
    if not session:
        return jsonify(error="This game is not running"), 404
    pid = read_player_token(data.get("token"))
    if not pid or pid != int(data.get("playerId") or 0) or not query_one("SELECT id FROM live_players WHERE id=? AND session_id=?", (pid, session["id"])):
        return jsonify(error="Player not found"), 403
    state = tick(session)
    if state["phase"] != "question" or state["paused_at"] is not None:
        return jsonify(error="Answers are closed right now", phase=state["phase"]), 409
    questions = session_questions(session)
    index = state["q_index"]
    q = questions[index]
    try:
        choice = int(data.get("choice", -1))
    except (TypeError, ValueError):
        choice = -1
    if not 0 <= choice < len(q["options"]):
        return jsonify(error="Pick one of the answers"), 400
    if query_one("SELECT id FROM live_answers WHERE session_id=? AND player_id=? AND q_index=?", (session["id"], pid, index)):
        return jsonify(ok=True, duplicate=True)
    elapsed = max(0.0, time.time() - state["phase_started"])
    fraction = min(1.0, elapsed / q["t"])
    correct = choice == q["correct"]
    points = int(round(1000 * (1 - fraction / 2))) if correct else 0
    streak = 0
    if correct:
        for earlier in range(index - 1, -1, -1):
            row = query_one("SELECT correct FROM live_answers WHERE session_id=? AND player_id=? AND q_index=?", (session["id"], pid, earlier))
            if row and row["correct"]:
                streak += 1
            else:
                break
    bonus = min(streak, 5) * 100 if correct else 0
    try:
        execute(
            "INSERT INTO live_answers(session_id,player_id,q_index,choice,correct,points,bonus,ms,created) VALUES(?,?,?,?,?,?,?,?,?)",
            (session["id"], pid, index, choice, 1 if correct else 0, points, bonus, int(elapsed * 1000), now()),
        )
    except pymysql.err.IntegrityError:
        return jsonify(ok=True, duplicate=True)
    if points or bonus:
        execute("UPDATE live_players SET score=score+? WHERE id=?", (points + bonus, pid))
    tick(session)
    return jsonify(ok=True)
