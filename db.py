"""Postgres-backed storage for generated articles (replaces the local outputs/ folder for the web app)."""

import os
import secrets
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

@contextmanager
def get_conn():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS articles (
                    id SERIAL PRIMARY KEY,
                    user_email TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_articles_user_email ON articles (user_email);"
            )
            # share_token is null until the owner enables a public link; added
            # via ALTER so databases created before this column get it too.
            cur.execute(
                "ALTER TABLE articles ADD COLUMN IF NOT EXISTS share_token TEXT;"
            )
            cur.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_share_token "
                "ON articles (share_token) WHERE share_token IS NOT NULL;"
            )


def save_article(user_email: str, filename: str, topic: str, content: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO articles (user_email, filename, topic, content)
                VALUES (%s, %s, %s, %s);
                """,
                (user_email, filename, topic, content),
            )


def list_articles(user_email: str) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT filename, topic, created_at, share_token
                FROM articles
                WHERE user_email = %s
                ORDER BY created_at DESC;
                """,
                (user_email,),
            )
            rows = []
            for row in cur.fetchall():
                row = dict(row)
                # Expose only whether it's shared, never the token itself, in lists.
                row["shared"] = row.pop("share_token") is not None
                rows.append(row)
            return rows


def get_article(user_email: str, filename: str) -> dict | None:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT filename, content
                FROM articles
                WHERE user_email = %s AND filename = %s;
                """,
                (user_email, filename),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def delete_article(user_email: str, filename: str) -> bool:
    """Delete an article owned by the user. Returns True if a row was removed."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM articles
                WHERE user_email = %s AND filename = %s
                RETURNING id;
                """,
                (user_email, filename),
            )
            return cur.fetchone() is not None


def enable_sharing(user_email: str, filename: str) -> str | None:
    """Give the article a public share token (reusing one if already set) and return it."""
    token = secrets.token_urlsafe(16)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE articles
                SET share_token = COALESCE(share_token, %s)
                WHERE user_email = %s AND filename = %s
                RETURNING share_token;
                """,
                (token, user_email, filename),
            )
            row = cur.fetchone()
            return row[0] if row else None


def disable_sharing(user_email: str, filename: str) -> bool:
    """Revoke the public link for an article. Returns True if a row was updated."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE articles
                SET share_token = NULL
                WHERE user_email = %s AND filename = %s
                RETURNING id;
                """,
                (user_email, filename),
            )
            return cur.fetchone() is not None


def get_shared_article(share_token: str) -> dict | None:
    """Look up a publicly shared article by its token. No user scoping (this is the public view)."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT filename, topic, content, created_at
                FROM articles
                WHERE share_token = %s;
                """,
                (share_token,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
