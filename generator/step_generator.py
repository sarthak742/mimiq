# FILE: generator/step_generator.py
"""Generator client that proxies all AI calls to cloud_brain HTTP routes."""

from __future__ import annotations

import logging
import threading
from typing import Final

import requests

from config import CLOUD_BRAIN_PORT, PRIMARY_VISION_URL

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


class StepGenerator:
    """Thin proxy to cloud_brain endpoints with AMD guardrails."""

    @property
    def _brain_url(self) -> str:
        return f"http://127.0.0.1:{CLOUD_BRAIN_PORT}"

    def _amd_guard(self) -> None:
        if not PRIMARY_VISION_URL:
            raise ValueError(
                "PRIMARY_VISION_URL not configured — AMD endpoint required."
            )

    def generate_single_step(
        self,
        phase_contract: dict,
        recent_state: dict | None = None,
        milestone_context: dict | None = None,
    ) -> dict:
        """POST to ``/playbook`` and return the JSON response."""
        self._amd_guard()
        resp = requests.post(
            f"{self._brain_url}/playbook",
            json={
                "os_name": "Windows",
                "video_url": "",
                "phase_contract": phase_contract,
                "recent_state": recent_state or {},
                "milestone_context": milestone_context or {},
            },
            timeout=15,
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"cloud_brain call failed: {resp.status_code} {resp.text[:200]}"
            )
        return resp.json()

    def generate(self, manifest: dict, phase_index: int) -> dict:
        """Fetch the phase at *phase_index* and generate a playbook for it."""
        phases = manifest.get("phases") or []
        if not (0 <= phase_index < len(phases)):
            raise IndexError(
                f"phase_index {phase_index} out of range ({len(phases)} phases)"
            )
        return self.generate_single_step(phase_contract=phases[phase_index])

    def generate_workspace_setup(
        self,
        target_workspace: list[str],
        transcript_summary: str = "",
        bootstrap_cwd: str = "",
    ) -> dict:
        """POST to ``/setup`` and return the workspace bootstrap playbook."""
        self._amd_guard()
        resp = requests.post(
            f"{self._brain_url}/setup",
            json={
                "os_name": "Windows",
                "video_url": "",
                "target_workspace": target_workspace,
                "transcript_summary": transcript_summary,
                "bootstrap_cwd": bootstrap_cwd,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"cloud_brain call failed: {resp.status_code} {resp.text[:200]}"
            )
        return resp.json()


# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------

_generator_lock: Final[threading.Lock] = threading.Lock()
_generator_instance: StepGenerator | None = None


def get_generator() -> StepGenerator:
    global _generator_instance  # noqa: PLW0603
    if _generator_instance is not None:
        return _generator_instance
    with _generator_lock:
        if _generator_instance is None:
            _generator_instance = StepGenerator()
    return _generator_instance
