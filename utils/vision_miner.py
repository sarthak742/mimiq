# FILE: utils/vision_miner.py
"""Visual transition detection using perceptual hashing + EasyOCR.

No AI/AMD calls — everything runs locally on CPU.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Final

import numpy as np
from PIL import Image

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# ------------------------------------------------------------------
# OCR reader singleton
# ------------------------------------------------------------------

_ocr_lock: Final[threading.Lock] = threading.Lock()
_ocr_reader = None


def _get_ocr_reader():
    global _ocr_reader  # noqa: PLW0603
    if _ocr_reader is not None:
        return _ocr_reader
    with _ocr_lock:
        if _ocr_reader is None:
            import easyocr
            _ocr_reader = easyocr.Reader(["en"], gpu=False)
    return _ocr_reader


# ------------------------------------------------------------------
# Perceptual hash helpers
# ------------------------------------------------------------------

def _phash(image_path: Path) -> int:
    """Compute a 64-bit average hash for *image_path*."""
    with Image.open(image_path) as img:
        gray = img.convert("L").resize((8, 8), Image.Resampling.LANCZOS)
        pixels = list(gray.getdata())
    avg = sum(pixels) / len(pixels)
    bits = "".join("1" if p > avg else "0" for p in pixels)
    return int(bits, 2)


def _hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


# ------------------------------------------------------------------
# Main transition detector
# ------------------------------------------------------------------

def get_visual_transitions(
    frame_paths: list[Path],
    goal: str = "",
    cache_dir: Path | None = None,
) -> list[dict]:
    """Return a list of candidate visual transition events."""
    # PASS 1 — hash scan
    hashes: list[int] = []
    transitions: list[dict] = []

    for idx, path in enumerate(frame_paths):
        h = _phash(path)
        if idx == 0:
            transitions.append({
                "index": idx,
                "path": str(path),
                "hash": h,
                "is_transition": True,
            })
        else:
            dist = _hamming(h, hashes[-1])
            transitions.append({
                "index": idx,
                "path": str(path),
                "hash": h,
                "is_transition": dist > 8,
            })
        hashes.append(h)

    # PASS 2 — OCR on transition candidates
    results: list[dict] = []
    cache_dir = Path(cache_dir) if cache_dir else None
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)

    for item in transitions:
        if not item["is_transition"]:
            continue

        path = Path(item["path"])
        cache_key = cache_dir / f"{path.stem}_ocr.json" if cache_dir else None

        if cache_key and cache_key.exists():
            with open(cache_key, "r", encoding="utf-8") as fh:
                ocr_data = json.load(fh)
            tokens = ocr_data.get("tokens", [])
            snippet = ocr_data.get("snippet", "")
        else:
            reader = _get_ocr_reader()
            raw = reader.readtext(str(path))
            tokens = [r[1] for r in raw][:20]
            snippet = " ".join(r[1] for r in raw)[:120]
            if cache_key:
                with open(cache_key, "w", encoding="utf-8") as fh:
                    json.dump({"tokens": tokens, "snippet": snippet}, fh)

        # Parse timestamp from filename
        stem = path.stem
        if stem.startswith("frame_"):
            try:
                timestamp = int(stem.split("_", 1)[1]) / 1000.0
            except (ValueError, IndexError):
                timestamp = float(item["index"])
        else:
            timestamp = float(item["index"])

        # Confidence: higher if we have both hash change and OCR text
        confidence = 0.6 + (0.2 if tokens else 0.0) + (0.2 if item["is_transition"] else 0.0)
        confidence = min(confidence, 1.0)

        total_seconds = int(timestamp)
        hrs = total_seconds // 3600
        mins = (total_seconds % 3600) // 60
        secs = total_seconds % 60

        results.append({
            "timestamp": timestamp,
            "timecode": f"{hrs:02d}:{mins:02d}:{secs:02d}",
            "frame_path": str(path),
            "ocr_tokens": tokens,
            "ocr_snippet": snippet,
            "change_type": "scene_cut" if item["is_transition"] else "stable",
            "confidence_score": round(confidence, 2),
        })

    return results


def write_candidate_audit(candidates: list[dict], output_path: Path) -> None:
    """Atomic JSON write of candidate transitions."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(candidates, fh, indent=2)
    os.replace(tmp, output_path)
    logging.info("[vision_miner] Wrote candidate audit: %s", output_path)
