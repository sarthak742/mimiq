# FILE: utils/preflight.py
"""Environment preflight checks before launching the Mimiq pipeline."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field

import requests

from config import CLOUD_BRAIN_PORT, PRIMARY_VISION_KEY, PRIMARY_VISION_URL


@dataclass
class PreflightResult:
    passed: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def check_env() -> PreflightResult:
    """Run all preflight checks and return a :class:`PreflightResult`."""
    errors: list[str] = []
    warnings: list[str] = []

    # 1. PRIMARY_VISION_URL
    blocked = (
        "example.com",
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "<amd-endpoint>",
        "",
    )
    url = (PRIMARY_VISION_URL or "").strip().lower()
    if not url or any(b in url for b in blocked):
        errors.append("PRIMARY_VISION_URL not configured — AMD endpoint required.")

    # 2. PRIMARY_VISION_KEY
    if not PRIMARY_VISION_KEY:
        errors.append("PRIMARY_VISION_KEY not set.")

    # 3. pyautogui
    try:
        import pyautogui  # noqa: F401
    except ImportError:
        errors.append("pyautogui not installed.")

    # 4. cloud_brain /health
    try:
        resp = requests.get(
            f"http://127.0.0.1:{CLOUD_BRAIN_PORT}/health", timeout=2
        )
        if resp.status_code != 200:
            warnings.append(
                f"cloud_brain /health returned {resp.status_code}"
            )
    except Exception:
        warnings.append(
            "cloud_brain not reachable yet (start it before running the pipeline)."
        )

    # 5. ffmpeg
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        warnings.append("ffmpeg not found on PATH — video frame extraction will fail.")

    return PreflightResult(passed=len(errors) == 0, warnings=warnings, errors=errors)


def print_report(result: PreflightResult) -> None:
    """Print colored preflight report to stdout."""
    try:
        from rich.console import Console
        from rich.text import Text

        console = Console()
        for err in result.errors:
            console.print(Text(f"FATAL: {err}", style="bold red"))
        for warn in result.warnings:
            console.print(Text(f"WARN:  {warn}", style="yellow"))
        if result.passed and not result.warnings:
            console.print(Text("OK — All preflight checks passed.", style="bold green"))
        elif result.passed:
            console.print(Text("OK — Preflight passed with warnings.", style="green"))
    except Exception:
        for err in result.errors:
            print(f"FATAL: {err}")
        for warn in result.warnings:
            print(f"WARN:  {warn}")
        if result.passed and not result.warnings:
            print("OK — All preflight checks passed.")
        elif result.passed:
            print("OK — Preflight passed with warnings.")
