import os
import json
from typing import Optional
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    """Open a new database connection."""
    return psycopg2.connect(DATABASE_URL)


def save_message(
    message_id: str,
    user_id: str,
    role: str,
    text: str,
    metadata: Optional[dict] = None,
) -> None:
    """Save a single message (user or assistant) to the database."""
    conn = get_connection()
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
        conn.close()


def get_history(user_id: str, limit: int = 15) -> list:
    """Fetch the most recent messages for a user, oldest first."""
    conn = get_connection()
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
            # Reverse to chronological order (oldest first) — better for chat UI
            rows.reverse()
            # Convert datetime to ISO string for JSON
            for row in rows:
                row["createdAt"] = row.pop("created_at").isoformat()
                row["messageId"] = row.pop("message_id")
            return rows
    finally:
        conn.close()


def test_connection() -> bool:
    """Quick health check — returns True if DB is reachable."""
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        conn.close()
        return True
    except Exception as e:
        print(f"DB connection failed: {e}")
        return False