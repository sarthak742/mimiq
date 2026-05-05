# Mimiq Project State Ledger
**Last Updated:** Day 1, 2026-05-05 18:42:58 IST

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

## 4. Current Active Slice (In Progress)
*   **Target:** `cloud_brain.py` (The FastAPI bridge).
*   **Current Status:** Generating the full 900+ line file. Ensuring strict retention of all existing validation logic, prompt templates, and `create_completion_with_fallback` logic.
*   **Next Step:** Verify `python -m py_compile cloud_brain.py` passes, then commit.

## 5. Pending Slices (Do Not Execute Yet)
*   [ ] **Slice 3:** `utils/composer.py` (Video manifest and prerequisite handling).
*   [ ] **Slice 4:** `executor/action_runner.py` & `screen_capture.py`.
*   [ ] **Slice 5:** `ui/app.py` & `ui/static/index.html` (Local demo path).
