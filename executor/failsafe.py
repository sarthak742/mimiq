"""PyAutoGUI failsafe wrapper for Mimiq.

PyAutoGUI's built-in failsafe aborts execution when the mouse cursor is
moved to any of the four screen corners.  This module provides a thin,
explicit API around that flag so callers can opt in and query status.
"""

from __future__ import annotations

import logging

import pyautogui


def start_failsafe() -> None:
    """Enable PyAutoGUI's corner-detection failsafe and log the kill-switch."""
    pyautogui.FAILSAFE = True
    logging.info(
        "Failsafe enabled: move the mouse cursor to any screen corner "
        "to immediately halt execution."
    )


def is_failsafe_active() -> bool:
    """Return whether PyAutoGUI's failsafe flag is currently True."""
    return bool(pyautogui.FAILSAFE)
