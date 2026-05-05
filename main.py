"""Mimiq Central Nervous System.

Wires cloud_brain (vision reasoning), utils.composer (plan scoring),
and executor.action_runner (physical execution) into a single async
orchestration pipeline.
"""

from __future__ import annotations

import argparse
import asyncio
import logging

import cloud_brain
from executor import action_runner
from utils import composer

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


async def run_mimiq(goal: str, video_path: str) -> None:
    """End-to-end Mimiq pipeline: propose -> compose -> playbook -> execute."""
    # ------------------------------------------------------------------
    # Step 1: Call cloud_brain.propose to get the initial manifest
    # ------------------------------------------------------------------
    propose_req = cloud_brain.ProposeRequest(
        os_name="windows",
        video_url="",
        local_tutorial_path=video_path,
        transcript_summary="",
        expected_environment="",
        visual_events=[],
        candidates=[],
        global_context_path="",
        global_context_description={},
        keyframe_paths=[],
        keyframe_descriptions=[],
    )
    logging.info("[Step 1] Requesting proposal manifest from cloud_brain...")
    propose_resp = await cloud_brain.propose_manifest(propose_req)

    # FastAPI JSONResponse or raw dict normalisation
    if hasattr(propose_resp, "body"):
        import json

        manifest = json.loads(propose_resp.body)
    else:
        manifest = propose_resp

    if isinstance(manifest, dict) and "error" in manifest:
        logging.error("Proposal failed: %s", manifest["error"])
        return

    logging.info("[Step 1] Proposal received with %d phase(s).", len(manifest.get("phases", [])))

    # ------------------------------------------------------------------
    # Step 2: Call composer.compose_plan to score and patch phases
    # ------------------------------------------------------------------
    logging.info("[Step 2] Composing plan against goal: %s", goal)
    final_manifest, gap_report = composer.compose_plan(goal, manifest)
    logging.info(
        "[Step 2] Composed plan: %d phase(s) | missing deps: %s",
        len(final_manifest.get("phases", [])),
        gap_report.get("missing_dependencies", []),
    )

    # ------------------------------------------------------------------
    # Step 3 + 4: For each phase, get playbook and execute
    # ------------------------------------------------------------------
    phases = final_manifest.get("phases", [])
    if not phases:
        logging.warning("No phases to execute.")
        return

    for idx, phase in enumerate(phases, start=1):
        phase_id = phase.get("phase_id", idx)
        description = phase.get("description", "")
        timecode = phase.get("timecode", "")
        logging.info("[Phase %d/%d] %s — %s", idx, len(phases), timecode, description)

        playbook_req = cloud_brain.PlaybookRequest(
            os_name="windows",
            video_url="",
            tutorial_frame_path="",
            context=description,
            timecode=timecode,
            phase_contract=phase,
            recent_state={},
            milestone_context={},
        )
        playbook_resp = await cloud_brain.get_playbook(playbook_req)

        if hasattr(playbook_resp, "body"):
            import json

            playbook = json.loads(playbook_resp.body)
        else:
            playbook = playbook_resp

        if isinstance(playbook, dict) and "error" in playbook:
            logging.error("Playbook generation failed for phase %d: %s", phase_id, playbook["error"])
            continue

        if not isinstance(playbook, dict) or not playbook.get("playbook"):
            logging.warning("Empty playbook for phase %d; skipping.", phase_id)
            continue

        logging.info("[Phase %d/%d] Executing playbook with %d step(s)...", idx, len(phases), len(playbook["playbook"]))
        success = action_runner.execute_playbook(playbook)
        if not success:
            logging.error("Execution failed at phase %d. Halting pipeline.", phase_id)
            return

    logging.info("Mimiq execution completed successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mimiq — Autonomous Desktop Agent")
    parser.add_argument("--goal", required=True, help="The user's high-level goal (e.g. 'Build a FastAPI app')")
    parser.add_argument("--video", required=True, help="Path to the local tutorial video (.mp4)")
    args = parser.parse_args()
    asyncio.run(run_mimiq(args.goal, args.video))
