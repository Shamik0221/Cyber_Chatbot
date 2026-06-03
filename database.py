"""
database.py
Cloud PostgreSQL (Supabase) access with persistent connection pool.
"""

import os
import json
from typing import Optional
from dotenv import load_dotenv
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Create ONE shared connection pool when this module first loads.
# minconn=1 means: keep at least 1 connection open and ready.
# maxconn=5 means: scale up to 5 if many requests come at once.
_pool = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=5,
    dsn=DATABASE_URL,
)


def _get_conn():
    """Borrow a connection from the pool."""
    return _pool.getconn()


def _put_conn(conn):
    """Return a connection to the pool when done."""
    _pool.putconn(conn)


def save_message(
    message_id: str,
    user_id: str,
    role: str,
    text: str,
    metadata: Optional[dict] = None,
) -> None:
    """Save a message row to chat_history."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_history (message_id, user_id, role, text, metadata)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    message_id,
                    user_id,
                    role,
                    text,
                    json.dumps(metadata) if metadata else None,
                ),
            )
            conn.commit()
    finally:
        _put_conn(conn)


def get_history(user_id: str, limit: int = 15) -> list:
    """Fetch the most recent messages for a user (oldest first)."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT message_id, user_id, role, text, created_at, metadata
                FROM chat_history
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
            rows = cur.fetchall()
            rows.reverse()
            for row in rows:
                row["createdAt"] = row.pop("created_at").isoformat()
                row["messageId"] = row.pop("message_id")
            return rows
    finally:
        _put_conn(conn)


def test_connection() -> bool:
    """Quick health check."""
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        _put_conn(conn)
        return True
    except Exception as e:
        print(f"DB connection failed: {e}")
        return False