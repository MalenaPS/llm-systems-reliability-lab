from __future__ import annotations

import json
from pathlib import Path

from llm_lab.evals.reliability import run_reliability_suite


def test_reliability_transient_recovers(tmp_path: Path) -> None:
    # Minimal matrix with transient scenario only
    matrix_path = tmp_path / "fault_matrix.yaml"
    matrix_path.write_text(
        "\n".join(
            [
                "version: 1",
                "scenarios:",
                "  - id: transient_then_ok",
                "    tool: search_kb",
                "    mode: transient_error",
                "    transient_failures: 1",
            ]
        ),
        encoding="utf-8",
    )

    out_dir = run_reliability_suite(matrix_path, runs_dir=tmp_path)
    report = json.loads((out_dir / "reliability_report.json").read_text(encoding="utf-8"))
    assert report["recovery_rate"] == 1.0
    assert report["scenarios"][0]["ok"] is True
    assert report["scenarios"][0]["retries_used"] >= 1