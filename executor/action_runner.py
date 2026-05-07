"""HITL-guarded manifest executor with DPI scaling and shell adaptation.

Loads a JSON action manifest produced by the understander and drives
PyAutoGUI / subprocess to carry out each step.  Every action is gated by
a human-in-the-loop overlay so the operator can approve, reject, or skip.
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Any

import pyautogui

from executor.hitl_overlay import HitlDecision, show_hitl_overlay
from executor.os_adapter import get_adapter

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


class ActionRunner:
    """Orchestrates manifest execution with per-step HITL approval."""

    def __init__(self) -> None:
        self._adapter = get_adapter()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute_manifest(self, manifest_path: Path) -> None:
        """Load the JSON manifest at *manifest_path* and execute every action.

        Each action triggers a HITL overlay.  The operator can:

        * **APPROVE** — run the action.
        * **REJECT** — abort the entire sequence.
        * **SKIP**   — skip to the next action.

        A 1-second pause is inserted between consecutive actions.
        """
        manifest_path = manifest_path.resolve()
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")

        with open(manifest_path, "r", encoding="utf-8") as fh:
            actions: list[dict[str, Any]] = json.load(fh)

        if not isinstance(actions, list):
            raise ValueError(
                f"Manifest root must be a JSON array, got {type(actions).__name__}."
            )

        logging.info("[action_runner] Loaded manifest with %d action(s).", len(actions))

        for action in actions:
            step = action.get("step", "?")
            target = action.get("target_description", "unknown target")

            decision = show_hitl_overlay(
                f"Execute Step {step}: {target}?",
                timeout=60.0,
            )

            if decision is HitlDecision.REJECT:
                logging.warning("[action_runner] Step %s REJECTED — aborting sequence.", step)
                return

            if decision is HitlDecision.SKIP:
                logging.info("[action_runner] Step %s SKIPPED.", step)
                continue

            if decision is HitlDecision.APPROVE:
                self._execute_single(action)
                time.sleep(1.0)
                continue

            # Timeout / unknown decision → treat as skip to be safe
            logging.info(
                "[action_runner] Step %s timed out or returned no decision — skipping.",
                step,
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute_single(self, action: dict[str, Any]) -> None:
        """Dispatch a single action dict to the appropriate handler."""
        action_type = str(action.get("action_type") or "").strip().lower()
        step = action.get("step", "?")

        if action_type == "click":
            coords = action.get("coordinates")
            if not isinstance(coords, (list, tuple)) or len(coords) < 2:
                logging.error(
                    "[action_runner] Step %s: click requires [x, y] coordinates.", step
                )
                return
            x = int(coords[0])
            y = int(coords[1])
            pyautogui.click(x, y)
            logging.info(
                "[action_runner] Step %s: clicked at (%d, %d).",
                step, x, y,
            )
            return

        if action_type == "type":
            text = str(action.get("value") or "")
            if not text:
                logging.warning(
                    "[action_runner] Step %s: type action has empty value.", step
                )
                return
            pyautogui.write(text, interval=0.05)
            logging.info("[action_runner] Step %s: typed %d character(s).", step, len(text))
            return

        if action_type == "wait":
            raw_value = action.get("value")
            try:
                duration = float(raw_value) if raw_value is not None else 1.0
            except (TypeError, ValueError):
                duration = 1.0
            duration = max(0.0, duration)
            time.sleep(duration)
            logging.info("[action_runner] Step %s: waited %.2f second(s).", step, duration)
            return

        if action_type == "shell":
            raw_cmd = str(action.get("value") or "")
            if not raw_cmd:
                logging.warning(
                    "[action_runner] Step %s: shell action has empty command.", step
                )
                return
            adapted = self._adapter.build_shell_command(raw_cmd)
            logging.info(
                "[action_runner] Step %s: running shell: %s", step, " ".join(adapted)
            )
            result = subprocess.run(
                adapted, capture_output=True, text=True, check=False
            )
            if result.returncode != 0:
                logging.warning(
                    "[action_runner] Step %s: shell exited with rc=%d | stderr: %s",
                    step,
                    result.returncode,
                    result.stderr.strip(),
                )
            else:
                logging.info(
                    "[action_runner] Step %s: shell completed successfully.", step
                )
            return

        if action_type == "hotkey":
            raw_keys = action.get("value")
            if isinstance(raw_keys, str):
                keys = [k.strip() for k in raw_keys.split("+") if k.strip()]
            elif isinstance(raw_keys, list):
                keys = [str(k).strip() for k in raw_keys if str(k).strip()]
            else:
                keys = []
            if not keys:
                logging.warning(
                    "[action_runner] Step %s: hotkey has no valid keys.", step
                )
                return
            pyautogui.hotkey(*keys)
            logging.info(
                "[action_runner] Step %s: pressed hotkey %s.", step, " + ".join(keys)
            )
            return

        if action_type == "scroll":
            amount = int(action.get("value") or 0)
            pyautogui.scroll(amount)
            logging.info(
                "[action_runner] Step %s: scrolled %d units.", step, amount
            )
            return

        logging.warning(
            "[action_runner] Step %s: unsupported action_type '%s'.",
            step,
            action_type,
        )
