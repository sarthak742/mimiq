# FILE: orchestrator/lookahead.py
"""Heuristic lookahead correction for negation detection in transcript."""

from __future__ import annotations

import re
from copy import deepcopy

NEGATION_WORDS = frozenset({
    "not", "don't", "doesn't", "didn't", "never", "no",
    "without", "avoid", "skip", "except", "unless", "don't", "doesn't", "didn't"
})


def apply_lookahead_corrections(
    phases: list[dict],
    transcript_segments: list[str],
) -> list[dict]:
    """Return a new list of phases with optional ``lookahead_warning`` keys
    when negation words appear near phase-description tokens."""
    corrected: list[dict] = []

    for i, phase in enumerate(phases):
        phase_copy = deepcopy(phase)
        segment = transcript_segments[i] if i < len(transcript_segments) else ""
        seg_tokens = re.findall(r"[a-zA-Z']+", segment.lower())
        desc = str(phase.get("description", ""))
        desc_tokens = re.findall(r"[a-zA-Z]+", desc.lower())

        for neg in NEGATION_WORDS:
            if neg not in seg_tokens:
                continue
            neg_idx = seg_tokens.index(neg)
            for dtoken in desc_tokens:
                for s_idx, stoken in enumerate(seg_tokens):
                    if stoken == dtoken and abs(s_idx - neg_idx) <= 3:
                        phase_copy["lookahead_warning"] = (
                            f"Negation detected near '{dtoken}': '{neg}'"
                        )
                        break
                if "lookahead_warning" in phase_copy:
                    break
            if "lookahead_warning" in phase_copy:
                break

        corrected.append(phase_copy)

    return corrected
