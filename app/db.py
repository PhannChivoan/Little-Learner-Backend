import json
import os
import re
from datetime import datetime, timezone

import psycopg
from flask import current_app, g
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from werkzeug.security import generate_password_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'kid',
    emoji TEXT NOT NULL DEFAULT '🐻',
    status TEXT NOT NULL DEFAULT 'active',
    created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS games (
    id SERIAL PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    title_km TEXT NOT NULL DEFAULT '',
    emoji TEXT NOT NULL DEFAULT '🎮',
    gradient TEXT NOT NULL DEFAULT '#dcd3ff,#a592f5',
    author TEXT NOT NULL DEFAULT 'Critter Team',
    subject TEXT NOT NULL DEFAULT 'General',
    age TEXT NOT NULL DEFAULT '4–7',
    kind TEXT NOT NULL DEFAULT 'Quiz',
    engine TEXT NOT NULL DEFAULT 'quiz',
    skin TEXT NOT NULL DEFAULT 'jungle',
    device TEXT NOT NULL DEFAULT 'phone',
    questions TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'draft',
    visibility TEXT NOT NULL DEFAULT 'private',
    owner_id INTEGER,
    version INTEGER NOT NULL DEFAULT 1,
    plays INTEGER NOT NULL DEFAULT 0,
    rating DOUBLE PRECISION NOT NULL DEFAULT 0,
    featured INTEGER NOT NULL DEFAULT 0,
    builtin INTEGER NOT NULL DEFAULT 0,
    position INTEGER NOT NULL DEFAULT 0,
    config TEXT NOT NULL DEFAULT '',
    created TEXT NOT NULL,
    updated TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS game_versions (
    id SERIAL PRIMARY KEY,
    game_id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    snapshot TEXT NOT NULL,
    created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS results (
    id SERIAL PRIMARY KEY,
    game_id INTEGER NOT NULL,
    user_id INTEGER,
    player TEXT NOT NULL DEFAULT 'Guest',
    score INTEGER NOT NULL DEFAULT 0,
    correct INTEGER NOT NULL DEFAULT 0,
    total INTEGER NOT NULL DEFAULT 0,
    seconds INTEGER NOT NULL DEFAULT 0,
    created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS live_sessions (
    id SERIAL PRIMARY KEY,
    pin TEXT NOT NULL UNIQUE,
    game_id INTEGER NOT NULL,
    host_id INTEGER,
    mode TEXT NOT NULL DEFAULT 'classic',
    status TEXT NOT NULL DEFAULT 'lobby',
    current INTEGER NOT NULL DEFAULT 0,
    created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS live_players (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    emoji TEXT NOT NULL DEFAULT '🐻',
    score INTEGER NOT NULL DEFAULT 0,
    created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS docs (
    id SERIAL PRIMARY KEY,
    coll TEXT NOT NULL,
    data TEXT NOT NULL,
    created TEXT NOT NULL,
    updated TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS purchases (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    reward_id INTEGER NOT NULL,
    cost INTEGER NOT NULL,
    created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS saved_games (
    user_id INTEGER NOT NULL,
    game_id INTEGER NOT NULL,
    created TEXT NOT NULL,
    PRIMARY KEY (user_id, game_id)
);
CREATE TABLE IF NOT EXISTS classrooms (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    teacher_id INTEGER NOT NULL,
    code TEXT NOT NULL UNIQUE,
    created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS class_members (
    class_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    created TEXT NOT NULL,
    PRIMARY KEY (class_id, user_id)
);
CREATE TABLE IF NOT EXISTS assignments (
    id SERIAL PRIMARY KEY,
    class_id INTEGER NOT NULL,
    game_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    due TEXT NOT NULL DEFAULT '',
    created TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ll_docs_coll ON docs(coll);
CREATE INDEX IF NOT EXISTS idx_ll_games_status ON games(status, visibility);
CREATE INDEX IF NOT EXISTS idx_ll_results_game ON results(game_id);
"""

BUILTIN_GAMES = [
    ("count-the-critters", "Count the Critters", "រាប់សត្វ", "🐰", "#ffd9a8,#ffb36b", "Critter Team", "Math", "4–6", "Counting", "count", 12400, 4.8),
    ("abc-safari", "ABC Safari", "សាហ្វារីអក្សរ", "🦁", "#dcd3ff,#a592f5", "Critter Team", "Letters", "4–7", "Matching", "abc", 9800, 4.9),
    ("animals-of-cambodia", "Animals of Cambodia", "សត្វនៅកម្ពុជា", "🐘", "#bdf1e6,#62d2bd", "Teacher Sophea", "Science", "5–8", "Quiz", "cambodia", 7100, 4.7),
    ("balloon-colors", "Balloon Colors", "ប៉េងប៉ោងពណ៌", "🎈", "#ffc9de,#ff8fbd", "Critter Team", "Colors", "3–5", "Balloon Pop", "balloon", 6500, 4.6),
    ("memory-farm", "Memory Farm", "ចងចាំស្រុកស្រែ", "🐮", "#cdf3ae,#8ed35a", "Mr. Dara", "Memory", "4–7", "Memory", "memory", 5200, 4.8),
    ("ocean-quiz", "Ocean Quiz", "សំណួរមហាសមុទ្រ", "🐳", "#c7e8ff,#6db8ff", "Ms. Chenda", "Science", "6–9", "Quiz", "ocean", 4400, 4.5),
    ("space-math-race", "Space Math Race", "ប្រណាំងគណិតអវកាស", "🚀", "#d9d0ff,#8b7bff", "Mr. Rithy", "Math", "6–9", "Race", "space", 3900, 4.7),
    ("shape-sorter", "Shape Sorter", "ដាក់រូបរាង", "🔺", "#ffe3a3,#ffc24d", "Critter Team", "Shapes", "3–6", "Sorting", "shape", 3100, 4.4),
    ("khmer-letters", "Khmer Letters", "អក្សរខ្មែរ", "ក", "#ffd0d0,#ff8f8f", "Teacher Sophea", "Language", "5–8", "Tracing", "khmer", 2800, 4.9),
    ("dino-time", "Dino Time", "ពេលដាយណូស័រ", "🦖", "#d4f5c4,#7fd36b", "Ms. Bopha", "Science", "5–8", "Hidden Object", "dino", 2200, 4.6),
]

THEMES = [
    ("jungle", "Jungle", "🌴", "#2fbf63,#8fe08a"),
    ("ocean", "Ocean", "🐠", "#3d8bff,#9be0ff"),
    ("space", "Space", "🚀", "#1a1446,#6b4fd8"),
    ("candy", "Candy", "🍭", "#ff5fa2,#ffc9de"),
    ("farm", "Farm", "🚜", "#f5a300,#ffe58a"),
    ("desert", "Desert", "🏜️", "#ff8a2b,#ffd9a8"),
]

SEED_DOCS = {
    "settings": [
        {"key": "platform_name", "value": "Critter Academy", "group": "general"},
        {"key": "default_language", "value": "en", "group": "general"},
        {"key": "parental_consent_under_13", "value": True, "group": "child safety"},
        {"key": "chat_enabled", "value": False, "group": "child safety"},
        {"key": "daily_play_limit_minutes", "value": 60, "group": "child safety"},
    ],
}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


TABLE_NAMES = ["users", "games", "game_versions", "results", "live_sessions", "live_players", "docs", "purchases", "saved_games", "classrooms", "class_members", "assignments"]
TABLE_SUFFIX = os.environ.get("DB_TABLE_SUFFIX", "_little-learner")
_TABLE_RE = re.compile(r"\b(FROM|JOIN|INTO|UPDATE|TABLE(?:\s+IF\s+NOT\s+EXISTS)?|ON|TRUNCATE)(\s+)(" + "|".join(TABLE_NAMES) + r")\b(?!\.)", re.I)


def table_name(name):
    return f'"{name}{TABLE_SUFFIX}"' if TABLE_SUFFIX else name


def tr(sql):
    if not TABLE_SUFFIX:
        return sql
    return _TABLE_RE.sub(lambda m: m.group(1) + m.group(2) + table_name(m.group(3).lower()), sql)


SERIAL_TABLES = {"users", "games", "game_versions", "results", "live_sessions", "live_players", "docs", "purchases", "classrooms", "assignments"}
_pool = None


def dsn():
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return url
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    name = os.environ.get("DB_NAME", "little_learner")
    user = os.environ.get("DB_USER", "postgres")
    password = os.environ.get("DB_PASSWORD", "")
    ssl = os.environ.get("DB_SSLMODE", "")
    parts = [f"host={host}", f"port={port}", f"dbname={name}", f"user={user}"]
    if password:
        parts.append(f"password={password}")
    if ssl:
        parts.append(f"sslmode={ssl}")
    return " ".join(parts)


def ensure_database():
    if os.environ.get("DATABASE_URL", "").strip():
        return
    try:
        psycopg.connect(dsn(), connect_timeout=5).close()
        return
    except psycopg.OperationalError as error:
        if "does not exist" not in str(error):
            raise
    name = os.environ.get("DB_NAME", "little_learner")
    admin = dsn().replace(f"dbname={name}", "dbname=postgres")
    with psycopg.connect(admin, autocommit=True, connect_timeout=5) as conn:
        conn.execute(f'CREATE DATABASE "{name}"')


class Conn:
    def __init__(self, raw):
        self.raw = raw

    def execute(self, sql, args=()):
        sql = tr(sql)
        if args:
            return self.raw.execute(sql.replace("%", "%%").replace("?", "%s"), list(args))
        return self.raw.execute(sql)

    def commit(self):
        return None


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_db():
    if "db" not in g:
        g.db = Conn(_pool.getconn())
    return g.db


def close_db(e=None):
    conn = g.pop("db", None)
    if conn is not None:
        _pool.putconn(conn.raw)


def init_app(app):
    global _pool
    ensure_database()
    if _pool is None:
        _pool = ConnectionPool(dsn(), min_size=1, max_size=int(os.environ.get("DB_POOL_MAX", "10")), kwargs={"autocommit": True, "row_factory": dict_row}, open=True)
        _pool.wait(timeout=15)
    app.teardown_appcontext(close_db)


def query(sql, args=()):
    return get_db().execute(sql, args).fetchall()


def query_one(sql, args=()):
    return get_db().execute(sql, args).fetchone()


def execute(sql, args=()):
    conn = get_db()
    found = re.match(r"\s*INSERT\s+INTO\s+(\w+)", sql, re.I)
    if found and found.group(1).lower() in SERIAL_TABLES and "returning" not in sql.lower():
        return conn.execute(sql + " RETURNING id", args).fetchone()["id"]
    conn.execute(sql, args)
    return None


def init_db():
    conn = get_db()
    conn.execute(SCHEMA)
    conn.execute("ALTER TABLE games ADD COLUMN IF NOT EXISTS config TEXT NOT NULL DEFAULT ''")
    if not query_one("SELECT id FROM users LIMIT 1"):
        seed(conn)
    fill_builtin_config(conn)
    from .builtin_convert import convert_builtin_games

    convert_builtin_games(conn)
    sync_templates(conn)


OLD_TEMPLATE_NAMES = {"Quiz", "True / False", "Matching", "Memory match", "Drag & drop", "Sorting", "Fill the blank", "Word search", "Spelling", "Sequencing", "Hidden object", "Balloon pop", "Counting", "Trace the letter", "Story choices", "Spin the wheel"}


def sync_templates(conn):
    from .templates_data import TEMPLATE_DATA

    rows = conn.execute("SELECT id,data FROM docs WHERE coll='templates'").fetchall()
    have = set()
    for r in rows:
        d = json.loads(r["data"])
        if "type" not in d and d.get("name") in OLD_TEMPLATE_NAMES:
            conn.execute("DELETE FROM docs WHERE id=?", (r["id"],))
            continue
        if "type" not in d:
            d.update({"type": "quiz", "skin": "jungle", "subject": "General", "age": "4–7", "questions": []})
            conn.execute("UPDATE docs SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), r["id"]))
        have.add(d.get("name"))
    stamp = now()
    for t in TEMPLATE_DATA:
        if t["name"] in have:
            continue
        conn.execute("INSERT INTO docs(coll,data,created,updated) VALUES(?,?,?,?)", ("templates", json.dumps({**t, "enabled": True}, ensure_ascii=False), stamp, stamp))
    conn.commit()


def fill_builtin_config(conn):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "builtin_config.json")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        defaults = json.load(f)
    for slug, cfg in defaults.items():
        conn.execute("UPDATE games SET config=? WHERE slug=? AND builtin=1 AND config=''", (json.dumps(cfg, ensure_ascii=False), slug))
    conn.commit()


def seed(conn):
    stamp = now()
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@critter.academy")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    conn.execute(
        "INSERT INTO users(name,email,password_hash,role,emoji,status,created) VALUES(?,?,?,?,?,?,?)",
        ("Admin", admin_email, generate_password_hash(admin_password), "super_admin", "🦊", "active", stamp),
    )
    for i, (slug, title, title_km, emoji, grad, author, subject, age, kind, engine, plays, rating) in enumerate(BUILTIN_GAMES):
        conn.execute(
            "INSERT INTO games(slug,title,title_km,emoji,gradient,author,subject,age,kind,engine,status,visibility,plays,rating,builtin,featured,position,created,updated) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (slug, title, title_km, emoji, grad, author, subject, age, kind, engine, "published", "public", plays, rating, 1, 1 if i < 2 else 0, i, stamp, stamp),
        )
    for key, name, emoji, colors in THEMES:
        conn.execute(
            "INSERT INTO docs(coll,data,created,updated) VALUES(?,?,?,?)",
            ("themes", json.dumps({"key": key, "name": name, "emoji": emoji, "colors": colors, "enabled": True}, ensure_ascii=False), stamp, stamp),
        )
    for coll, items in SEED_DOCS.items():
        for item in items:
            conn.execute("INSERT INTO docs(coll,data,created,updated) VALUES(?,?,?,?)", (coll, json.dumps(item, ensure_ascii=False), stamp, stamp))
    conn.commit()
