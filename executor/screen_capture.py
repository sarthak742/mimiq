"""Desktop screen capture utilities for the Mimiq execution engine."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pyautogui
from PIL import Image


def capture_desktop(save_path: str = "temp_screenshot.png", region: tuple | None = None) -> str:
    """Capture the desktop and save to disk. Returns the absolute path."""
    screenshot = pyautogui.screenshot(region=region)

    absolute_path = os.path.abspath(save_path)
    os.makedirs(os.path.dirname(absolute_path) or ".", exist_ok=True)
    screenshot.save(absolute_path)

    return absolute_path


def get_active_window_region() -> tuple | None:
    """Return the bounding box of the currently focused window, or None for full screen.

    TODO: Implement pygetwindow-based focus detection to return the exact
    (left, top, width, height) tuple of the active window for precise
    cropping during multi-app workspace phases.
    """
    return None
