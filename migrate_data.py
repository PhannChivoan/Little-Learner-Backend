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
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                os.environ.setdefault(key.strip(), value)


load_env()

from app import db

TABLES = ["users", "games", "game_versions", "results", "live_sessions", "live_players", "docs", "purchases", "saved_games", "classrooms", "class_members", "assignments"]

USAGE = """Copy data into the MySQL database set in .env (or DATABASE_URL).

  python migrate_data.py --sqlite [path\\to\\file.db]     from an old SQLite file (default instance/little_learner.db)
  python migrate_data.py --postgres "postgresql://user:password@host:5432/dbname"
                                                          from a PostgreSQL database (needs: pip install "psycopg[binary]")
  add --replace to overwrite a MySQL database that already has data
"""


def read_sqlite(path):
    if not os.path.exists(path):
        sys.exit(f"SQLite file not found: {path}")
    lite = sqlite3.connect(path)
    lite.row_factory = sqlite3.Row

    def rows(table):
        cols = [r[1] for r in lite.execute(f"PRAGMA table_info({table})")]
        if not cols:
            return None, []
        return cols, [tuple(r) for r in lite.execute(f"SELECT {', '.join(cols)} FROM {table}")]

    return rows


def read_postgres(dsn):
    try:
        import psycopg
    except ImportError:
        sys.exit('Install the PostgreSQL driver first: pip install "psycopg[binary]"')
    pg = psycopg.connect(dsn)

    def rows(table):
        for name in (f"{table}{db.TABLE_SUFFIX}", table):
            cur = pg.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position", (name,))
            cols = [r[0] for r in cur]
            if cols:
                data = pg.execute('SELECT ' + ", ".join(f'"{c}"' for c in cols) + f' FROM "{name}"').fetchall()
                return cols, [tuple(r) for r in data]
        return None, []

    return rows


def main():
    args = sys.argv[1:]
    if not args or args[0] not in ("--sqlite", "--postgres"):
        sys.exit(USAGE)
    replace = "--replace" in args
    rest = [a for a in args[1:] if a != "--replace"]
    if args[0] == "--sqlite":
        default = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "little_learner.db")
        read = read_sqlite(rest[0] if rest else default)
    else:
        if not rest:
            sys.exit(USAGE)
        read = read_postgres(rest[0])

    db.ensure_database()
    conn = db.connect()
    try:
        cur = conn.cursor()
        for statement in [p.strip() for p in db.SCHEMA.split(";") if p.strip()]:
            try:
                cur.execute(db.tr(statement))
            except db.pymysql.err.OperationalError as error:
                if error.args[0] != 1061:
                    raise
        cur.execute(db.tr("SELECT COUNT(*) AS n FROM users"))
        if cur.fetchone()["n"] and not replace:
            sys.exit("The MySQL database already has data. Run again with --replace to overwrite it.")
        for table in TABLES:
            target = db.table_name(table)
            cur.execute(f"TRUNCATE TABLE {target}")
        for table in TABLES:
            target = db.table_name(table)
            source_cols, rows = read(table)
            if source_cols is None:
                print(f"{table}: not in the source, skipped")
                continue
            cur.execute(f"SHOW COLUMNS FROM {target}")
            have = {r["Field"] for r in cur.fetchall()}
            keep = [i for i, c in enumerate(source_cols) if c in have]
            names = [source_cols[i] for i in keep]
            if rows:
                marks = ", ".join(["%s"] * len(names))
                cols = ", ".join(f"`{n}`" for n in names)
                cur.executemany(f"INSERT INTO {target} ({cols}) VALUES ({marks})", [tuple(r[i] for i in keep) for r in rows])
            print(f"{table}: {len(rows)} rows")
    finally:
        conn.close()
    print("Done. Start the backend as usual.")


if __name__ == "__main__":
    main()
