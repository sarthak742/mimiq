"""Goal-aware composition from 1 or 2 video manifests."""

from __future__ import annotations

import re
from difflib import SequenceMatcher


def _tokenize(text: str) -> set[str]:
    """Extract lowercase alphabetic tokens from text."""
    return set(re.findall(r"[a-zA-Z]+", text.lower()))


def _calculate_relevance(goal: str, phase: dict) -> float:
    """Calculate Jaccard-like token overlap between goal and phase text blobs."""
    goal_tokens = _tokenize(goal)
    if not goal_tokens:
        return 0.0

    text_blobs = [
        phase.get("description", ""),
        phase.get("expected_focus", ""),
        " ".join(phase.get("required_workspace", [])),
        " ".join(phase.get("success_signals", [])),
        phase.get("file_target", ""),
    ]
    phase_text = " ".join(str(blob) for blob in text_blobs if blob)
    phase_tokens = _tokenize(phase_text)
    if not phase_tokens:
        return 0.0

    overlap = len(goal_tokens & phase_tokens)
    relevance = overlap / max(len(goal_tokens), len(phase_tokens), 1)
    return min(relevance, 1.0)


def _is_prerequisite(phase: dict) -> bool:
    """Determine if a phase represents a prerequisite or dependency step."""
    phase_mode = str(phase.get("phase_mode") or "").strip().lower()
    if phase_mode == "terminal_install":
        return True
    if "prerequisites" in phase or "dependencies" in phase:
        return True
    desc = str(phase.get("description") or "").lower()
    if any(marker in desc for marker in ("install", "setup dependencies", "bootstrap environment")):
        return True
    return False


def _description_similarity(desc_a: str, desc_b: str) -> float:
    """Return similarity ratio between two description strings."""
    return SequenceMatcher(None, desc_a.lower(), desc_b.lower()).ratio()


def score_phases(goal: str, phases: list[dict]) -> list[dict]:
    """Score each phase by token overlap relevance and confidence, applying mode boosts."""
    scored: list[dict] = []
    for phase in phases:
        relevance = _calculate_relevance(goal, phase)

        phase_mode = str(phase.get("phase_mode") or "").strip().lower()
        if phase_mode == "type_code":
            relevance *= 1.3
        elif phase_mode == "terminal_install":
            relevance *= 1.1

        relevance = min(relevance, 1.0)

        confidence = float(phase.get("confidence_score", 0.5))
        confidence = max(0.0, min(1.0, confidence))

        combined_score = (relevance * 0.8) + (confidence * 0.2)
        combined_score = round(max(0.0, min(1.0, combined_score)), 4)

        enriched = dict(phase)
        enriched["_score"] = combined_score
        scored.append(enriched)
    return scored


def select_phases(
    scored_1: list[dict],
    scored_2: list[dict] | None = None,
    threshold: float = 0.2,
) -> list[dict]:
    """Filter, pool, deduplicate, and sort phases by execution order."""
    filtered_1 = [p for p in scored_1 if p.get("_score", 0.0) >= threshold]
    filtered_2 = [p for p in (scored_2 or []) if p.get("_score", 0.0) >= threshold]

    pool: list[dict] = []
    pool.extend(filtered_1)
    pool.extend(filtered_2)

    # CRITICAL BUG PREVENTION (BUG 5): collect prerequisites in a SEPARATE list
    # before extending the pool.
    prerequisite_pool: list[dict] = []
    for phase in scored_1 + (scored_2 or []):
        if _is_prerequisite(phase) and phase not in pool:
            prerequisite_pool.append(phase)
    # THEN, and only then, extend pool with prerequisites
    pool.extend(prerequisite_pool)

    # Deduplicate the final pool by description similarity >= 0.65,
    # keeping the higher-scored version when duplicates are found.
    deduplicated: list[dict] = []
    for phase in pool:
        desc = str(phase.get("description") or "").strip()
        duplicate_index = None
        for idx, existing in enumerate(deduplicated):
            existing_desc = str(existing.get("description") or "").strip()
            if desc and existing_desc and _description_similarity(desc, existing_desc) >= 0.65:
                duplicate_index = idx
                break
        if duplicate_index is not None:
            if phase.get("_score", 0.0) > deduplicated[duplicate_index].get("_score", 0.0):
                deduplicated[duplicate_index] = phase
        else:
            deduplicated.append(phase)

    # Sort by phase_mode: terminal_install -> type_code -> terminal_run -> browser_verify
    _PHASE_ORDER = {
        "terminal_install": 0,
        "type_code": 1,
        "terminal_run": 2,
        "browser_verify": 3,
    }

    def _sort_key(phase: dict) -> int:
        mode = str(phase.get("phase_mode") or "").strip().lower()
        return _PHASE_ORDER.get(mode, 99)

    deduplicated.sort(key=_sort_key)
    return deduplicated


def _apply_cumulative_description_patch(phases: list[dict]) -> list[dict]:
    """Patch type_code phase descriptions so later phases include prior code context."""
    patched: list[dict] = []
    file_target_history: dict[str, list[str]] = {}

    for phase in phases:
        enriched = dict(phase)
        phase_mode = str(enriched.get("phase_mode") or "").strip().lower()
        file_target = str(enriched.get("file_target") or "").strip()

        if phase_mode == "type_code" and file_target:
            prior_descriptions = file_target_history.get(file_target, [])
            current_desc = str(enriched.get("description") or "").strip()

            if prior_descriptions and current_desc:
                history_text = " + ".join(prior_descriptions)
                enriched["description"] = (
                    f"write complete {file_target} including: {history_text} + {current_desc}"
                )

            file_target_history.setdefault(file_target, [])
            file_target_history[file_target].append(current_desc)

        patched.append(enriched)

    return patched


def compose_plan(
    goal: str,
    manifest_1: dict,
    manifest_2: dict | None = None,
) -> tuple[dict, dict]:
    """Main entry point: score, select, patch, and return the final manifest + GapReport."""
    phases_1 = manifest_1.get("phases") or []
    phases_2 = manifest_2.get("phases") or [] if manifest_2 else []

    scored_1 = score_phases(goal, phases_1)
    scored_2 = score_phases(goal, phases_2) if manifest_2 else None

    selected = select_phases(scored_1, scored_2)
    patched = _apply_cumulative_description_patch(selected)

    final_manifest: dict = {
        "demo_name": manifest_1.get("demo_name", "Mimiq_Composed_Plan"),
        "local_tutorial_path": manifest_1.get("local_tutorial_path", ""),
        "expected_environment": manifest_1.get("expected_environment", ""),
        "dependencies": dict(manifest_1.get("dependencies") or {}),
        "execution_rules": dict(
            manifest_1.get("execution_rules")
            or {
                "max_retries": 1,
                "allowed_actions": ["click", "keyboard_input", "hotkey", "sleep"],
            }
        ),
        "phases": patched,
    }

    # Merge dependencies from manifest_2 if present
    if manifest_2:
        deps_2 = manifest_2.get("dependencies") or {}
        apps_2 = deps_2.get("apps") or []
        apps_1 = final_manifest["dependencies"].get("apps") or []
        if apps_2:
            merged_apps = list(apps_1)
            existing_names: set[str] = set()
            for app in merged_apps:
                name = str(app.get("name") if isinstance(app, dict) else app).strip().lower()
                if name:
                    existing_names.add(name)
            for app in apps_2:
                name = str(app.get("name") if isinstance(app, dict) else app).strip().lower()
                if name and name not in existing_names:
                    merged_apps.append(app)
                    existing_names.add(name)
            final_manifest["dependencies"]["apps"] = merged_apps

    gap_report: dict = {"missing_dependencies": []}
    return final_manifest, gap_report
