"""Human-in-the-loop (HITL) decision overlay for Mimiq.

Provides a thread-safe state machine that external UI or CLI code can
poll while the agent waits for human approval, rejection, or skip.
"""

from __future__ import annotations

import threading
import time
from enum import Enum


class HitlDecision(Enum):
    """Discrete decisions a human operator can make."""

    APPROVE = "approve"
    REJECT = "reject"
    SKIP = "skip"


# ------------------------------------------------------------------
# Global shared state
# ------------------------------------------------------------------

_lock = threading.Lock()
_overlay_state: dict[str, object] = {
    "pending": False,
    "decision": None,
    "message": "",
}


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def show_hitl_overlay(message: str, timeout: float = 60.0) -> HitlDecision | None:
    """Block until the human makes a decision or *timeout* expires.

    Sets the global overlay state to *pending* and records the prompt
    *message*.  Polls every 0.5 seconds for a decision.  Returns the
    decision enum value, or ``None`` on timeout.
    """
    with _lock:
        _overlay_state["pending"] = True
        _overlay_state["decision"] = None
        _overlay_state["message"] = message

    deadline = time.monotonic() + max(0.0, timeout)
    while time.monotonic() < deadline:
        with _lock:
            decision = _overlay_state.get("decision")
            if decision is not None:
                _overlay_state["pending"] = False
                return decision  # type: ignore[return-value]
        time.sleep(0.5)

    # Timeout — clear pending flag
    with _lock:
        _overlay_state["pending"] = False
    return None


def set_overlay_decision(decision: HitlDecision) -> None:
    """Thread-safe setter for the overlay decision.

    Typically invoked by a UI button handler or CLI input loop running
    in a separate thread.
    """
    with _lock:
        _overlay_state["decision"] = decision
