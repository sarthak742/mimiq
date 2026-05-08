"""Verification engine for Mimiq.

Supports three verification modes:
- ocr_focus     : read text from the after screenshot and match signals
- pixel_diff    : compare before/after screenshots numerically
- vision_state  : POST to cloud_brain /playbook for LLM judgment
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Final

import numpy as np
import requests
from PIL import Image

from config import CLOUD_BRAIN_PORT, PRIMARY_VISION_URL

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


def extract_ocr_text(image_path: Path) -> str:
    """Run EasyOCR on *image_path* and return joined text."""
    reader = _get_ocr_reader()
    results = reader.readtext(str(image_path))
    texts = [item[1] for item in results if item[1]]
    return " ".join(texts)


# ------------------------------------------------------------------
# Pixel diff helper
# ------------------------------------------------------------------

def pixel_diff_ratio(before: Path, after: Path) -> float:
    """Return mean absolute pixel difference normalised to [0, 1]."""
    with Image.open(before) as img_a, Image.open(after) as img_b:
        img_a = img_a.convert("RGB")
        img_b = img_b.convert("RGB")
        if img_a.size != img_b.size:
            img_b = img_b.resize(img_a.size, Image.Resampling.LANCZOS)
        a = np.array(img_a, dtype=np.float32)
        b = np.array(img_b, dtype=np.float32)
    return float(np.mean(np.abs(a - b)) / 255.0)


# ------------------------------------------------------------------
# Main verification dispatcher
# ------------------------------------------------------------------

def verify_state_change(
    before_path: Path,
    after_path: Path,
    success_signals: list[str],
    failure_signals: list[str],
    mode: str = "vision_state",
) -> dict:
    """Verify whether the desired UI state change occurred.

    Returns a dict with at least a ``success`` key and mode-specific metadata.
    """
    if mode == "ocr_focus":
        ocr_text = extract_ocr_text(after_path)
        ocr_lower = ocr_text.lower()
        matched_signal = None
        for sig in success_signals:
            if sig.lower() in ocr_lower:
                matched_signal = sig
                return {
                    "success": True,
                    "mode": "ocr_focus",
                    "ocr_text": ocr_text,
                    "matched_signal": matched_signal,
                }
        for sig in failure_signals:
            if sig.lower() in ocr_lower:
                matched_signal = sig
                return {
                    "success": False,
                    "mode": "ocr_focus",
                    "ocr_text": ocr_text,
                    "matched_signal": matched_signal,
                }
        return {
            "success": False,
            "mode": "ocr_focus",
            "ocr_text": ocr_text,
            "matched_signal": None,
        }

    if mode == "pixel_diff":
        ratio = pixel_diff_ratio(before_path, after_path)
        return {
            "success": ratio > 0.01,
            "mode": "pixel_diff",
            "ratio": ratio,
        }

    # mode == "vision_state" (default)
    if not PRIMARY_VISION_URL:
        raise ValueError(
            "PRIMARY_VISION_URL not configured — AMD endpoint required."
        )
    try:
        resp = requests.post(
            f"http://127.0.0.1:{CLOUD_BRAIN_PORT}/playbook",
            json={
                "recent_state": {
                    "before_frame": str(before_path),
                    "after_frame": str(after_path),
                },
                "phase_contract": {
                    "verification_request": True,
                    "success_signals": success_signals,
                    "failure_signals": failure_signals,
                },
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "success": bool(data.get("success", False)),
            "mode": "vision_state",
            "fallback_used": False,
            "raw_response": data,
        }
    except Exception as exc:
        logging.warning(
            "[verify] vision_state request failed (%s), falling back to ocr_focus",
            exc,
        )
        return verify_state_change(
            before_path,
            after_path,
            success_signals,
            failure_signals,
            mode="ocr_focus",
        )
