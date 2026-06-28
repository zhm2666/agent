"""SQLite 映射表：user_id + session_id → thread_id + OpenTelemetry 追踪"""

import sqlite3
import uuid
from typing import Optional

# 懒加载 tracer
_tracer: Optional = None


def _get_tracer():
    global _tracer
    if _tracer is None:
        from opentelemetry import trace
        _tracer = trace.get_tracer("database")
    return _tracer


def get_connection():
    return sqlite3.connect("agent.db", check_same_thread=False)


def init_db():
    tracer = _get_tracer()
    with tracer.start_as_current_span("db.init_db"):
        conn = get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_threads (
                thread_id   TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL,
                session_id  TEXT NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, session_id)
            )
        """)
        conn.commit()
        conn.close()


def get_or_create_thread(user_id: str, session_id: str) -> str:
    tracer = _get_tracer()
    with tracer.start_as_current_span(
        "db.get_or_create_thread",
        attributes={
            "db.operation": "upsert",
            "db.table": "conversation_threads",
            "user.id": user_id,
            "session.id": session_id,
        },
    ) as span:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT thread_id FROM conversation_threads WHERE user_id=? AND session_id=?",
            (user_id, session_id),
        )
        row = cursor.fetchone()

        if row:
            conn.close()
            span.set_attribute("db.result", "found")
            span.set_attribute("thread.id", row[0])
            return row[0]

        thread_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO conversation_threads (thread_id, user_id, session_id) VALUES (?, ?, ?)",
            (thread_id, user_id, session_id),
        )
        conn.commit()
        conn.close()

        span.set_attribute("db.result", "created")
        span.set_attribute("thread.id", thread_id)
        return thread_id


def list_user_sessions(user_id: str) -> list:
    tracer = _get_tracer()
    with tracer.start_as_current_span(
        "db.list_user_sessions",
        attributes={
            "db.operation": "select",
            "db.table": "conversation_threads",
            "user.id": user_id,
        },
    ) as span:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT session_id, thread_id, created_at FROM conversation_threads WHERE user_id=? ORDER BY created_at DESC",
            (user_id,),
        )
        rows = cursor.fetchall()
        conn.close()

        span.set_attribute("db.result_count", len(rows))
        return [
            {"session_id": r[0], "thread_id": r[1], "created_at": r[2]}
            for r in rows
        ]
