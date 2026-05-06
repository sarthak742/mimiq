"""Pure-logic safety classifier for Mimiq commands.

No AI or network calls.  Every decision is a deterministic prefix match
against the allow- and deny-lists imported from `config.py`.
"""

from __future__ import annotations

import threading
from enum import Enum
from typing import Final

from config import GREEN_COMMANDS, RED_COMMANDS


class SafetyLevel(Enum):
    """Discrete safety tiers for command classification."""

    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class SafetyClassifier:
    """Deterministic command classifier backed by static allow/deny lists."""

    _red: frozenset[str]
    _green: frozenset[str]

    def __init__(
        self,
        *,
        green_commands: frozenset[str] = frozenset(GREEN_COMMANDS),
        red_commands: frozenset[str] = frozenset(RED_COMMANDS),
    ) -> None:
        self._green = green_commands
        self._red = red_commands

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify(self, command: str) -> SafetyLevel:
        """Return the safety level for *command* based on prefix rules.

        Priority:
        1. RED — command starts with any entry in RED_COMMANDS.
        2. GREEN — command starts with any entry in GREEN_COMMANDS.
        3. YELLOW — everything else.
        """
        lowered = command.strip().lower()
        if not lowered:
            return SafetyLevel.YELLOW

        # Check RED first (deny-list has priority)
        for marker in self._red:
            if lowered.startswith(marker.lower()):
                return SafetyLevel.RED

        # Check GREEN next (allow-list)
        for marker in self._green:
            if lowered.startswith(marker.lower()):
                return SafetyLevel.GREEN

        return SafetyLevel.YELLOW

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def is_safe(self, command: str) -> bool:
        """Convenience wrapper: True only for GREEN commands."""
        return self.classify(command) is SafetyLevel.GREEN

    def is_dangerous(self, command: str) -> bool:
        """Convenience wrapper: True only for RED commands."""
        return self.classify(command) is SafetyLevel.RED


# ----------------------------------------------------------------------
# Module-level singleton
# ----------------------------------------------------------------------

_classifier_lock: Final[threading.Lock] = threading.Lock()
_classifier_instance: SafetyClassifier | None = None


def get_classifier() -> SafetyClassifier:
    """Return the thread-safe singleton ``SafetyClassifier``."""
    global _classifier_instance  # noqa: PLW0603

    if _classifier_instance is not None:
        return _classifier_instance

    with _classifier_lock:
        # Double-checked locking
        if _classifier_instance is None:
            _classifier_instance = SafetyClassifier()
    return _classifier_instance
