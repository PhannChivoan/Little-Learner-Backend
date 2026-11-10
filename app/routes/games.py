import csv
import io
import json
import random
import re

from flask import Blueprint, g, jsonify, request

from ..auth import ROLE_RANK, login_required, optional_user
from ..db import execute, now, query, query_one

bp = Blueprint("games", __name__, url_prefix="/api")

SKINS = {"jungle", "ocean", "space", "candy", "farm", "desert", "sunny", "grape", "mint", "coral", "lime", "deepsea", "sky", "gold", "meadow"}
VISIBILITY = {"private", "link", "public"}
DEVICES = {"phone", "tablet", "desktop"}

AI_BANK = {
    "animals": [
        ("Which animal says moo?", ["Cow", "Cat", "Duck", "Pig"], 0, "🐮"),
        ("Which animal has a long trunk?", ["Lion", "Elephant", "Frog", "Owl"], 1, "🐘"),
        ("Which animal can fly?", ["Fish", "Dog", "Bird", "Cow"], 2, "🐦"),
        ("Which animal hops and says ribbit?", ["Frog", "Horse", "Bear", "Cat"], 0, "🐸"),
        ("Which animal is black and white and eats bamboo?", ["Panda", "Fox", "Rabbit", "Lion"], 0, "🐼"),
        ("Which animal lives in the sea?", ["Cow", "Fish", "Hen", "Goat"], 1, "🐟"),
    ],
    "colors": [
        ("What color is a banana?", ["Red", "Blue", "Yellow", "Green"], 2, "🍌"),
        ("What color is the sky on a sunny day?", ["Blue", "Pink", "Black", "Brown"], 0, "☀️"),
        ("What color is grass?", ["Purple", "Green", "Orange", "White"], 1, "🌿"),
        ("What color is a strawberry?", ["Red", "Blue", "Green", "Gray"], 0, "🍓"),
        ("What color is a carrot?", ["Pink", "Orange", "Blue", "Black"], 1, "🥕"),
    ],
    "numbers": [
        ("What is 1 + 1?", ["1", "2", "3", "4"], 1, "➕"),
        ("What is 2 + 3?", ["4", "5", "6", "7"], 1, "🔢"),
        ("What is 5 - 2?", ["1", "2", "3", "4"], 2, "➖"),
        ("How many fingers on one hand?", ["4", "5", "6", "10"], 1, "🖐️"),
        ("What number comes after 9?", ["8", "10", "11", "7"], 1, "🔟"),
    ],
    "fruit": [
        ("Which fruit is yellow and curved?", ["Apple", "Banana", "Grape", "Mango"], 1, "🍌"),
        ("Which fruit is red and round?", ["Apple", "Lemon", "Kiwi", "Pear"], 0, "🍎"),
        ("Which fruit has a hard shell and sweet water inside?", ["Coconut", "Orange", "Plum", "Fig"], 0, "🥥"),
        ("Which fruit is the king of fruits in Cambodia?", ["Durian", "Apple", "Peach", "Cherry"], 0, "🍈"),
    ],
}


def slugify(text):
    base = re.sub(r"[^a-z0-9]+", "-", (text or "game").lower()).strip("-") or "game"
    slug, n = base, 2
    while query_one("SELECT id FROM games WHERE slug=?", (slug,)):
        slug = f"{base}-{n}"
        n += 1
    return slug


QTYPES = {"quiz", "truefalse", "type", "order", "slider", "match", "memory", "lesson", "canvas"}
OBJ_KINDS = {"text", "emoji", "image", "shape", "button", "zone"}
OBJ_ROLES = {"decor", "correct", "wrong", "drag", "target"}


def strs(v, limit):
    return [str(x) for x in (v or [])][:limit]


def num(v, default):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def clamp(v, lo, hi, default):
    return min(max(num(v, default), lo), hi)


def clean_obj(o):
    kind = o.get("kind") if o.get("kind") in OBJ_KINDS else "text"
    role = o.get("role") if o.get("role") in OBJ_ROLES else "decor"
    return {
        "id": str(o.get("id") or "")[:24],
        "kind": kind,
        "text": str(o.get("text") or "")[:400],
        "x": clamp(o.get("x"), -20, 110, 10),
        "y": clamp(o.get("y"), -20, 110, 10),
        "w": clamp(o.get("w"), 2, 100, 15),
        "h": clamp(o.get("h"), 2, 100, 15),
        "fs": clamp(o.get("fs"), 1, 30, 6),
        "color": str(o.get("color") or "")[:40],
        "role": role,
        "target": str(o.get("target") or "")[:24],
    }


def clean_question(q):
    kind = q.get("type") if q.get("type") in QTYPES else "quiz"
    answers = strs(q.get("a"), 4)
    ak = strs(q.get("ak"), 4)
    if kind == "truefalse":
        answers = ["True", "False"]
        ak = ["ពិត", "មិនពិត"]
    c = q.get("c", 0)
    c = c if isinstance(c, int) and 0 <= c < max(len(answers), 1) else 0
    out = {
        "q": str(q.get("q") or ""),
        "qk": str(q.get("qk") or ""),
        "img": str(q.get("img") or ""),
        "a": answers,
        "ak": ak,
        "c": c,
        "t": max(5, min(120, int(q.get("t") or 20))),
        "p": int(num(q.get("p"), 500)),
        "type": kind,
        "music": str(q.get("music") or "")[:500],
    }
    if kind == "type":
        out["acc"] = strs(q.get("acc"), 10)
    if kind == "order":
        out["items"] = strs(q.get("items"), 6)
    if kind == "slider":
        lo, hi = num(q.get("min"), 0), num(q.get("max"), 100)
        if hi <= lo:
            hi = lo + 1
        out.update({"min": lo, "max": hi, "step": max(num(q.get("step"), 1), 0.01), "ans": min(max(num(q.get("ans"), lo), lo), hi), "tol": max(num(q.get("tol"), 0), 0)})
    if kind == "match":
        out["pairs"] = [[str(a), str(b)] for a, b in [(x + ["", ""])[:2] for x in (q.get("pairs") or []) if isinstance(x, list)]][:6]
    if kind == "memory":
        out["cards"] = strs(q.get("cards"), 8)
    if kind == "canvas":
        out["mode"] = "drag" if q.get("mode") == "drag" else "tap"
        out["bg"] = str(q.get("bg") or "")[:300]
        out["objs"] = [clean_obj(o) for o in (q.get("objs") or []) if isinstance(o, dict)][:40]
    if kind == "lesson":
        out["text"] = str(q.get("text") or "")[:600]
        out["textk"] = str(q.get("textk") or "")[:600]
        out["p"] = 0
    return out


TRACKS = {"happy", "calm", "party", "adventure", "magic", "groove", "none"}
LAYOUTS = {"grid", "balloon", "scene"}


def clean_settings(v):
    v = v if isinstance(v, dict) else {}
    track = v.get("track") if v.get("track") in TRACKS else "happy"
    layout = v.get("layout") if v.get("layout") in LAYOUTS else "grid"
    return {
        "shuffle": bool(v.get("shuffle", False)),
        "shuffleAnswers": bool(v.get("shuffleAnswers", True)),
        "speedBonus": bool(v.get("speedBonus", True)),
        "music": bool(v.get("music", True)) and track != "none",
        "track": track,
        "musicUrl": str(v.get("musicUrl") or "")[:500],
        "layout": layout,
        "race": bool(v.get("race", False)),
        "limit": max(0, min(100, int(num(v.get("limit"), 0)))),
        "dark": bool(v.get("dark", True)),
        "hint": str(v.get("hint") or "")[:120],
    }


def serialize(row, full=False):
    data = {
        "id": row["id"],
        "slug": row["slug"],
        "title": row["title"],
        "titleK": row["title_km"],
        "emoji": row["emoji"],
        "gradient": row["gradient"],
        "author": row["author"],
        "subject": row["subject"],
        "age": row["age"],
        "kind": row["kind"],
        "engine": row["engine"],
        "skin": row["skin"],
        "device": row["device"],
        "status": row["status"],
        "visibility": row["visibility"],
        "ownerId": row["owner_id"],
        "version": row["version"],
        "plays": row["plays"],
        "rating": row["rating"],
        "featured": bool(row["featured"]),
        "builtin": bool(row["builtin"]),
        "updated": row["updated"],
        "created": row["created"],
        "questionCount": len(json.loads(row["questions"] or "[]")),
        "link": f"/g/{row['slug']}",
    }
    if full or row["builtin"]:
        data["config"] = json.loads(row["config"] or "null")
    if full:
        data["questions"] = json.loads(row["questions"] or "[]")
    return data


def can_edit(row):
    return row["owner_id"] == g.user["id"] or ROLE_RANK.get(g.user["role"], 0) >= ROLE_RANK["admin"]


def snapshot(row, note):
    execute(
        "INSERT INTO game_versions(game_id,version,note,snapshot,created) VALUES(?,?,?,?,?)",
        (row["id"], row["version"], note, json.dumps(serialize(row, True), ensure_ascii=False), now()),
    )


def find(ident):
    if str(ident).isdigit():
        return query_one("SELECT * FROM games WHERE id=?", (int(ident),))
    return query_one("SELECT * FROM games WHERE slug=?", (ident,))


@bp.get("/games")
def list_games():
    where, args = ["status='published'", "visibility='public'"], []
    q = (request.args.get("q") or "").strip().lower()
    if q:
        where.append("(LOWER(title) LIKE ? OR LOWER(subject) LIKE ? OR LOWER(kind) LIKE ? OR LOWER(author) LIKE ?)")
        args += [f"%{q}%"] * 4
    for field, col in (("subject", "subject"), ("kind", "kind"), ("author", "author"), ("engine", "engine")):
        if request.args.get(field):
            where.append(f"{col}=?")
            args.append(request.args[field])
    if request.args.get("featured") == "1":
        where.append("featured=1")
    if request.args.get("custom") == "1":
        where.append("builtin=0")
    order = {"new": "created DESC", "rating": "rating DESC", "plays": "plays DESC"}.get(request.args.get("sort"), "builtin DESC, position ASC, plays DESC")
    limit = max(1, min(200, int(request.args.get("limit") or 100)))
    rows = query(f"SELECT * FROM games WHERE {' AND '.join(where)} ORDER BY {order} LIMIT ?", (*args, limit))
    return jsonify(games=[serialize(r) for r in rows])


@bp.get("/games/<ident>")
@optional_user
def get_game(ident):
    row = find(ident)
    if not row:
        return jsonify(error="Game not found"), 404
    visible = row["status"] == "published" and row["visibility"] in ("public", "link")
    if not visible and not (g.user and can_edit(row)):
        return jsonify(error="Game not found"), 404
    return jsonify(game=serialize(row, True))


@bp.get("/studio/games")
@login_required("creator")
def my_games():
    if request.args.get("all") == "1" and ROLE_RANK.get(g.user["role"], 0) >= ROLE_RANK["admin"]:
        rows = query("SELECT * FROM games ORDER BY updated DESC")
    else:
        rows = query("SELECT * FROM games WHERE owner_id=? ORDER BY updated DESC", (g.user["id"],))
    total = len(rows)
    per = request.args.get("per", "")
    page, pages = 1, 1
    if per.isdigit() and int(per) > 0:
        per = min(int(per), 200)
        pages = max(1, -(-total // per))
        page = request.args.get("page", "1")
        page = min(max(int(page) if page.isdigit() else 1, 1), pages)
        rows = rows[(page - 1) * per : page * per]
    return jsonify(games=[serialize(r) for r in rows], total=total, page=page, pages=pages)


@bp.post("/studio/games")
@login_required("creator")
def create_game():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "Untitled game").strip()
    questions = [clean_question(q) for q in data.get("questions") or []]
    stamp = now()
    skin = data.get("skin") if data.get("skin") in SKINS else "jungle"
    gid = execute(
        "INSERT INTO games(slug,title,title_km,emoji,gradient,author,subject,age,kind,engine,skin,device,questions,status,visibility,owner_id,created,updated,position,config) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            slugify(title), title, data.get("titleK") or "", data.get("emoji") or "🎮", data.get("gradient") or "#dcd3ff,#a592f5",
            g.user["name"], data.get("subject") or "General", data.get("age") or "4–7", data.get("kind") or "Quiz", "quiz", skin,
            data.get("device") if data.get("device") in DEVICES else "phone", json.dumps(questions, ensure_ascii=False),
            "draft", "private", g.user["id"], stamp, stamp, 100,
            json.dumps({"settings": clean_settings(data.get("settings"))}),
        ),
    )
    return jsonify(game=serialize(query_one("SELECT * FROM games WHERE id=?", (gid,)), True)), 201


@bp.get("/studio/games/<int:gid>")
@login_required("creator")
def studio_get(gid):
    row = query_one("SELECT * FROM games WHERE id=?", (gid,))
    if not row or not can_edit(row):
        return jsonify(error="Game not found"), 404
    return jsonify(game=serialize(row, True))


@bp.put("/studio/games/<int:gid>")
@login_required("creator")
def update_game(gid):
    row = query_one("SELECT * FROM games WHERE id=?", (gid,))
    if not row or not can_edit(row):
        return jsonify(error="Game not found"), 404
    data = request.get_json(silent=True) or {}
    fields = {}
    mapping = {"title": "title", "titleK": "title_km", "emoji": "emoji", "gradient": "gradient", "subject": "subject", "age": "age", "kind": "kind"}
    for key, col in mapping.items():
        if key in data:
            fields[col] = str(data[key])
    if data.get("skin") in SKINS:
        fields["skin"] = data["skin"]
    if data.get("device") in DEVICES:
        fields["device"] = data["device"]
    if "questions" in data:
        if not isinstance(data["questions"], list):
            return jsonify(error="questions must be a list"), 400
        fields["questions"] = json.dumps([clean_question(q) for q in data["questions"]], ensure_ascii=False)
    if "settings" in data:
        fields["config"] = json.dumps({"settings": clean_settings(data["settings"])})
    if not fields:
        return jsonify(game=serialize(row, True))
    fields["updated"] = now()
    sets = ", ".join(f"{k}=?" for k in fields)
    execute(f"UPDATE games SET {sets} WHERE id=?", (*fields.values(), gid))
    return jsonify(game=serialize(query_one("SELECT * FROM games WHERE id=?", (gid,)), True), saved=True)


def problems(row):
    qs = json.loads(row["questions"] or "[]")
    found = []
    if not row["title"].strip():
        found.append("Add a title")
    if row["engine"] == "quiz":
        if not qs:
            found.append("Add at least 1 question")
        for i, q in enumerate(qs, 1):
            kind = q.get("type", "quiz")
            if kind == "canvas":
                objs = q.get("objs", [])
                if q.get("mode") == "drag":
                    ids = {o["id"] for o in objs if o["role"] == "target"}
                    if not [o for o in objs if o["role"] == "drag" and o["target"] in ids]:
                        found.append(f"Scene {i} needs a draggable item linked to a drop target")
                elif not [o for o in objs if o["role"] == "correct"]:
                    found.append(f"Scene {i} needs at least one correct item")
            if kind == "lesson" and not (q["q"].strip() or q.get("text", "").strip()):
                found.append(f"Lesson {i} is empty")
            if kind in ("quiz", "truefalse", "type", "order", "slider") and not q["q"].strip():
                found.append(f"Question {i} has no text")
            if kind == "quiz" and len([a for a in q["a"] if a.strip()]) < 2:
                found.append(f"Question {i} needs at least 2 answers")
            if kind == "type" and not [a for a in q.get("acc", []) if a.strip()]:
                found.append(f"Question {i} needs an accepted answer")
            if kind == "order" and len([a for a in q.get("items", []) if a.strip()]) < 2:
                found.append(f"Question {i} needs at least 2 items to order")
            if kind == "match" and len([p for p in q.get("pairs", []) if p[0].strip() and p[1].strip()]) < 2:
                found.append(f"Question {i} needs at least 2 pairs")
            if kind == "memory" and len([c for c in q.get("cards", []) if c.strip()]) < 2:
                found.append(f"Question {i} needs at least 2 cards")
    return found


@bp.post("/studio/games/<int:gid>/publish")
@login_required("creator")
def publish(gid):
    row = query_one("SELECT * FROM games WHERE id=?", (gid,))
    if not row or not can_edit(row):
        return jsonify(error="Game not found"), 404
    data = request.get_json(silent=True) or {}
    issues = problems(row)
    if issues:
        return jsonify(error="Fix these first: " + "; ".join(issues), issues=issues), 422
    visibility = data.get("visibility") if data.get("visibility") in VISIBILITY else "public"
    if visibility == "private":
        execute("UPDATE games SET status='draft', visibility='private', updated=? WHERE id=?", (now(), gid))
    else:
        version = row["version"] + (1 if row["status"] == "published" else 0)
        execute("UPDATE games SET status='published', visibility=?, version=?, updated=? WHERE id=?", (visibility, version, now(), gid))
        snapshot(query_one("SELECT * FROM games WHERE id=?", (gid,)), data.get("note") or "Published")
    return jsonify(game=serialize(query_one("SELECT * FROM games WHERE id=?", (gid,)), True))


@bp.post("/studio/games/<int:gid>/unpublish")
@login_required("creator")
def unpublish(gid):
    row = query_one("SELECT * FROM games WHERE id=?", (gid,))
    if not row or not can_edit(row):
        return jsonify(error="Game not found"), 404
    execute("UPDATE games SET status='draft', visibility='private', updated=? WHERE id=?", (now(), gid))
    return jsonify(game=serialize(query_one("SELECT * FROM games WHERE id=?", (gid,))))


@bp.delete("/studio/games/<int:gid>")
@login_required("creator")
def delete_game(gid):
    row = query_one("SELECT * FROM games WHERE id=?", (gid,))
    if not row or not can_edit(row):
        return jsonify(error="Game not found"), 404
    if row["builtin"] and ROLE_RANK.get(g.user["role"], 0) < ROLE_RANK["admin"]:
        return jsonify(error="Only admins can delete built-in games"), 403
    execute("DELETE FROM games WHERE id=?", (gid,))
    execute("DELETE FROM game_versions WHERE game_id=?", (gid,))
    execute("DELETE FROM results WHERE game_id=?", (gid,))
    return jsonify(ok=True)


@bp.post("/studio/games/<int:gid>/duplicate")
@login_required("creator")
def duplicate(gid):
    row = query_one("SELECT * FROM games WHERE id=?", (gid,))
    if not row or not can_edit(row):
        return jsonify(error="Game not found"), 404
    stamp = now()
    title = row["title"] + " (copy)"
    new_id = execute(
        "INSERT INTO games(slug,title,title_km,emoji,gradient,author,subject,age,kind,engine,skin,device,questions,status,visibility,owner_id,created,updated,position) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (slugify(title), title, row["title_km"], row["emoji"], row["gradient"], g.user["name"], row["subject"], row["age"], row["kind"],
         "quiz", row["skin"], row["device"], row["questions"], "draft", "private", g.user["id"], stamp, stamp, 100),
    )
    return jsonify(game=serialize(query_one("SELECT * FROM games WHERE id=?", (new_id,)), True)), 201


@bp.get("/studio/games/<int:gid>/versions")
@login_required("creator")
def versions(gid):
    row = query_one("SELECT * FROM games WHERE id=?", (gid,))
    if not row or not can_edit(row):
        return jsonify(error="Game not found"), 404
    rows = query("SELECT id,version,note,created FROM game_versions WHERE game_id=? ORDER BY id DESC", (gid,))
    return jsonify(versions=[dict(r) for r in rows])


@bp.post("/studio/games/<int:gid>/restore/<int:vid>")
@login_required("creator")
def restore(gid, vid):
    row = query_one("SELECT * FROM games WHERE id=?", (gid,))
    ver = query_one("SELECT * FROM game_versions WHERE id=? AND game_id=?", (vid, gid))
    if not row or not ver or not can_edit(row):
        return jsonify(error="Version not found"), 404
    snap = json.loads(ver["snapshot"])
    execute("UPDATE games SET title=?, title_km=?, skin=?, questions=?, updated=? WHERE id=?",
            (snap["title"], snap["titleK"], snap["skin"], json.dumps(snap["questions"], ensure_ascii=False), now(), gid))
    return jsonify(game=serialize(query_one("SELECT * FROM games WHERE id=?", (gid,)), True))


@bp.get("/studio/games/<int:gid>/export")
@login_required("creator")
def export(gid):
    row = query_one("SELECT * FROM games WHERE id=?", (gid,))
    if not row or not can_edit(row):
        return jsonify(error="Game not found"), 404
    return jsonify(serialize(row, True))


@bp.post("/studio/import")
@login_required("creator")
def import_game():
    if request.is_json:
        data = request.get_json(silent=True) or {}
        questions = [clean_question(q) for q in data.get("questions") or []]
        title = data.get("title") or "Imported game"
    else:
        text = (request.files["file"].read().decode("utf-8-sig") if "file" in request.files else request.form.get("csv", ""))
        questions = []
        for row in csv.reader(io.StringIO(text)):
            if len(row) < 6 or row[0].strip().lower() in ("question", "q"):
                continue
            try:
                correct = int(row[5]) - 1
            except ValueError:
                continue
            questions.append(clean_question({"q": row[0], "a": row[1:5], "c": correct}))
        title = request.form.get("title") or "Imported game"
    if not questions:
        return jsonify(error="No questions found. CSV columns: question, answer1, answer2, answer3, answer4, correct (1-4)"), 400
    stamp = now()
    gid = execute(
        "INSERT INTO games(slug,title,author,engine,questions,status,visibility,owner_id,created,updated,position) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (slugify(title), title, g.user["name"], "quiz", json.dumps(questions, ensure_ascii=False), "draft", "private", g.user["id"], stamp, stamp, 100),
    )
    return jsonify(game=serialize(query_one("SELECT * FROM games WHERE id=?", (gid,)), True)), 201


@bp.post("/studio/ai/generate")
@login_required("creator")
def ai_generate():
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "animals").lower()
    count = max(1, min(10, int(data.get("count") or 5)))
    key = next((k for k in AI_BANK if k in topic or topic in k), None)
    pool = list(AI_BANK[key]) if key else [item for items in AI_BANK.values() for item in items]
    random.shuffle(pool)
    out = []
    for q, answers, correct, img in pool[:count]:
        out.append({"q": q, "qk": "", "img": img, "a": answers, "ak": ["", "", "", ""], "c": correct, "t": 20, "p": 500, "type": "quiz"})
    return jsonify(questions=out, topic=topic)
