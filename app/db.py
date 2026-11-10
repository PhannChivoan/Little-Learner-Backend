import json
import os
import queue
import re
import ssl
import threading
from urllib.parse import unquote, urlparse
from datetime import datetime, timezone

import pymysql
from flask import g
from pymysql import converters
from pymysql.constants import FIELD_TYPE
from pymysql.cursors import DictCursor
from werkzeug.security import generate_password_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(190) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'kid',
    emoji VARCHAR(32) NOT NULL DEFAULT '🐻',
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created VARCHAR(40) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS games (
    id INT AUTO_INCREMENT PRIMARY KEY,
    slug VARCHAR(190) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    title_km VARCHAR(255) NOT NULL DEFAULT '',
    emoji VARCHAR(32) NOT NULL DEFAULT '🎮',
    gradient VARCHAR(80) NOT NULL DEFAULT '#dcd3ff,#a592f5',
    author VARCHAR(255) NOT NULL DEFAULT 'Critter Team',
    subject VARCHAR(100) NOT NULL DEFAULT 'General',
    age VARCHAR(20) NOT NULL DEFAULT '4–7',
    kind VARCHAR(80) NOT NULL DEFAULT 'Quiz',
    engine VARCHAR(40) NOT NULL DEFAULT 'quiz',
    skin VARCHAR(40) NOT NULL DEFAULT 'jungle',
    device VARCHAR(20) NOT NULL DEFAULT 'phone',
    questions LONGTEXT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    visibility VARCHAR(20) NOT NULL DEFAULT 'private',
    owner_id INT NULL,
    version INT NOT NULL DEFAULT 1,
    plays INT NOT NULL DEFAULT 0,
    rating DOUBLE NOT NULL DEFAULT 0,
    featured INT NOT NULL DEFAULT 0,
    builtin INT NOT NULL DEFAULT 0,
    position INT NOT NULL DEFAULT 0,
    config LONGTEXT NULL,
    created VARCHAR(40) NOT NULL,
    updated VARCHAR(40) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS game_versions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    game_id INT NOT NULL,
    version INT NOT NULL,
    note VARCHAR(255) NOT NULL DEFAULT '',
    snapshot LONGTEXT NOT NULL,
    created VARCHAR(40) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    game_id INT NOT NULL,
    user_id INT NULL,
    player VARCHAR(255) NOT NULL DEFAULT 'Guest',
    score INT NOT NULL DEFAULT 0,
    correct INT NOT NULL DEFAULT 0,
    total INT NOT NULL DEFAULT 0,
    seconds INT NOT NULL DEFAULT 0,
    created VARCHAR(40) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS live_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pin VARCHAR(16) NOT NULL UNIQUE,
    game_id INT NOT NULL,
    host_id INT NULL,
    mode VARCHAR(40) NOT NULL DEFAULT 'classic',
    status VARCHAR(20) NOT NULL DEFAULT 'lobby',
    current INT NOT NULL DEFAULT 0,
    created VARCHAR(40) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS live_players (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    emoji VARCHAR(32) NOT NULL DEFAULT '🐻',
    score INT NOT NULL DEFAULT 0,
    created VARCHAR(40) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS docs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    coll VARCHAR(64) NOT NULL,
    data LONGTEXT NOT NULL,
    created VARCHAR(40) NOT NULL,
    updated VARCHAR(40) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS purchases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    reward_id INT NOT NULL,
    cost INT NOT NULL,
    created VARCHAR(40) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS saved_games (
    user_id INT NOT NULL,
    game_id INT NOT NULL,
    created VARCHAR(40) NOT NULL,
    PRIMARY KEY (user_id, game_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS classrooms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    teacher_id INT NOT NULL,
    code VARCHAR(40) NOT NULL UNIQUE,
    created VARCHAR(40) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS class_members (
    class_id INT NOT NULL,
    user_id INT NOT NULL,
    created VARCHAR(40) NOT NULL,
    PRIMARY KEY (class_id, user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    class_id INT NOT NULL,
    game_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    due VARCHAR(40) NOT NULL DEFAULT '',
    created VARCHAR(40) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX idx_ll_docs_coll ON docs(coll);
CREATE INDEX idx_ll_games_status ON games(status, visibility);
CREATE INDEX idx_ll_results_game ON results(game_id);
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
_TABLE_RE = re.compile(r"\b(FROM|JOIN|INTO|UPDATE|TABLE(?:\s+IF\s+NOT\s+EXISTS)?|ON|TRUNCATE(?:\s+TABLE)?)(\s+)(" + "|".join(TABLE_NAMES) + r")\b(?!\.)", re.I)
_pool = None


def table_name(name):
    return f"`{name}{TABLE_SUFFIX}`"


def tr(sql):
    return _TABLE_RE.sub(lambda m: m.group(1) + m.group(2) + table_name(m.group(3).lower()), sql)


def _number(raw):
    text = raw.decode() if isinstance(raw, bytes) else raw
    return float(text) if "." in text else int(text)


CONVERSIONS = converters.conversions.copy()
CONVERSIONS[FIELD_TYPE.DECIMAL] = _number
CONVERSIONS[FIELD_TYPE.NEWDECIMAL] = _number


def env(*names, default=""):
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return default


def settings():
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        parsed = urlparse(url.replace("mysql+pymysql://", "mysql://"))
        return {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 3306,
            "user": unquote(parsed.username or ""),
            "password": unquote(parsed.password or ""),
            "database": (parsed.path or "").lstrip("/") or env("DB_DATABASE", "DB_NAME", default="little_learner"),
        }
    return {
        "host": env("DB_HOST", default="localhost"),
        "port": int(env("DB_PORT", default="3306")),
        "user": env("DB_USERNAME", "DB_USER", default="root"),
        "password": env("DB_PASSWORD", default=""),
        "database": env("DB_DATABASE", "DB_NAME", default="little_learner"),
    }


def connect(with_database=True):
    cfg = settings()
    if not with_database:
        cfg["database"] = None
    extra = {}
    if os.environ.get("DB_SSLMODE", "").strip().lower() in ("require", "true", "1", "on"):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        extra["ssl"] = context
    return pymysql.connect(**cfg, charset="utf8mb4", cursorclass=DictCursor, autocommit=True, conv=CONVERSIONS, connect_timeout=10, **extra)


def ensure_database():
    try:
        connect().close()
        return
    except pymysql.err.OperationalError as error:
        if error.args[0] != 1049:
            raise
    name = settings()["database"]
    conn = connect(False)
    try:
        conn.cursor().execute(f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    finally:
        conn.close()


class Pool:
    def __init__(self, size):
        self.size = size
        self.made = 0
        self.idle = queue.LifoQueue()
        self.lock = threading.Lock()

    def get(self):
        try:
            conn = self.idle.get_nowait()
        except queue.Empty:
            with self.lock:
                room = self.made < self.size
                if room:
                    self.made += 1
            if room:
                try:
                    return connect()
                except Exception:
                    with self.lock:
                        self.made -= 1
                    raise
            conn = self.idle.get(timeout=15)
        try:
            conn.ping(reconnect=True)
        except Exception:
            conn = connect()
        return conn

    def put(self, conn):
        self.idle.put(conn)


class Conn:
    def __init__(self, raw):
        self.raw = raw

    def execute(self, sql, args=()):
        sql = tr(sql)
        cur = self.raw.cursor()
        if args:
            cur.execute(sql.replace("%", "%%").replace("?", "%s"), list(args))
        else:
            cur.execute(sql)
        return cur

    def commit(self):
        return None


def get_db():
    if "db" not in g:
        g.db = Conn(_pool.get())
    return g.db


def close_db(e=None):
    conn = g.pop("db", None)
    if conn is not None:
        _pool.put(conn.raw)


def init_app(app):
    global _pool
    ensure_database()
    if _pool is None:
        _pool = Pool(int(os.environ.get("DB_POOL_MAX", "10") or 10))
    app.teardown_appcontext(close_db)


def query(sql, args=()):
    return get_db().execute(sql, args).fetchall()


def query_one(sql, args=()):
    return get_db().execute(sql, args).fetchone()


def execute(sql, args=()):
    return get_db().execute(sql, args).lastrowid or None


def create_schema(conn):
    for statement in [part.strip() for part in SCHEMA.split(";") if part.strip()]:
        try:
            conn.execute(statement)
        except pymysql.err.OperationalError as error:
            if error.args[0] != 1061:
                raise


def init_db():
    conn = get_db()
    create_schema(conn)
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
        conn.execute("UPDATE games SET config=? WHERE slug=? AND builtin=1 AND (config IS NULL OR config='')", (json.dumps(cfg, ensure_ascii=False), slug))
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
