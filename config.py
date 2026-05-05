"""Central configuration for the Mimiq rebuild.

This module intentionally contains only scaffold-level constants and provider
guardrails. Runtime clients and application logic belong in later slices.
"""

from __future__ import annotations

import os

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - allows py_compile/import before deps install
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


PROVIDER = os.getenv("PROVIDER", "gemini").strip().lower()

PRIMARY_VISION_URL = os.getenv("PRIMARY_VISION_URL", "").strip()
PRIMARY_VISION_KEY = os.getenv("PRIMARY_VISION_KEY", "").strip()
PRIMARY_VISION_MODEL = os.getenv(
    "PRIMARY_VISION_MODEL",
    "Qwen/Qwen2.5-VL-72B-Instruct",
).strip()
PRIMARY_VISION_PROVIDER = os.getenv("PRIMARY_VISION_PROVIDER", "PRIMARY").strip()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

PUTER_AUTH_TOKEN = os.getenv("PUTER_AUTH_TOKEN", "").strip()
PUTER_MODEL = os.getenv("PUTER_MODEL", "qwen/qwen2.5-vl-72b-instruct").strip()

MIMIQ_STEP_GENERATOR_URL = os.getenv(
    "MIMIQ_STEP_GENERATOR_URL",
    "http://127.0.0.1:8000/playbook",
).strip()
CLOUD_BRAIN_PORT = int(os.getenv("CLOUD_BRAIN_PORT", "8000"))

CACHE_DIR = os.getenv("CACHE_DIR", "cache/tutorials")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")

GREEN_COMMANDS = {
    "ls",
    "cd",
    "mkdir",
    "git",
    "npm",
    "pip",
    "python",
    "node",
    "echo",
    "cat",
    "touch",
    "cp",
    "mv",
    "brew",
    "winget",
    "npx",
    "yarn",
    "pnpm",
    "cargo",
    "go",
    "docker",
    "conda",
    "uvicorn",
    "fastapi",
    "venv",
}

RED_COMMANDS = {
    "sudo",
    "rm -rf",
    "del /s /q",
    "/etc/",
    "/sys/",
    "c:\\windows\\system32",
    "chmod 777",
    "dd",
    "eval",
    "exec",
    ":(){ :|:& };:",
}


def require_real_vision_endpoint() -> None:
    """Fail closed when demo mode points at a fake or local vision endpoint."""

    normalized_url = PRIMARY_VISION_URL.lower()
    blocked_markers = (
        "example.com",
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "<amd-endpoint>",
    )

    if not normalized_url or any(marker in normalized_url for marker in blocked_markers):
        raise ValueError(
            f"PRIMARY_VISION_URL is not a real AMD endpoint: '{PRIMARY_VISION_URL}'. "
            "Set PRIMARY_VISION_URL to the AMD Developer Cloud endpoint in .env."
        )


if PROVIDER == "amd":
    require_real_vision_endpoint()
