# FILE: understander/timeline_builder.py
"""Merges frame descriptions and transcript into a unified timeline."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


class TimelineBuilder:
    """Builds a chronologically sorted timeline from frames + transcript."""

    def build(
        self,
        frame_descriptions: list[dict],
        transcript: list[dict],
    ) -> list[dict]:
        """Merge *frame_descriptions* with *transcript* by timestamp proximity."""
        events: list[dict] = []

        for frame in frame_descriptions:
            frame_ts = self._parse_frame_timestamp(frame.get("path", ""))
            closest_text = ""
            min_gap = float("inf")
            for item in transcript:
                gap = abs(item.get("start", 0.0) - frame_ts)
                if gap <= 3.0 and gap < min_gap:
                    min_gap = gap
                    closest_text = item.get("text", "")

            events.append({
                "timestamp": frame_ts,
                "timecode": self._format_timecode(frame_ts),
                "description": frame.get("description", ""),
                "transcript_text": closest_text,
                "frame_path": frame.get("path", ""),
            })

        events.sort(key=lambda e: e["timestamp"])
        return events

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_frame_timestamp(self, path_str: str) -> float:
        """Extract milliseconds from ``frame_{ms}.png`` or fall back to 0."""
        name = Path(path_str).stem
        if name.startswith("frame_"):
            try:
                return int(name.split("_", 1)[1]) / 1000.0
            except (ValueError, IndexError):
                pass
        return 0.0

    def _format_timecode(self, seconds: float) -> str:
        """Format *seconds* as ``HH:MM:SS``."""
        total = int(seconds)
        hrs = total // 3600
        mins = (total % 3600) // 60
        secs = total % 60
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"

    def save(self, timeline: list[dict], output_path: Path) -> None:
        """Atomic JSON write to *output_path*."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = output_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(timeline, fh, indent=2)
        os.replace(tmp, output_path)
        logging.info("[timeline_builder] Saved timeline: %s", output_path)

    def load(self, path: Path) -> list[dict]:
        """Load timeline from JSON or return an empty list."""
        path = Path(path)
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
