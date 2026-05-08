# FILE: extractor/downloader.py
"""YouTube transcript downloader and video downloader."""

from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


class TranscriptDownloader:
    """Downloads and caches YouTube video transcripts."""

    def download(self, video_url: str, cache_dir: Path) -> dict:
        """Fetch transcript for *video_url*, caching to *cache_dir*.

        Returns a dict with ``transcript``, ``language``, and ``video_id`` keys.
        """
        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)

        video_id = self.extract_video_id(video_url)
        cache_path = cache_dir / f"{video_id}_transcript.json"

        if cache_path.exists():
            logging.info("[downloader] Loading cached transcript: %s", cache_path)
            with open(cache_path, "r", encoding="utf-8") as fh:
                return json.load(fh)

        logging.info("[downloader] Fetching transcript for %s...", video_id)
        try:
            raw = YouTubeTranscriptApi.get_transcript(video_id)
        except Exception as exc:
            raise RuntimeError(f"Transcript fetch failed: {exc}") from exc

        result = {
            "transcript": raw,
            "language": "en",
            "video_id": video_id,
        }

        with open(cache_path, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
        logging.info("[downloader] Cached transcript: %s", cache_path)
        return result

    def extract_video_id(self, url: str) -> str:
        """Extract the 11-character YouTube video ID from *url*."""
        match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
        if not match:
            raise ValueError(f"Could not extract video_id from URL: {url}")
        return match.group(1)

    def get_summary(self, transcript: list[dict], max_chars: int = 2000) -> str:
        """Join all transcript text entries and truncate to *max_chars*."""
        full_text = " ".join(item.get("text", "") for item in transcript)
        if len(full_text) > max_chars:
            return full_text[:max_chars] + "..."
        return full_text


class VideoDownloader:
    """Downloads YouTube videos to disk using yt-dlp via subprocess."""

    def __init__(self, download_dir: Path) -> None:
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def download(self, url: str) -> Path:
        """Download *url* to self.download_dir using yt-dlp.

        Returns the Path to the downloaded .mp4 file.
        """
        output_template = str(self.download_dir / "%(title)s.%(ext)s")

        logging.info("[downloader] Downloading video: %s", url)

        cmd = [
            "yt-dlp",
            "-f",
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format",
            "mp4",
            "--output",
            output_template,
            url,
        ]

        try:
            result = subprocess.run(
                cmd,
                check=False,
                timeout=300,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "yt-dlp not found. Install with: pip install yt-dlp"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("yt-dlp download timed out after 300 seconds.")

        if result.returncode != 0:
            logging.warning("[downloader] yt-dlp stderr: %s", result.stderr.strip())

        mp4_files = list(self.download_dir.glob("*.mp4"))
        if not mp4_files:
            raise RuntimeError(f"yt-dlp download failed for {url}")

        video_path = max(mp4_files, key=lambda p: p.stat().st_mtime)
        logging.info("[downloader] Video saved: %s", video_path)
        return video_path

    def is_youtube_url(self, url: str) -> bool:
        """Return True if url looks like a YouTube link."""
        return bool(re.search(r"(youtube\.com|youtu\.be)", url))
