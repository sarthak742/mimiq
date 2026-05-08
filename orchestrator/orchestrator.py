# FILE: orchestrator/orchestrator.py
"""End-to-end pipeline orchestrator for Mimiq.

Routes all AI calls through :class:`StepGenerator` (cloud_brain HTTP),
executes actions via :class:`ActionRunner`, and verifies results locally.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from executor.action_runner import ActionRunner
from executor.failsafe import start_failsafe
from executor.hitl_overlay import HitlDecision, show_hitl_overlay
from executor.recovery import get_recovery_manager
from executor.screen_capture import capture
from executor.verification import verify_state_change
from generator.step_generator import get_generator
from utils.reporter import MimiqReporter, StepRecord
from utils.state_manager import get_manager as get_state_manager

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


class Orchestrator:
    """Coordinates frame capture, action execution, verification, recovery."""

    def __init__(self, work_root: Path, state_path: Path | None = None) -> None:
        self.work_root = Path(work_root)
        self.state_path = state_path or (self.work_root / "state.json")
        self._runner = ActionRunner()
        self._reporter: MimiqReporter | None = None

    # ------------------------------------------------------------------
    # Step-level execution
    # ------------------------------------------------------------------

    def execute_step(self, phase: dict, step: dict) -> bool:
        """Execute every action in *step*, capture before/after, verify."""
        frames_dir = self.work_root / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)

        before = capture(frames_dir / "before")

        actions = step.get("actions") or []
        for action in actions:
            self._runner._execute_single(action)
            time.sleep(0.3)

        after = capture(frames_dir / "after")

        result = verify_state_change(
            before_path=before,
            after_path=after,
            success_signals=phase.get("success_signals", []),
            failure_signals=phase.get("failure_signals", []),
            mode=phase.get("verification_mode", "ocr_focus"),
        )
        logging.info("[orchestrator] Verification result: %s", result)
        return bool(result.get("success", False))

    # ------------------------------------------------------------------
    # Playbook-level execution
    # ------------------------------------------------------------------

    def run_playbook(self, playbook: dict, phase: dict) -> bool:
        """Run every step in *playbook* with retry / recovery / HITL."""
        max_retries = playbook.get("max_retries", 1)
        steps = playbook.get("playbook") or []

        for step in steps:
            success = self.execute_step(phase, step)
            if success:
                continue

            for attempt in range(1, max_retries + 2):
                result = get_recovery_manager().attempt_recovery(
                    phase_contract=phase,
                    failure_reason="step failed",
                    attempt=attempt,
                )
                if result.action_taken == "escalate":
                    decision = show_hitl_overlay(
                        "Step failed. Approve skip or reject?",
                        timeout=60.0,
                    )
                    if decision is HitlDecision.REJECT:
                        return False
                    break  # skip on APPROVE or SKIP
                if result.retry_playbook:
                    return self.run_playbook(result.retry_playbook, phase)
                success = self.execute_step(phase, step)
                if success:
                    break

        return True

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def run_pipeline(self, goal: str, manifest: dict) -> bool:
        """Run the complete Mimiq pipeline from *manifest*."""
        start_failsafe()
        state_mgr = get_state_manager()
        saved = state_mgr.load(self.state_path)
        resume_idx = saved.get("current_phase_index", 0) if saved else 0

        phases = manifest.get("phases") or []
        for idx in range(resume_idx, len(phases)):
            phase = phases[idx]
            logging.info(
                "[orchestrator] Phase %d / %d: %s",
                idx + 1,
                len(phases),
                phase.get("description", "unknown"),
            )

            # 1. Workspace setup
            setup_playbook = get_generator().generate_workspace_setup(
                target_workspace=phase.get("required_workspace", []),
            )
            self.run_playbook(setup_playbook, phase)

            # 2. Phase playbook
            phase_playbook = get_generator().generate_single_step(
                phase_contract=phase,
            )
            ok = self.run_playbook(phase_playbook, phase)

            # 3. Persist state
            state_mgr.save(
                {
                    "goal": goal,
                    "current_phase_index": idx + 1,
                    "completed_phases": list(range(idx + 1)),
                    "manifest": manifest,
                },
                self.state_path,
            )

            # 4. Report
            if self._reporter is not None:
                self._reporter.add_step(
                    StepRecord(
                        phase_id=phase.get("phase_id", idx),
                        description=phase.get("description", ""),
                        success=ok,
                        action_taken="executed",
                        duration_seconds=0.0,
                        screenshot_path="",
                    )
                )

        logging.info("[orchestrator] Pipeline complete.")
        return True
