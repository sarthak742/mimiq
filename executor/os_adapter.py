"""Cross-shell command adapter for Windows PowerShell.

Translates common POSIX / Unix shell idioms into their Windows equivalents
so that tutorials written for bash/zsh work out of the box on Mimiq's
primary Windows target.
"""

from __future__ import annotations

import re
import threading

import config

# Simple 1-to-1 command-name mapping
_SIMPLE_MAP: dict[str, str] = {
    "ls": "dir",
    "clear": "cls",
    "cat": "Get-Content",
    "touch": "New-Item",
    "rm -rf": "Remove-Item -Recurse -Force",
}

# Regex patterns for flag substitution
_FLAG_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    #  ls -la   ->  dir
    (re.compile(r"^\s*ls\s+-(?:[a-zA-Z]+)\s*"), "dir"),
    #  rm -r    ->  Remove-Item -Recurse
    (re.compile(r"^\s*rm\s+-r(?:ecurse)?\b"), "Remove-Item -Recurse"),
    #  cp -r    ->  Copy-Item -Recurse
    (re.compile(r"^\s*cp\s+-r(?:ecurse)?\b"), "Copy-Item -Recurse"),
]


class OSAdapter:
    """Deterministic shell-command translator for Windows."""

    def adapt_command(self, cmd: str) -> str:
        """Translate *cmd* into its Windows / PowerShell equivalent.

        Order of precedence:
        1. Exact match in the simple mapping (including multi-word keys).
        2. Regex-based flag substitution.
        3. Passthrough — return the original command unchanged.
        """
        stripped = cmd.strip()
        lowered = stripped.lower()

        # 1. Simple exact / prefix match
        for posix, win in _SIMPLE_MAP.items():
            if lowered == posix or lowered.startswith(posix + " "):
                remainder = stripped[len(posix) :]
                return f"{win}{remainder}"

        # 2. Regex patterns
        for pattern, replacement in _FLAG_PATTERNS:
            if pattern.match(stripped):
                # Replace only the matched prefix, keep the rest
                return pattern.sub(replacement, stripped, count=1)

        # 3. Passthrough
        return stripped

    def build_shell_command(self, cmd: str) -> list[str]:
        """Return a ``subprocess``-ready argument list for PowerShell.

        Example::

            adapter.build_shell_command("ls -la")
            # -> ["powershell", "-Command", "dir"]
        """
        adapted = self.adapt_command(cmd)
        return ["powershell", "-Command", adapted]


# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------

_adapter_lock = threading.Lock()
_adapter_instance: OSAdapter | None = None


def get_adapter() -> OSAdapter:
    """Return the thread-safe singleton ``OSAdapter``."""
    global _adapter_instance  # noqa: PLW0603

    if _adapter_instance is not None:
        return _adapter_instance

    with _adapter_lock:
        if _adapter_instance is None:
            _adapter_instance = OSAdapter()
    return _adapter_instance
