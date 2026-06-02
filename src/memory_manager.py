"""SQLite-backed long-term memory manager."""

from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .config import get_settings
from .utils import ensure_dir, simple_tokenize, utc_now_iso


TRIVIAL_PATTERNS = [
    r"^\s*(hi|hello|hey|ok|okay|thanks|thank you|cool|great)\s*[.!]?\s*$",
    r"^\s*what is .+\?\s*$",
]

SAVE_PATTERNS = [
    (r"\b(i am|i'm) (new|a beginner|beginner|learning|studying)\b", "learning_profile"),
    (r"\b(i prefer|please use|explain with|teach me with)\b", "preference"),
    (r"\b(i am building|i'm building|my project|working on)\b", "project_context"),
    (r"\b(bias-variance|gradient descent|neural network|data-centric|machine learning)\b.*\b(right now|currently|learning|studying|project)\b", "learning_topic"),
]


class MemoryManager:
    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or get_settings().sqlite_memory_db
        self.init_db()

    def connect(self) -> sqlite3.Connection:
        ensure_dir(self.db_path.parent)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=MEMORY")
        except sqlite3.OperationalError:
            conn.close()
            raise
        return conn

    @contextmanager
    def session(self):
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        with self.session() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    importance INTEGER DEFAULT 3,
                    created_at TEXT,
                    updated_at TEXT
                );

                CREATE TABLE IF NOT EXISTS conversation_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    created_at TEXT
                );
                """
            )

    def ensure_user(self, user_id: str) -> None:
        with self.session() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (user_id, created_at) VALUES (?, ?)",
                (user_id, utc_now_iso()),
            )

    def save_memory(self, user_id: str, memory_type: str, content: str, importance: int = 3) -> None:
        content = content.strip()
        if not content:
            return
        self.ensure_user(user_id)
        now = utc_now_iso()
        with self.session() as conn:
            existing = conn.execute(
                "SELECT id FROM memories WHERE user_id = ? AND lower(content) = lower(?)",
                (user_id, content),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE memories SET updated_at = ?, importance = MAX(importance, ?) WHERE id = ?",
                    (now, importance, existing["id"]),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO memories (user_id, memory_type, content, importance, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, memory_type, content, importance, now, now),
                )

    def get_relevant_memories(self, user_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        self.ensure_user(user_id)
        query_tokens = set(simple_tokenize(query))
        with self.session() as conn:
            rows = conn.execute(
                """
                SELECT id, memory_type, content, importance, created_at, updated_at
                FROM memories
                WHERE user_id = ?
                ORDER BY importance DESC, updated_at DESC
                """,
                (user_id,),
            ).fetchall()

        scored: list[tuple[float, dict[str, Any]]] = []
        for row in rows:
            memory = dict(row)
            memory_tokens = set(simple_tokenize(memory["content"]))
            overlap = len(query_tokens & memory_tokens)
            score = overlap + 0.2 * int(memory.get("importance", 3))
            scored.append((score, memory))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [memory for score, memory in scored[:limit] if score > 0]

    def get_all_memories(self, user_id: str) -> list[dict[str, Any]]:
        try:
            self.ensure_user(user_id)
            with self.session() as conn:
                rows = conn.execute(
                    """
                    SELECT id, memory_type, content, importance, created_at, updated_at
                    FROM memories
                    WHERE user_id = ?
                    ORDER BY updated_at DESC, importance DESC
                    """,
                    (user_id,),
                ).fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error:
            return []

    def search_memories(self, user_id: str, query: str) -> list[dict[str, Any]]:
        query = query.strip()
        if not query:
            return self.get_all_memories(user_id)
        try:
            self.ensure_user(user_id)
            pattern = f"%{query}%"
            with self.session() as conn:
                rows = conn.execute(
                    """
                    SELECT id, memory_type, content, importance, created_at, updated_at
                    FROM memories
                    WHERE user_id = ?
                      AND (content LIKE ? OR memory_type LIKE ?)
                    ORDER BY updated_at DESC, importance DESC
                    """,
                    (user_id, pattern, pattern),
                ).fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error:
            return []

    def update_memory(self, memory_id: int, user_id: str, new_content: str, new_importance: int) -> bool:
        content = new_content.strip()
        if not content:
            return False
        importance = max(1, min(5, int(new_importance)))
        try:
            with self.session() as conn:
                result = conn.execute(
                    """
                    UPDATE memories
                    SET content = ?, importance = ?, updated_at = ?
                    WHERE id = ? AND user_id = ?
                    """,
                    (content, importance, utc_now_iso(), memory_id, user_id),
                )
            return result.rowcount > 0
        except (sqlite3.Error, ValueError):
            return False

    def delete_memory(self, memory_id: int, user_id: str) -> bool:
        try:
            with self.session() as conn:
                result = conn.execute(
                    "DELETE FROM memories WHERE id = ? AND user_id = ?",
                    (memory_id, user_id),
                )
            return result.rowcount > 0
        except sqlite3.Error:
            return False

    def clear_user_memory(self, user_id: str) -> None:
        with self.session() as conn:
            conn.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM conversation_summaries WHERE user_id = ?", (user_id,))

    def extract_memory_candidate(self, user_message: str, assistant_response: str = "") -> dict[str, Any] | None:
        message = user_message.strip()
        if len(message) < 12:
            return None
        lower = message.lower()
        if any(re.match(pattern, lower) for pattern in TRIVIAL_PATTERNS):
            return None
        for pattern, memory_type in SAVE_PATTERNS:
            if re.search(pattern, lower):
                content = message.rstrip(".")
                return {"memory_type": memory_type, "content": content, "importance": 4}
        return None


def init_db() -> None:
    MemoryManager().init_db()


def save_memory(user_id: str, memory_type: str, content: str, importance: int = 3) -> None:
    MemoryManager().save_memory(user_id, memory_type, content, importance)


def get_relevant_memories(user_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
    return MemoryManager().get_relevant_memories(user_id, query, limit)


def get_all_memories(user_id: str) -> list[dict[str, Any]]:
    return MemoryManager().get_all_memories(user_id)


def search_memories(user_id: str, query: str) -> list[dict[str, Any]]:
    return MemoryManager().search_memories(user_id, query)


def update_memory(memory_id: int, user_id: str, new_content: str, new_importance: int) -> bool:
    return MemoryManager().update_memory(memory_id, user_id, new_content, new_importance)


def delete_memory(memory_id: int, user_id: str) -> bool:
    return MemoryManager().delete_memory(memory_id, user_id)


def clear_user_memory(user_id: str) -> None:
    MemoryManager().clear_user_memory(user_id)


def extract_memory_candidate(user_message: str, assistant_response: str = "") -> dict[str, Any] | None:
    return MemoryManager().extract_memory_candidate(user_message, assistant_response)
