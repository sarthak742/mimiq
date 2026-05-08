# FILE: utils/reporter.py
"""HTML report generator for Mimiq pipeline runs."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import requests

from config import CLOUD_BRAIN_PORT

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


@dataclass
class StepRecord:
    phase_id: int
    description: str
    success: bool
    action_taken: str
    duration_seconds: float
    screenshot_path: str = ""


class MimiqReporter:
    """Builds a dark-themed HTML report of pipeline execution."""

    def __init__(self, goal: str, output_dir: Path) -> None:
        self.goal = goal
        self.output_dir = Path(output_dir)
        self._steps: list[StepRecord] = []

    def add_step(self, record: StepRecord) -> None:
        self._steps.append(record)

    def _get_amd_status(self) -> dict:
        try:
            resp = requests.get(
                f"http://127.0.0.1:{CLOUD_BRAIN_PORT}/health", timeout=2
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {"active_provider": "AMD — offline", "active_model": "unknown"}

    def generate(self) -> Path:
        status = self._get_amd_status()
        provider = status.get("active_provider", "unknown")
        model = status.get("active_model", "unknown")
        badge_color = "#22c55e" if "AMD" in provider and "offline" not in provider else "#ef4444"

        total_duration = sum(s.duration_seconds for s in self._steps)
        successes = sum(1 for s in self._steps if s.success)
        rate = (successes / len(self._steps) * 100) if self._steps else 0

        rows = ""
        for s in self._steps:
            ok = "✓" if s.success else "✗"
            ok_color = "#22c55e" if s.success else "#ef4444"
            rows += (
                f"<tr>"
                f"<td>{s.phase_id}</td>"
                f"<td>{s.description}</td>"
                f"<td style='color:{ok_color}'>{ok}</td>"
                f"<td>{s.action_taken}</td>"
                f"<td>{s.duration_seconds:.2f}s</td>"
                f"<td>{s.screenshot_path}</td>"
                f"</tr>"
            )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Mimiq Report</title>
<style>
body {{ background:#111111; color:#e5e7eb; font-family:Inter,system-ui,sans-serif; font-size:14px; margin:0; padding:2rem; }}
h1 {{ font-weight:500; margin-bottom:0.5rem; }}
.badge {{ display:inline-flex; align-items:center; gap:6px; border:0.5px solid #374151; padding:4px 10px; border-radius:4px; font-size:12px; }}
.dot {{ width:8px; height:8px; border-radius:50%; background:{badge_color}; }}
table {{ width:100%; border-collapse:collapse; margin-top:1.5rem; }}
th, td {{ padding:8px 12px; border-bottom:0.5px solid #374151; text-align:left; }}
th {{ color:#9ca3af; font-weight:400; }}
.summary {{ margin-top:1.5rem; color:#9ca3af; }}
</style>
</head>
<body>
<h1>Mimiq Report</h1>
<div class="badge"><span class="dot"></span>{provider} · {model}</div>
<p style="margin-top:1rem;"><strong>Goal:</strong> {self.goal}</p>
<table>
<thead><tr><th>Phase</th><th>Description</th><th>Success</th><th>Action</th><th>Duration</th><th>Screenshot</th></tr></thead>
<tbody>{rows}</tbody>
</table>
<div class="summary">
Total duration: {total_duration:.2f}s | Success rate: {rate:.0f}% ({successes}/{len(self._steps)})
</div>
</body>
</html>"""

        self.output_dir.mkdir(parents=True, exist_ok=True)
        report_path = self.output_dir / "report.html"
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write(html)
        logging.info("[reporter] Generated report: %s", report_path)
        return report_path

    def generate_from_history(self, history: list[dict]) -> Path:
        for item in history:
            self.add_step(
                StepRecord(
                    phase_id=item.get("phase_id", 0),
                    description=item.get("description", ""),
                    success=bool(item.get("success", False)),
                    action_taken=item.get("action_taken", ""),
                    duration_seconds=float(item.get("duration_seconds", 0.0)),
                    screenshot_path=item.get("screenshot_path", ""),
                )
            )
        return self.generate()
