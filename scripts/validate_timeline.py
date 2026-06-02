"""Validate timeline JSON used by AndrewAI."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import get_settings
from src.timeline.timeline_loader import REQUIRED_FIELDS, load_timeline


def main() -> int:
    settings = get_settings()
    events = load_timeline(settings.timeline_file)
    if not events:
        print(f"No valid timeline events found in {settings.timeline_file}.")
        return 1
    for event in events:
        missing = REQUIRED_FIELDS - set(event)
        if missing:
            print(f"Missing fields {sorted(missing)} in event: {event}")
            return 1
    print(f"Validated {len(events)} timeline events from {settings.timeline_file}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
