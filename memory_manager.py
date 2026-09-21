# ==================================================
# JARVIS PERSISTENT MEMORY MANAGER
# ==================================================

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


# ==================================================
# CONFIGURATION
# ==================================================

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "memory.db"

DEFAULT_USER_ID = "default_user"


# ==================================================
# DATABASE CONNECTION
# ==================================================

def get_connection():
    connection = sqlite3.connect(
        DB_PATH,
        timeout=10
    )

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA journal_mode=WAL"
    )

    connection.execute(
        "PRAGMA foreign_keys=ON"
    )

    return connection


# ==================================================
# DATABASE INITIALIZATION
# ==================================================

def init_database():

    with get_connection() as connection:

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                session_id TEXT,
                user_text TEXT NOT NULL,
                assistant_text TEXT NOT NULL,
                metadata_json TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS context (
                user_id TEXT NOT NULL,
                context_key TEXT NOT NULL,
                context_value_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,

                PRIMARY KEY (
                    user_id,
                    context_key
                )
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_conversations_user
            ON conversations(user_id)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_conversations_created
            ON conversations(created_at)
            """
        )

        connection.commit()


# ==================================================
# TIME
# ==================================================

def utc_now():
    return datetime.now(
        timezone.utc
    ).isoformat()


# ==================================================
# JSON HELPERS
# ==================================================

def serialize(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        default=str
    )


def deserialize(value, default=None):

    if value is None:
        return default

    try:
        return json.loads(value)

    except (
        json.JSONDecodeError,
        TypeError
    ):
        return default


# ==================================================
# SAVE CONVERSATION
# ==================================================

def save_conversation(
    user_text,
    assistant_text,
    metadata=None,
    user_id=DEFAULT_USER_ID,
    session_id=None
):

    init_database()

    with get_connection() as connection:

        connection.execute(
            """
            INSERT INTO conversations (
                user_id,
                session_id,
                user_text,
                assistant_text,
                metadata_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                session_id,
                user_text,
                assistant_text,
                serialize(metadata or {}),
                utc_now()
            )
        )

        connection.commit()


# ==================================================
# GET RECENT CONVERSATIONS
# ==================================================

def get_recent_conversations(
    limit=10,
    user_id=DEFAULT_USER_ID
):

    init_database()

    with get_connection() as connection:

        rows = connection.execute(
            """
            SELECT
                id,
                user_id,
                session_id,
                user_text,
                assistant_text,
                metadata_json,
                created_at
            FROM conversations
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                user_id,
                int(limit)
            )
        ).fetchall()

    rows = list(reversed(rows))

    conversations = []

    for row in rows:

        conversations.append({
            "id": row["id"],
            "user_id": row["user_id"],
            "session_id": row["session_id"],
            "user": row["user_text"],
            "assistant": row["assistant_text"],
            "metadata": deserialize(
                row["metadata_json"],
                {}
            ),
            "timestamp": row["created_at"]
        })

    return conversations


# ==================================================
# SAVE CONTEXT
# ==================================================

def set_context(
    context_key,
    context_value,
    user_id=DEFAULT_USER_ID
):

    init_database()

    with get_connection() as connection:

        connection.execute(
            """
            INSERT INTO context (
                user_id,
                context_key,
                context_value_json,
                updated_at
            )
            VALUES (?, ?, ?, ?)

            ON CONFLICT (
                user_id,
                context_key
            )

            DO UPDATE SET
                context_value_json = excluded.context_value_json,
                updated_at = excluded.updated_at
            """,
            (
                user_id,
                context_key,
                serialize(context_value),
                utc_now()
            )
        )

        connection.commit()


# ==================================================
# GET CONTEXT
# ==================================================

def get_context(
    context_key,
    user_id=DEFAULT_USER_ID,
    default=None
):

    init_database()

    with get_connection() as connection:

        row = connection.execute(
            """
            SELECT context_value_json
            FROM context
            WHERE user_id = ?
              AND context_key = ?
            """,
            (
                user_id,
                context_key
            )
        ).fetchone()

    if not row:
        return default

    return deserialize(
        row["context_value_json"],
        default
    )


# ==================================================
# GET ALL CONTEXT
# ==================================================

def get_all_context(
    user_id=DEFAULT_USER_ID
):

    init_database()

    with get_connection() as connection:

        rows = connection.execute(
            """
            SELECT
                context_key,
                context_value_json,
                updated_at
            FROM context
            WHERE user_id = ?
            ORDER BY context_key
            """,
            (user_id,)
        ).fetchall()

    result = {}

    for row in rows:

        result[row["context_key"]] = {
            "value": deserialize(
                row["context_value_json"],
                None
            ),
            "updated_at": row["updated_at"]
        }

    return result


# ==================================================
# DELETE CONTEXT
# ==================================================

def delete_context(
    context_key,
    user_id=DEFAULT_USER_ID
):

    init_database()

    with get_connection() as connection:

        connection.execute(
            """
            DELETE FROM context
            WHERE user_id = ?
              AND context_key = ?
            """,
            (
                user_id,
                context_key
            )
        )

        connection.commit()


# ==================================================
# GET LAST COMMAND
# ==================================================

def get_last_command(
    user_id=DEFAULT_USER_ID
):

    return get_context(
        "last_command",
        user_id=user_id,
        default=None
    )


# ==================================================
# CLEAR USER MEMORY
# ==================================================

def clear_user_memory(
    user_id=DEFAULT_USER_ID
):

    init_database()

    with get_connection() as connection:

        connection.execute(
            """
            DELETE FROM conversations
            WHERE user_id = ?
            """,
            (user_id,)
        )

        connection.execute(
            """
            DELETE FROM context
            WHERE user_id = ?
            """,
            (user_id,)
        )

        connection.commit()


# ==================================================
# INITIALIZE DATABASE
# ==================================================

init_database()