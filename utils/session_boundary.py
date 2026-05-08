# FILE: utils/session_boundary.py
"""Work-root and transient directory management."""

from __future__ import annotations

import fnmatch
import logging
import os
import shutil
import tempfile
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def get_work_root() -> Path:
    """Return the Mimiq working directory (env or temp)."""
    raw = os.environ.get("MIMIQ_WORKDIR")
    if raw:
        return Path(raw)
    return Path(tempfile.gettempdir()) / "mimiq_work"


def clear_transient_workdir(
    work_root: Path,
    keep_patterns: list[str] | None = None,
) -> None:
    """Delete all contents of *work_root* except files matching *keep_patterns*."""
    work_root = Path(work_root)
    work_root.mkdir(parents=True, exist_ok=True)
    keep = keep_patterns or []
    deleted = 0

    for item in work_root.iterdir():
        if any(fnmatch.fnmatch(item.name, pat) for pat in keep):
            continue
        try:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
            deleted += 1
        except OSError as exc:
            logging.warning("[session_boundary] Could not remove %s: %s", item, exc)

    logging.info("[session_boundary] Deleted %d item(s) from %s", deleted, work_root)
