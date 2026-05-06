"""Desktop screen capture utilities for the Mimiq execution engine.

Provides a context-manager class for scoped capture sessions and a
convenience standalone function for one-off screenshots.
"""

from __future__ import annotations

import time
from pathlib import Path
from types import TracebackType

from PIL import ImageGrab


def _make_filename() -> str:
    """Return a unique PNG filename based on the current wall-clock time."""
    timestamp = int(time.time() * 1000)
    return f"frame_{timestamp}.png"


def capture(save_dir: Path) -> Path:
    """Grab the full desktop and save a PNG under *save_dir*.

    The directory is created automatically if it does not exist.
    Returns the absolute ``Path`` of the saved file.
    """
    save_dir = save_dir.resolve()
    save_dir.mkdir(parents=True, exist_ok=True)

    screenshot = ImageGrab.grab(all_screens=True)
    dest = save_dir / _make_filename()
    screenshot.save(dest, format="PNG")
    return dest


class ScreenCapture:
    """Context-manager for a single scoped desktop capture.

    Usage::

        with ScreenCapture(Path("./shots")) as shot:
            print(f"Saved to {shot}")
    """

    def __init__(self, save_dir: Path) -> None:
        self.save_dir = save_dir.resolve()
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self._saved: Path | None = None

    def __enter__(self) -> Path:
        screenshot = ImageGrab.grab(all_screens=True)
        dest = self.save_dir / _make_filename()
        screenshot.save(dest, format="PNG")
        self._saved = dest
        return dest

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """No cleanup required — the PNG persists on disk."""
        return None
