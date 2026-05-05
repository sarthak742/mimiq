"""Translate Cloud Brain payloads into physical OS interactions via pyautogui."""

from __future__ import annotations

import logging
import threading
import time

import pyautogui

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5

_execution_lock = threading.Lock()

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

_SHORT_COMMANDS = {"ls", "clear", "pwd", "npm i", "npm install"}


def execute_action(action: dict) -> bool:
    """Execute a single action dict and return True on success."""
    if not isinstance(action, dict):
        logging.error("Action must be a dict, got %s", type(action).__name__)
        return False

    action_type = str(action.get("type") or "").strip().lower()

    if action_type == "click":
        coords = action.get("coordinates")
        if not isinstance(coords, list) or len(coords) < 2:
            logging.error("Click action requires a coordinates list of at least 2 ints.")
            return False
        x = int(coords[0])
        y = int(coords[1])
        pyautogui.click(x, y)
        logging.info("Executed click at (%d, %d)", x, y)
        return True

    if action_type == "type":
        text = str(action.get("text") or "").strip()
        if not text:
            logging.error("Type action requires non-empty text.")
            return False

        press_enter = bool(action.get("press_enter"))

        # Short-command fix: force Enter for common shell commands
        if text in _SHORT_COMMANDS and not press_enter:
            press_enter = True

        pyautogui.write(text, interval=0.05)
        if press_enter:
            pyautogui.press("enter")
        logging.info("Typed text (press_enter=%s)", press_enter)
        return True

    if action_type == "hotkey":
        keys = action.get("keys")
        if not isinstance(keys, list) or not keys:
            logging.error("Hotkey action requires a non-empty keys list.")
            return False
        clean_keys = [str(key).strip() for key in keys if str(key).strip()]
        if not clean_keys:
            logging.error("Hotkey action has no valid keys after cleaning.")
            return False
        pyautogui.hotkey(*clean_keys)
        logging.info("Executed hotkey: %s", " + ".join(clean_keys))
        return True

    if action_type == "sleep":
        duration = float(action.get("duration") or action.get("seconds") or 1.0)
        duration = max(0.0, duration)
        time.sleep(duration)
        logging.info("Slept for %.2f seconds", duration)
        return True

    logging.error("Unsupported action type: '%s'", action_type)
    return False


def execute_playbook(playbook_payload: dict) -> bool:
    """Execute a full playbook under the global execution lock. Return True on success."""
    try:
        if not isinstance(playbook_payload, dict):
            logging.error("Playbook payload must be a dict.")
            return False

        steps = playbook_payload.get("playbook")
        if not isinstance(steps, list) or not steps:
            logging.error("Playbook payload must contain a non-empty 'playbook' list.")
            return False

        with _execution_lock:
            for step_index, step in enumerate(steps, start=1):
                if not isinstance(step, dict):
                    logging.warning("Step %d is not a dict; skipping.", step_index)
                    continue

                actions = step.get("actions")
                if not isinstance(actions, list) or not actions:
                    logging.warning("Step %d has no actions; skipping.", step_index)
                    continue

                step_title = str(step.get("title") or f"Step {step_index}").strip()
                logging.info("Executing step %d: %s", step_index, step_title)

                for action_index, action in enumerate(actions, start=1):
                    success = execute_action(action)
                    if not success:
                        logging.error(
                            "Step %d (%s) action %d failed: %s",
                            step_index,
                            step_title,
                            action_index,
                            action,
                        )
                        return False

        logging.info("Playbook executed successfully.")
        return True
    except Exception as exc:
        logging.error("Playbook execution failed: %s", exc)
        return False
