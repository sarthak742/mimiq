# FILE: understander/sentencizer.py
"""Text segmentation into sentences for transcript processing."""

from __future__ import annotations

import re


def sentencize(text: str) -> list[str]:
    """Split *text* into sentences and return non-empty stripped strings."""
    raw = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in raw if s.strip()]


def sentencize_transcript(transcript: list[dict]) -> list[dict]:
    """Break each transcript item into sentences, distributing duration."""
    results: list[dict] = []
    for item in transcript:
        sentences = sentencize(str(item.get("text", "")))
        count = len(sentences)
        duration = float(item.get("duration", 0.0))
        start = float(item.get("start", 0.0))
        per_sentence = duration / count if count > 0 else 0.0
        for i, sentence in enumerate(sentences):
            results.append({
                "sentence": sentence,
                "start": start + (i * per_sentence),
                "duration": per_sentence,
            })
    return results
