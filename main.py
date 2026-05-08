"""Mimiq Central Nervous System.

Ingestion → Deduplication → Vision Mining → Manifest Composition →
Dependency Audit → Execution → Report Generation
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

import requests
from pathlib import Path

from config import CLOUD_BRAIN_PORT
from extractor.deduplicator import Deduplicator
from extractor.frame_sampler import FrameSampler
from utils.vision_miner import get_visual_transitions, write_candidate_audit
from utils.composer import compose_plan
from utils.preflight import check_env, print_report
from utils.session_boundary import clear_transient_workdir, get_work_root
from utils.dependency_auditor import audit, print_audit_table
from utils.reporter import MimiqReporter
from utils.bridge_supervisor import ManagedBridge
from orchestrator.orchestrator import Orchestrator

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mimiq — Ingest a tutorial video and generate an actionable manifest."
    )
    parser.add_argument(
        "--goal",
        type=str,
        required=True,
        help="What do you want to build?",
    )
    parser.add_argument(
        "--video",
        type=str,
        required=True,
        help="Path to the local tutorial video (.mp4)",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="output",
        help="Directory for outputs (default: output)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from saved state",
    )
    parser.add_argument(
        "--compose-only",
        action="store_true",
        help="Stop after manifest composition",
    )
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="Run calibration wizard only",
    )
    args = parser.parse_args()

    work_root = get_work_root()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Preflight
    result = check_env()
    print_report(result)
    if not result.passed:
        sys.exit(1)

    with ManagedBridge() as bridge:
        clear_transient_workdir(
            work_root, keep_patterns=["state.json", "*.json"]
        )
        frames_dir = work_root / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)

        # 1. Extract frames
        sampler = FrameSampler()
        raw_frames = sampler.extract_uniform_frames(
            Path(args.video), count=16, output_dir=frames_dir
        )

        # 2. Deduplicate
        deduplicator = Deduplicator()
        survivors = deduplicator.filter_duplicates(raw_frames)
        if not survivors:
            logging.error("No frames survived deduplication. Aborting.")
            sys.exit(1)

        # 3. Vision mining
        transitions = get_visual_transitions(
            survivors, goal=args.goal, cache_dir=work_root / "cache"
        )
        write_candidate_audit(transitions, work_root / "candidate_audit.json")

        # 4. Propose manifest via cloud_brain /propose
        propose_payload = {
            "os_name": "Windows",
            "video_url": "",
            "local_tutorial_path": args.video,
            "visual_events": transitions,
            "keyframe_paths": [str(p) for p in survivors[:8]],
            "keyframe_descriptions": [],
            "transcript_summary": args.goal,
            "expected_environment": "",
        }
        resp = requests.post(
            f"http://127.0.0.1:{CLOUD_BRAIN_PORT}/propose",
            json=propose_payload,
            timeout=30,
        )
        resp.raise_for_status()
        manifest_1 = resp.json()

        # 5. Compose
        final_manifest, gap_report = compose_plan(args.goal, manifest_1)
        manifest_path = out_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(final_manifest, f, indent=2)
        logging.info(
            "Manifest saved: %s (%d phases)",
            manifest_path,
            len(final_manifest.get("phases", [])),
        )

        if args.compose_only:
            logging.info("--compose-only flag set. Stopping after composition.")
            return

        # 6. Dependency audit
        audit_results = audit(final_manifest, auto_install=False)
        print_audit_table(audit_results)

        # 7. Run pipeline
        reporter = MimiqReporter(goal=args.goal, output_dir=out_dir)
        orch = Orchestrator(work_root=work_root)
        orch._reporter = reporter
        success = orch.run_pipeline(args.goal, final_manifest)

        # 8. Generate report
        report_path = reporter.generate()
        logging.info("Report: %s | Pipeline success: %s", report_path, success)


if __name__ == "__main__":
    main()
