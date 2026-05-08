# FILE: extractor/semantic_sampler.py
"""Jaccard-similarity transcript sampler for goal-aligned timestamps."""

from __future__ import annotations

import re
import threading
from typing import Final


class SemanticSampler:
    """Scores transcript segments by token-overlap with a goal string."""

    def find_high_intent_timestamps(
        self,
        transcript: list[dict],
        goal: str,
        max_count: int = 10,
    ) -> list[float]:
        """Return up to *max_count* timestamps most semantically aligned
        with *goal*, sorted ascending."""
        goal_tokens = set(re.findall(r"[a-zA-Z]+", goal.lower()))
        if not goal_tokens:
            return []

        scored: list[tuple[float, float]] = []
        for item in transcript:
            text = str(item.get("text", ""))
            seg_tokens = set(re.findall(r"[a-zA-Z]+", text.lower()))
            union = goal_tokens | seg_tokens
            if not union:
                continue
            score = len(goal_tokens & seg_tokens) / len(union)
            scored.append((item.get("start", 0.0), score))

        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:max_count]
        top.sort(key=lambda x: x[0])
        return [t for t, _ in top]


# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------

_sampler_lock: Final[threading.Lock] = threading.Lock()
_sampler_instance: SemanticSampler | None = None


def get_sampler() -> SemanticSampler:
    global _sampler_instance  # noqa: PLW0603
    if _sampler_instance is not None:
        return _sampler_instance
    with _sampler_lock:
        if _sampler_instance is None:
            _sampler_instance = SemanticSampler()
    return _sampler_instance
