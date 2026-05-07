# Mimiq Project State Ledger
**Last Updated:** Day 2, 2026-05-05 23:21 IST

## 1. The Macro Goal
Build an autonomous desktop agent (Mimiq) that watches a local tutorial video (.mp4), extracts actionable steps via an AMD-powered vision model, and executes them with visual verification.

## 2. Global Guardrails (DO NOT VIOLATE)
*   **Hardware Mandate:** All vision models must route through `PRIMARY_VISION_*` env vars. Never hardcode API keys or default fallback URLs.
*   **Aesthetic:** UI must adhere to Stealth Wealth (matte charcoal, metallic accents, minimal).
*   **Safety:** Never use `sudo`, `rm -rf`, or interact directly with `C:\Windows\System32`.
*   **Context:** The agent is blind to its own terminal. Do not click or interact with the agent's running console.

## 3. Completed Slices (Locked & Committed)
*   [x] **Slice 0:** `codex.md` created with global project instructions.
*   [x] **Slice 1:** Initial scaffolding (`requirements.txt`, `.gitignore`, `config.py` with AMD hardware guards, empty package directories).
*   [x] **Slice 2:** `cloud_brain.py` FastAPI bridge rebuilt with PRIMARY_VISION env routing, /health endpoint, and CLOUD_BRAIN_PORT support.
*   [x] **Slice 3:** `utils/composer.py` goal-aware manifest composition with prerequisite pooling, deduplication, and cumulative code patching.
*   [x] **Slice 4:** `executor/action_runner.py` thread-safe pyautogui action runner with short-command fix.
*   [x] **Slice 5:** `executor/safety.py` pure-logic deterministic safety classifier (GREEN/YELLOW/RED) with thread-safe singleton.
*   [x] **Slice 6:** `executor/screen_capture.py` refactored into context manager with standalone capture().
*   [x] **Slice 7:** `executor/failsafe.py` PyAutoGUI corner-detection failsafe wrapper.
*   [x] **Slice 8:** `executor/os_adapter.py` cross-shell command adaptation for Windows.
*   [x] **Slice 9:** `executor/stdout_watcher.py` process stdout monitoring with signal detection.
*   [x] **Slice 10:** `executor/hitl_overlay.py` human-in-the-loop decision overlay.
*   [x] **Slice 11:** `executor/calibrator.py` DPI-aware coordinate scaler.
*   [x] **Slice 12:** `executor/verification.py` & `executor/recovery.py` vision-feedback loop and action recovery.
*   [x] **Slice 13:** `extractor/frame_sampler.py` video ingestion and frame extraction via ffmpeg.

## 4. Current Active Slices (In Progress)
*   **Slice 14:** `extractor/deduplicator.py` (Frame deduplication via MSE thresholding).

## 5. Pending Slices (Do Not Execute Yet)
*   [ ] **Slice 15:** `main.py` (Central Nervous System / orchestrator).
*   [ ] **Slice 16:** `ui/app.py` & `ui/static/index.html` (Local demo path).
