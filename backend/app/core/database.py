"""
backend/app/core/database.py — Sloj baze korisnika.

PostgreSQL (Supabase) kad je DATABASE_URL postavljen, inače SQLite.
config.DATABASE_URL se čita dinamički jer startup može aktivirati fallback.
"""

import contextlib
import sqlite3

from backend.app.core import config


def ph() -> str:
    """SQL parameter placeholder — %s za PostgreSQL, ? za SQLite."""
    return "%s" if config.DATABASE_URL else "?"


@contextlib.contextmanager
def db_ctx():
    """Konekcija ka bazi — PostgreSQL (Supabase) ili SQLite (lokalno)."""
    if config.DATABASE_URL:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(config.DATABASE_URL, sslmode="require")
        try:
            yield conn, psycopg2.extras.RealDictCursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(config.DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn, None
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def db_exec(conn, cf, sql: str, params: tuple = ()):
    """Izvršava SQL upit za PostgreSQL ili SQLite."""
    if cf:  # PostgreSQL — koristi cursor
        cur = conn.cursor(cursor_factory=cf)
        cur.execute(sql, params)
        return cur
    return conn.execute(sql, params)


def init_user_db() -> None:
    """Kreira tabelu korisnika ako ne postoji (PostgreSQL ili SQLite).

    Šema mora odgovarati postojećoj `users` tabeli u Supabase projektu
    (poticaji-bih-eu): email, password_hash, full_name, is_active,
    subscription_tier, created_at, last_login.
    """
    _id_col = (
        "id SERIAL PRIMARY KEY"
        if config.DATABASE_URL
        else "id INTEGER PRIMARY KEY AUTOINCREMENT"
    )
    _timestamp_type = "TIMESTAMPTZ" if config.DATABASE_URL else "TEXT"
    with db_ctx() as (conn, cf):
        db_exec(conn, cf, f"""
            CREATE TABLE IF NOT EXISTS users (
                {_id_col},
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                subscription_tier TEXT DEFAULT 'free',
                created_at {_timestamp_type} DEFAULT CURRENT_TIMESTAMP,
                last_login {_timestamp_type}
            )
        """)
