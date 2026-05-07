"""Video frame extraction using ffmpeg and ffprobe.

Provides a ``FrameSampler`` class that queries video metadata and extracts
frames uniformly or at specific timestamps.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path


class FrameSampler:
    """Wrapper around ffmpeg / ffprobe for video frame sampling."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_video_info(self, video_path: Path) -> dict:
        """Return duration (seconds) and fps for *video_path* via ffprobe.

        Raises ``RuntimeError`` if ffprobe is unavailable or the probe fails.
        """
        video_path = video_path.resolve()
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=duration,r_frame_rate",
            "-show_entries", "format=duration",
            "-of", "json",
            str(video_path),
        ]

        logging.debug("[frame_sampler] ffprobe command: %s", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            raise RuntimeError(
                f"ffprobe failed (rc={result.returncode}): {result.stderr.strip()}"
            )

        data = json.loads(result.stdout)
        stream = (data.get("streams") or [{}])[0]
        fmt = data.get("format") or {}

        # Duration can live in stream or format block
        raw_duration = stream.get("duration") or fmt.get("duration")
        duration = float(raw_duration) if raw_duration else 0.0

        # Frame rate is often expressed as a fraction "num/den"
        fps = 0.0
        rate_str = stream.get("r_frame_rate", "")
        if rate_str and "/" in rate_str:
            num, den = rate_str.split("/", 1)
            try:
                fps = float(num) / float(den)
            except (ValueError, ZeroDivisionError):
                fps = 0.0
        elif rate_str:
            try:
                fps = float(rate_str)
            except ValueError:
                fps = 0.0

        info = {
            "duration": duration,
            "fps": fps,
            "path": str(video_path),
        }
        logging.info("[frame_sampler] Video info: %s", info)
        return info

    def extract_uniform_frames(
        self,
        video_path: Path,
        count: int,
        output_dir: Path,
    ) -> list[Path]:
        """Extract *count* uniformly-spaced frames from *video_path*.

        Returns a list of ``Path`` objects pointing to the saved PNG files.
        """
        video_path = video_path.resolve()
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        if count <= 0:
            logging.warning("[frame_sampler] count <= 0; returning empty list.")
            return []

        info = self.get_video_info(video_path)
        duration = info.get("duration", 0.0)
        if duration <= 0:
            raise RuntimeError(f"Cannot sample frames: invalid duration {duration}")

        # fps filter: count frames spread across the full duration
        fps_value = count / duration

        pattern = str(output_dir / "frame_%04d.png")
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(video_path),
            "-vf", f"fps={fps_value:.4f}",
            pattern,
        ]

        logging.info("[frame_sampler] ffmpeg command: %s", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            raise RuntimeError(
                f"ffmpeg failed (rc={result.returncode}): {result.stderr.strip()}"
            )

        # Collect the generated frame files in lexicographic order
        frames = sorted(output_dir.glob("frame_*.png"))
        logging.info(
            "[frame_sampler] Extracted %d frame(s) to %s", len(frames), output_dir
        )
        return frames

    def extract_frame_at_time(
        self,
        video_path: Path,
        timestamp: float,
        output_path: Path,
    ) -> Path:
        """Extract a single frame at *timestamp* seconds.

        Returns the ``Path`` of the saved image.
        """
        video_path = video_path.resolve()
        output_path = output_path.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        timestamp = max(0.0, timestamp)

        cmd = [
            "ffmpeg",
            "-y",
            "-ss", str(timestamp),
            "-i", str(video_path),
            "-vframes", "1",
            str(output_path),
        ]

        logging.info("[frame_sampler] ffmpeg command: %s", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            raise RuntimeError(
                f"ffmpeg failed (rc={result.returncode}): {result.stderr.strip()}"
            )

        logging.info("[frame_sampler] Frame saved to %s", output_path)
        return output_path
