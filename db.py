import os
import sqlite3

DB_PATH = os.environ.get("DB_PATH", "/data/ha_monitor.db")


def get_db():
    if DB_PATH != ":memory:":
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS instances (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                token TEXT NOT NULL,
                email TEXT,
                managed INTEGER NOT NULL DEFAULT 0
            )
        """)
        try:
            conn.execute("ALTER TABLE instances ADD COLUMN managed INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass


def get_instances():
    with get_db() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM instances").fetchall()]


def upsert_instance(id, name, url, token, email, managed=False):
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO instances (id, name, url, token, email, managed)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET name=excluded.name, url=excluded.url, token=excluded.token, email=excluded.email, managed=excluded.managed
        """,
            (id, name, url, token, email, 1 if managed else 0),
        )


def delete_instance(id):
    with get_db() as conn:
        conn.execute("DELETE FROM instances WHERE id = ?", (id,))
