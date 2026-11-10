from flask import Blueprint, g, jsonify, request

from ..auth import login_required, optional_user
from ..db import execute, now, query, query_one

bp = Blueprint("play", __name__, url_prefix="/api/play")


def find_game(ident):
    if str(ident).isdigit():
        return query_one("SELECT * FROM games WHERE id=?", (int(ident),))
    return query_one("SELECT * FROM games WHERE slug=?", (ident,))


@bp.post("/results")
@optional_user
def submit_result():
    data = request.get_json(silent=True) or {}
    game = find_game(data.get("game") or data.get("gameId") or "")
    if not game:
        return jsonify(error="Game not found"), 404
    total = max(0, int(data.get("total") or 0))
    correct = max(0, min(total, int(data.get("correct") or 0)))
    score = max(0, int(data.get("score") or 0))
    player = g.user["name"] if g.user else (data.get("player") or "Guest")[:40]
    rid = execute(
        "INSERT INTO results(game_id,user_id,player,score,correct,total,seconds,created) VALUES(?,?,?,?,?,?,?,?)",
        (game["id"], g.user["id"] if g.user else None, player, score, correct, total, max(0, int(data.get("seconds") or 0)), now()),
    )
    execute("UPDATE games SET plays=plays+1 WHERE id=?", (game["id"],))
    rank = query_one("SELECT COUNT(*) AS n FROM results WHERE game_id=? AND score>?", (game["id"], score))["n"] + 1
    return jsonify(id=rid, rank=rank, stars=3 if total and correct / total >= 0.8 else 2 if total and correct / total >= 0.5 else 1), 201


@bp.post("/rate")
@optional_user
def rate():
    data = request.get_json(silent=True) or {}
    game = find_game(data.get("game") or "")
    stars = int(data.get("stars") or 0)
    if not game or not 1 <= stars <= 5:
        return jsonify(error="Game and stars (1-5) are required"), 400
    plays = max(game["plays"], 1)
    new = round((game["rating"] * min(plays, 50) + stars) / (min(plays, 50) + 1), 2)
    execute("UPDATE games SET rating=? WHERE id=?", (new, game["id"]))
    return jsonify(rating=new)


@bp.get("/leaderboard/<ident>")
def leaderboard(ident):
    game = find_game(ident)
    if not game:
        return jsonify(error="Game not found"), 404
    rows = query(
        "SELECT player, MAX(score) AS score, MAX(correct) AS correct, MAX(total) AS total FROM results WHERE game_id=? GROUP BY player ORDER BY score DESC LIMIT 20",
        (game["id"],),
    )
    return jsonify(leaderboard=[dict(r) for r in rows])


@bp.get("/history")
@login_required()
def history():
    rows = query(
        "SELECT r.id, r.score, r.correct, r.total, r.seconds, r.created, g.title, g.emoji, g.id AS game_id FROM results r JOIN games g ON g.id=r.game_id "
        "WHERE r.user_id=? ORDER BY r.id DESC LIMIT 50",
        (g.user["id"],),
    )
    return jsonify(history=[dict(r) for r in rows])


@bp.get("/me/stats")
@login_required()
def my_stats():
    row = query_one(
        "SELECT COUNT(*) AS games, COALESCE(SUM(score),0) AS points, COALESCE(SUM(correct),0) AS correct, COALESCE(SUM(total),0) AS total FROM results WHERE user_id=?",
        (g.user["id"],),
    )
    return jsonify(stats=dict(row))
