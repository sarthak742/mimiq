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

## 4. Current Active Slice (In Progress)
*   **Target:** `executor/action_runner.py` & `screen_capture.py` (Execution engine).
*   **Current Status:** Not yet started.
*   **Next Step:** Build `executor/action_runner.py` with pyautogui action translation and thread-safe playbook execution.

## 5. Pending Slices (Do Not Execute Yet)
*   [ ] **Slice 5:** `ui/app.py` & `ui/static/index.html` (Local demo path).
