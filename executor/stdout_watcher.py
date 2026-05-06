"""Process stdout monitor with signal-based exit-status detection.

Spawns a side-thread to drain the child process's stdout into a queue.
The main thread polls the queue until either a success / failure signal
is detected, the process terminates, or the timeout expires.
"""

from __future__ import annotations

import logging
import queue
import subprocess
import threading
import time
from enum import Enum
from typing import IO


class ExitStatus(Enum):
    """Discrete outcomes for a watched stdout session."""

    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class StdoutWatcher:
    """Thread-safe stdout consumer with signal matching.

    Usage::

        proc = subprocess.Popen(
            ["powershell", "-Command", "Write-Output 'done'"],
            stdout=subprocess.PIPE,
            text=True,
        )
        watcher = StdoutWatcher(proc, timeout=10.0)
        status, output = watcher.watch()
    """

    def __init__(
        self,
        process: subprocess.Popen[str],
        *,
        timeout: float = 30.0,
        success_signals: list[str] | None = None,
        failure_signals: list[str] | None = None,
    ) -> None:
        self._process = process
        self._timeout = max(0.0, timeout)
        self._success_signals = [s.lower() for s in (success_signals or []) if s]
        self._failure_signals = [s.lower() for s in (failure_signals or []) if s]
        self._queue: queue.Queue[str] = queue.Queue()
        self._output_lines: list[str] = []
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def watch(self) -> tuple[ExitStatus, str]:
        """Drain stdout until a signal matches, the process ends, or timeout.

        Returns a tuple of ``(ExitStatus, full_output)``.
        """
        # Start the side-thread
        reader = threading.Thread(target=self._reader_worker, daemon=True)
        reader.start()

        start_time = time.monotonic()
        full_output = ""

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed >= self._timeout:
                self._stop_event.set()
                return ExitStatus.TIMEOUT, full_output

            # Drain the queue without blocking indefinitely
            try:
                line = self._queue.get(timeout=0.5)
            except queue.Empty:
                # Check if the process has finished
                returncode = self._process.poll()
                if returncode is not None:
                    # Process finished — collect any remaining stdout
                    self._stop_event.set()
                    full_output = self._collect_remaining()
                    if returncode == 0:
                        return ExitStatus.SUCCESS, full_output
                    return ExitStatus.FAILURE, full_output
                continue

            full_output += line

            lowered = line.lower()
            for signal in self._success_signals:
                if signal in lowered:
                    self._stop_event.set()
                    return ExitStatus.SUCCESS, full_output

            for signal in self._failure_signals:
                if signal in lowered:
                    self._stop_event.set()
                    return ExitStatus.FAILURE, full_output

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _reader_worker(self) -> None:
        """Side-thread: read process stdout line-by-line and enqueue."""
        stdout = self._process.stdout
        if stdout is None:
            return

        try:
            for line in stdout:
                if self._stop_event.is_set():
                    break
                self._queue.put(line)
        except Exception as exc:
            logging.warning("Stdout reader thread encountered an error: %s", exc)

    def _collect_remaining(self) -> str:
        """Pull every line still sitting in the queue after the process exits."""
        remaining: list[str] = []
        while True:
            try:
                remaining.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return "".join(remaining)
