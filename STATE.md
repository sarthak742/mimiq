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

## 4. Current Active Slices (In Progress)
*   **Slice 5:** `executor/screen_capture.py` (Desktop capture utilities).
*   **Slice 6:** `main.py` (Central Nervous System / orchestrator wiring cloud_brain, composer, and action_runner).

## 5. Pending Slices (Do Not Execute Yet)
*   [ ] **Slice 7:** `ui/app.py` & `ui/static/index.html` (Local demo path).
