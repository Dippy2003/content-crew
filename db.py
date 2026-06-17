"""Postgres-backed storage for generated articles (replaces the local outputs/ folder for the web app)."""

import os
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
                SELECT filename, topic, created_at
                FROM articles
                WHERE user_email = %s
                ORDER BY created_at DESC;
                """,
                (user_email,),
            )
            return [dict(row) for row in cur.fetchall()]


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
