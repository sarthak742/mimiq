"""Action recovery logic for Mimiq.

Provides a three-tier recovery strategy:
1. Press Escape and wait.
2. Re-plan via cloud_brain /playbook endpoint.
3. Escalate to human-in-the-loop.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Final

import pyautogui
import requests

from config import MIMIQ_STEP_GENERATOR_URL, PRIMARY_VISION_URL


@dataclass
class RecoveryResult:
    success: bool
    action_taken: str
    retry_playbook: dict | None


class RecoveryManager:
    """Three-tier recovery manager for failed actions."""

    def attempt_recovery(
        self,
        phase_contract: dict,
        failure_reason: str,
        attempt: int,
    ) -> RecoveryResult:
        logging.warning(
            "[recovery] Attempt %d | Failure: '%s'", attempt, failure_reason
        )

        if attempt == 1:
            pyautogui.press("escape")
            time.sleep(1.0)
            return RecoveryResult(
                success=True,
                action_taken="escape",
                retry_playbook=None,
            )

        if attempt == 2:
            if not PRIMARY_VISION_URL:
                raise ValueError(
                    "PRIMARY_VISION_URL not configured — AMD endpoint required."
                )
            try:
                resp = requests.post(
                    MIMIQ_STEP_GENERATOR_URL,
                    json={
                        "phase_contract": phase_contract,
                        "recent_state": {
                            "current_phase_failure": failure_reason,
                            "attempt": attempt,
                        },
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                retry_playbook = resp.json()
                return RecoveryResult(
                    success=True,
                    action_taken="replanned",
                    retry_playbook=retry_playbook,
                )
            except Exception as exc:
                logging.warning("[recovery] Re-plan request failed: %s", exc)
                return RecoveryResult(
                    success=False,
                    action_taken="replan_failed",
                    retry_playbook=None,
                )

        return RecoveryResult(
            success=False,
            action_taken="escalate",
            retry_playbook=None,
        )


# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------

_recovery_lock: Final[threading.Lock] = threading.Lock()
_recovery_instance: RecoveryManager | None = None


def get_recovery_manager() -> RecoveryManager:
    global _recovery_instance  # noqa: PLW0603
    if _recovery_instance is not None:
        return _recovery_instance
    with _recovery_lock:
        if _recovery_instance is None:
            _recovery_instance = RecoveryManager()
    return _recovery_instance
