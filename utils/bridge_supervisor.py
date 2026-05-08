# FILE: utils/bridge_supervisor.py
"""Managed lifecycle for the cloud_brain FastAPI subprocess."""

from __future__ import annotations

import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Final

import requests

from config import CLOUD_BRAIN_PORT

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


class ManagedBridge:
    """Context manager that starts ``cloud_brain.py`` and waits for /health."""

    def __init__(self, port: int | None = None) -> None:
        self.port = port or CLOUD_BRAIN_PORT
        self._process: subprocess.Popen | None = None

    def __enter__(self) -> ManagedBridge:
        script = Path(__file__).parent.parent / "cloud_brain.py"
        logging.info("[bridge] Starting cloud_brain: %s", script)
        self._process = subprocess.Popen(
            [sys.executable, str(script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        deadline = time.time() + 8.0
        while time.time() < deadline:
            if self.is_healthy():
                try:
                    resp = requests.get(
                        f"http://127.0.0.1:{self.port}/health", timeout=2
                    )
                    data = resp.json()
                    logging.info(
                        "[bridge] cloud_brain healthy — provider=%s model=%s",
                        data.get("active_provider", "unknown"),
                        data.get("active_model", "unknown"),
                    )
                except Exception:
                    logging.info("[bridge] cloud_brain /health returned 200.")
                return self
            time.sleep(0.5)

        raise RuntimeError("cloud_brain failed to start within 8 seconds.")

    def __exit__(self, *args) -> None:
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            logging.info("[bridge] cloud_brain stopped.")

    def is_healthy(self) -> bool:
        try:
            resp = requests.get(
                f"http://127.0.0.1:{self.port}/health", timeout=2
            )
            return resp.status_code == 200
        except Exception:
            return False
