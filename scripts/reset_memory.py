"""Reset all long-term memory rows."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import get_settings
from src.memory_manager import MemoryManager


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reset all long-term digital twin memory rows.")
    parser.add_argument(
        "--user-id",
        help="Only clear memory for this user. If omitted, all long-term memories and summaries are cleared.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = get_settings()
    try:
        manager = MemoryManager(settings.sqlite_memory_db)
    except sqlite3.OperationalError:
        for path in [
            settings.sqlite_memory_db,
            Path(f"{settings.sqlite_memory_db}-journal"),
            Path(f"{settings.sqlite_memory_db}-wal"),
            Path(f"{settings.sqlite_memory_db}-shm"),
        ]:
            if path.exists():
                path.unlink()
        manager = MemoryManager(settings.sqlite_memory_db)
    if settings.sqlite_memory_db.exists():
        if args.user_id:
            manager.clear_user_memory(args.user_id)
            print(f"Reset long-term memory for user '{args.user_id}' in {settings.sqlite_memory_db}.")
        else:
            with manager.session() as conn:
                conn.execute("DELETE FROM memories")
                conn.execute("DELETE FROM conversation_summaries")
            print(f"Reset all long-term memory in {settings.sqlite_memory_db}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
