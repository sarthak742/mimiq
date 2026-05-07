"""Vision model manifest generator for Mimiq.

Takes a sequence of extracted/deduplicated UI frames, sends them to the
vision model, and asks it to produce a structured JSON action manifest.
"""

from __future__ import annotations

import base64
import json
import logging
import re
from pathlib import Path
from typing import Any

import cloud_brain


def encode_image(image_path: Path) -> str:
    """Read an image from disk and return its base64-encoded string."""
    with open(image_path, "rb") as fh:
        return base64.b64encode(fh.read()).decode("utf-8")


def _strip_markdown_fences(text: str) -> str:
    """Remove `` ```json ... ``` `` or `` ``` ... ``` `` markdown fences."""
    stripped = re.sub(r"^\s*```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    stripped = re.sub(r"\s*```\s*$", "", stripped)
    return stripped.strip()


def generate_manifest(
    frame_paths: list[Path],
    output_path: Path,
) -> list[dict[str, Any]]:
    """Send *frame_paths* to the vision model and return the parsed action manifest.

    The manifest is a JSON array of action dicts with keys:
    ``step``, ``action_type``, ``target_description``, ``coordinates``, ``value``.
    The raw JSON is also saved to *output_path*.
    """
    if not frame_paths:
        logging.warning("[manifest_generator] No frames provided; returning empty manifest.")
        return []

    # ------------------------------------------------------------------
    # Encode frames
    # ------------------------------------------------------------------
    image_blocks: list[dict[str, Any]] = []
    for path in sorted(frame_paths):
        b64 = encode_image(path)
        image_blocks.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"},
            }
        )

    # ------------------------------------------------------------------
    # Build the prompt
    # ------------------------------------------------------------------
    system_prompt = (
        "You are an RPA (Robotic Process Automation) system analyzing a "
        "sequence of UI frames extracted from a tutorial video. "
        "Your task is to identify the sequence of user actions shown in the frames.\n\n"
        "Output a JSON array of action objects. Each object must have the following keys:\n"
        '  - "step": integer, the step number (1-indexed)\n'
        '  - "action_type": string, one of ["click", "type", "wait", "hotkey", "scroll"]\n'
        '  - "target_description": string, a human-readable description of the UI element\n'
        '  - "coordinates": list of two integers [x, y], screen coordinates for the action\n'
        '  - "value": string (optional), the text to type or the hotkey combination\n\n'
        "Be precise with coordinates. Return ONLY the JSON array, no commentary."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Analyze the following frames and produce the JSON action manifest."
                    ),
                },
                *image_blocks,
            ],
        },
    ]

    # ------------------------------------------------------------------
    # Call the vision model
    # ------------------------------------------------------------------
    logging.info(
        "[manifest_generator] Sending %d frame(s) to the vision model...", len(frame_paths)
    )
    response = cloud_brain.create_completion_with_fallback(
        messages=messages, temperature=0.0
    )

    raw_text = response.choices[0].message.content or ""
    logging.debug("[manifest_generator] Raw model response (first 500 chars): %s", raw_text[:500])

    # ------------------------------------------------------------------
    # Parse the JSON response
    # ------------------------------------------------------------------
    cleaned = _strip_markdown_fences(raw_text)
    try:
        manifest: list[dict[str, Any]] = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logging.error(
            "[manifest_generator] JSON parse failed: %s | Raw text: %s", exc, cleaned[:500]
        )
        raise RuntimeError(f"Model returned invalid JSON: {exc}") from exc

    if not isinstance(manifest, list):
        raise RuntimeError(
            f"Model returned a {type(manifest).__name__} instead of a JSON array."
        )

    # ------------------------------------------------------------------
    # Persist and return
    # ------------------------------------------------------------------
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    logging.info(
        "[manifest_generator] Manifest saved to %s (%d action(s))",
        output_path,
        len(manifest),
    )
    return manifest
