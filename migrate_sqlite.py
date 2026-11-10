import os
import sqlite3
import sys


def load_env():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


load_env()

import psycopg

from app import db

TABLES = [
    "users",
    "games",
    "game_versions",
    "results",
    "live_sessions",
    "live_players",
    "docs",
    "purchases",
    "saved_games",
    "classrooms",
    "class_members",
    "assignments",
]
SERIAL = {"users", "games", "game_versions", "results", "live_sessions", "live_players", "docs", "purchases", "classrooms", "assignments"}


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "little_learner.db")
    if not os.path.exists(source):
        sys.exit(f"SQLite file not found: {source}")
    db.ensure_database()
    lite = sqlite3.connect(source)
    lite.row_factory = sqlite3.Row
    with psycopg.connect(db.dsn(), autocommit=False) as pg:
        pg.execute(db.tr(db.SCHEMA))
        pg.execute(db.tr("ALTER TABLE games ADD COLUMN IF NOT EXISTS config TEXT NOT NULL DEFAULT ''"))
        existing = pg.execute(db.tr("SELECT COUNT(*) FROM users")).fetchone()[0]
        if existing and "--replace" not in sys.argv:
            sys.exit("The Postgres database already has data. Run again with --replace to overwrite it.")
        pg.execute("TRUNCATE " + ", ".join(db.table_name(t) for t in TABLES) + " RESTART IDENTITY")
        for table in TABLES:
            have = {r[1] for r in lite.execute(f"PRAGMA table_info({table})")}
            if not have:
                print(f"{table}: not in the SQLite file, skipped")
                continue
            target = db.table_name(table)
            pg_cols = [r[0] for r in pg.execute("SELECT column_name FROM information_schema.columns WHERE table_name=%s ORDER BY ordinal_position", (target.strip(chr(34)),))]
            cols = [c for c in pg_cols if c in have]
            rows = lite.execute(f"SELECT {', '.join(cols)} FROM {table}").fetchall()
            marks = ", ".join(["%s"] * len(cols))
            with pg.cursor() as cur:
                cur.executemany(f"INSERT INTO {target} ({', '.join(cols)}) VALUES ({marks})", [tuple(r) for r in rows])
            if table in SERIAL and rows:
                pg.execute(f"SELECT setval(pg_get_serial_sequence(%s, 'id'), (SELECT MAX(id) FROM {target}))", (target,))
            print(f"{table}: {len(rows)} rows")
        pg.commit()
    print("Done. Start the backend as usual.")


if __name__ == "__main__":
    main()
