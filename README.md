# Mimiq

Mimiq watches pre-downloaded tutorial videos, extracts actionable steps with a vision-language model, composes those steps against a user goal, and executes them on the desktop with safety checks, verification, recovery, and an HTML run report.

This repository is being rebuilt slice by slice for the AMD Hackathon. The current slice is only the project scaffold: dependency manifest, environment template, configuration guardrails, and empty Python package folders.

## Demo Priority

The first working path is local `.mp4` upload -> goal-aware compose -> dependency audit -> execute -> report. Cold YouTube processing, live transcript download, and documentation search are stretch work only after the local demo path is green.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Keep real provider keys in `.env`. The file is ignored by git and must never be committed.

## Configuration

Development defaults to Gemini:

```env
PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-flash
```

Demo mode uses the canonical primary vision variables:

```env
PROVIDER=amd
PRIMARY_VISION_URL=https://integrate.api.nvidia.com/v1
PRIMARY_VISION_MODEL=Qwen/Qwen2.5-VL-72B-Instruct
PRIMARY_VISION_PROVIDER=AMD_MI300X
```

When `PROVIDER=amd`, `config.py` fails at import time if the primary vision URL is missing or points to a placeholder/local endpoint.

## Later Slice Commands

These commands are reserved for later implementation slices and are documented here so the intended interface stays stable:

```powershell
python cloud_brain.py
python ui/app.py
python main.py --goal "FastAPI JWT auth" --video1 auth.mp4
python main.py --goal "FastAPI JWT auth" --video1 fastapi.mp4 --video2 auth.mp4
```

There is no `--mode web` flag planned for `main.py`; the web UI starts with `python ui/app.py`.
