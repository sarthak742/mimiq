# FILE: utils/state_manager.py
"""Persistent run-state manager with atomic writes."""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Final


@dataclass
class RunState:
    goal: str = ""
    video_path: str = ""
    current_phase_index: int = 0
    completed_phases: list[int] = field(default_factory=list)
    manifest: dict = field(default_factory=dict)
    timestamp: str = ""


class StateManager:
    """Atomic JSON read/write for pipeline resumption."""

    def save(self, state: dict, path: Path) -> None:
        """Write *state* to *path* atomically via a temp file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(state)
        if "timestamp" not in payload:
            payload["timestamp"] = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "") + "Z"
            )
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        os.replace(tmp, path)

    def load(self, path: Path) -> dict | None:
        """Load state from *path* or return ``None``."""
        path = Path(path)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def clear(self, path: Path) -> None:
        """Delete the state file if it exists."""
        path = Path(path)
        if path.exists():
            os.remove(path)


# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------

_state_lock: Final[threading.Lock] = threading.Lock()
_state_instance: StateManager | None = None


def get_manager() -> StateManager:
    global _state_instance  # noqa: PLW0603
    if _state_instance is not None:
        return _state_instance
    with _state_lock:
        if _state_instance is None:
            _state_instance = StateManager()
    return _state_instance
