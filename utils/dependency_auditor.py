# FILE: utils/dependency_auditor.py
"""Dependency presence checker with optional auto-install."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass


@dataclass
class AuditResult:
    name: str
    present: bool
    version: str
    auto_installed: bool


def audit(manifest: dict, auto_install: bool = False) -> list[AuditResult]:
    """Probe each app in *manifest["dependencies"]["apps"]* and return
    a list of :class:`AuditResult`."""
    deps = manifest.get("dependencies") or {}
    apps = deps.get("apps") or []
    results: list[AuditResult] = []

    for app in apps:
        if isinstance(app, str):
            app = {"name": app}
        name = str(app.get("name", ""))
        if not name:
            continue

        probe = app.get("probe") or f"{name} --version"
        present, version = _probe(probe)
        auto_installed_flag = False

        if not present and auto_install and os.environ.get("MIMIQ_AUTO_INSTALL_PIP") == "1":
            subprocess.run(
                ["pip", "install", name],
                capture_output=True,
                check=False,
            )
            present, version = _probe(probe)
            auto_installed_flag = True

        results.append(
            AuditResult(
                name=name,
                present=present,
                version=version,
                auto_installed=auto_installed_flag,
            )
        )

    return results


def _probe(cmd: str) -> tuple[bool, str]:
    """Run *cmd* via shell and return ``(present, version_string)``."""
    try:
        result = subprocess.run(
            cmd.split(),
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0:
            first_line = result.stdout.strip().splitlines()[0]
            return True, first_line
    except Exception:
        pass
    return False, ""


def print_audit_table(results: list[AuditResult]) -> None:
    """Render audit results as a table."""
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title="Dependency Audit")
        table.add_column("Name", style="cyan")
        table.add_column("Present", justify="center")
        table.add_column("Version")
        table.add_column("Auto-installed", justify="center")

        for r in results:
            present = "✓" if r.present else "✗"
            present_style = "green" if r.present else "red"
            auto = "✓" if r.auto_installed else "—"
            table.add_row(
                r.name,
                f"[{present_style}]{present}[/{present_style}]",
                r.version or "—",
                auto,
            )
        console.print(table)
    except Exception:
        for r in results:
            mark = "✓" if r.present else "✗"
            auto = "auto" if r.auto_installed else "—"
            print(f"{mark} {r.name:20s}  {r.version:20s}  {auto}")
