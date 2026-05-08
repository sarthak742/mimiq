# FILE: understander/frame_describer.py
"""Frame-to-text describer using the vision model via cloud_brain /propose."""

from __future__ import annotations

import base64
import io
import logging
import threading
from pathlib import Path
from typing import Final

import requests
from PIL import Image

from config import CLOUD_BRAIN_PORT, PRIMARY_VISION_URL

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


class FrameDescriber:
    """Encodes frames and asks cloud_brain for a textual description."""

    def _encode_frame(self, frame_path: Path) -> str:
        """Resize to max 1280x720, JPEG quality 70, return base64."""
        with Image.open(frame_path) as img:
            img.thumbnail((1280, 720), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=70)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    def describe(self, frame_path: Path) -> dict:
        """Send a single frame to cloud_brain /propose and return metadata."""
        if not PRIMARY_VISION_URL:
            raise ValueError(
                "PRIMARY_VISION_URL not configured — AMD endpoint required."
            )

        encoded = self._encode_frame(frame_path)
        try:
            resp = requests.post(
                f"http://127.0.0.1:{CLOUD_BRAIN_PORT}/propose",
                json={
                    "os_name": "Windows",
                    "keyframe_paths": [str(frame_path)],
                    "keyframe_descriptions": [],
                    "visual_events": [],
                },
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            phases = data.get("phases") or []
            description = (
                phases[0].get("description", "No description")
                if phases
                else "No description"
            )
        except Exception as exc:
            logging.warning("[frame_describer] cloud_brain call failed: %s", exc)
            description = "Description unavailable"

        return {
            "path": str(frame_path),
            "description": description,
            "timecode": "00:00:00",
        }

    def describe_batch(
        self, frame_paths: list[Path], batch_size: int = 4
    ) -> list[dict]:
        """Describe each frame individually."""
        results: list[dict] = []
        for path in frame_paths:
            results.append(self.describe(path))
        return results


# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------

_describer_lock: Final[threading.Lock] = threading.Lock()
_describer_instance: FrameDescriber | None = None


def get_describer() -> FrameDescriber:
    global _describer_instance  # noqa: PLW0603
    if _describer_instance is not None:
        return _describer_instance
    with _describer_lock:
        if _describer_instance is None:
            _describer_instance = FrameDescriber()
    return _describer_instance
