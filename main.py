"""Mimiq Central Nervous System.

Ingestion  →  Deduplication  →  Manifest Generation

Takes a local tutorial video, extracts frames at 1 fps, prunes
visually-identical duplicates, and asks the vision model to produce a
structured JSON action manifest.  The executor is deliberately NOT wired
up here so the operator can inspect the manifest before the agent takes
control of the mouse.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from extractor.deduplicator import Deduplicator
from extractor.frame_sampler import FrameSampler
from understander import manifest_generator

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mimiq — Ingest a tutorial video and generate an actionable manifest."
    )
    parser.add_argument(
        "video_path",
        type=str,
        help="Path to the local tutorial video (.mp4)",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="output",
        help="Directory for extracted frames and generated manifest (default: output)",
    )
    args = parser.parse_args()

    video_path = Path(args.video_path).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Step 1: Ingestion — extract frames at ~1 fps
    # ------------------------------------------------------------------
    logging.info("Starting Ingestion...")
    sampler = FrameSampler()
    info = sampler.get_video_info(video_path)
    duration = info.get("duration", 0.0)
    frame_count = max(1, int(duration))

    logging.info(
        "Video duration: %.2fs → extracting %d frame(s) to %s",
        duration,
        frame_count,
        frames_dir,
    )
    raw_frames = sampler.extract_uniform_frames(
        video_path, count=frame_count, output_dir=frames_dir
    )

    # ------------------------------------------------------------------
    # Step 2: Deduplication — prune visually-identical neighbours
    # ------------------------------------------------------------------
    logging.info("Deduplicating frames...")
    deduplicator = Deduplicator()
    survivors = deduplicator.filter_duplicates(raw_frames)
    logging.info("%d frame(s) survived deduplication.", len(survivors))

    if not survivors:
        logging.error("No frames remain after deduplication. Aborting.")
        return

    # ------------------------------------------------------------------
    # Step 3: Manifest generation — ask the vision model for actions
    # ------------------------------------------------------------------
    logging.info("Generating actionable manifest...")
    manifest_path = out_dir / "manifest.json"
    manifest = manifest_generator.generate_manifest(
        frame_paths=survivors,
        output_path=manifest_path,
    )

    logging.info(
        "Success! Manifest ready for review: %s (%d action(s))",
        manifest_path,
        len(manifest),
    )


if __name__ == "__main__":
    main()
