# FILE: understander/sampler.py
"""Timeline event sampling utilities."""

from __future__ import annotations


def sample_timeline(timeline: list[dict], max_events: int = 20) -> list[dict]:
    """Return up to *max_events* events, evenly spaced by index."""
    if len(timeline) <= max_events:
        return list(timeline)
    step = len(timeline) / max_events
    indices = [int(i * step) for i in range(max_events)]
    return [timeline[i] for i in indices]


def sample_by_density(
    timeline: list[dict], window_seconds: float = 10.0
) -> list[dict]:
    """Group events into time windows and keep the one with the longest
    description from each window."""
    if not timeline:
        return []

    windows: dict[int, list[dict]] = {}
    for event in timeline:
        key = int(event.get("timestamp", 0.0) // window_seconds)
        windows.setdefault(key, []).append(event)

    winners: list[dict] = []
    for key in sorted(windows):
        group = windows[key]
        best = max(group, key=lambda e: len(e.get("description", "")))
        winners.append(best)

    return sorted(winners, key=lambda e: e.get("timestamp", 0.0))
