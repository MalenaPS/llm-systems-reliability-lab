from __future__ import annotations

import json
from pathlib import Path

from llm_lab.drift.runner import run_drift


def test_drift_report_generated(tmp_path: Path) -> None:
    # Create minimal cases.jsonl
    cases = tmp_path / "cases.jsonl"
    cases.write_text(
        "\n".join(
            [
                '{"case_id":"c1","prompt":"What is BM25?","expected":{}}',
                '{"case_id":"c2","prompt":"What is prompt injection?","expected":{}}',
            ]
        ),
        encoding="utf-8",
    )

    matrix = tmp_path / "drift.yaml"
    matrix.write_text(
        "\n".join(
            [
                "version: 1",
                f"cases_path: {cases.as_posix()}",
                "runs:",
                "  - id: baseline",
                "    backend: mock",
                "    model: mock-v1",
                "  - id: candidate",
                "    backend: mock",
                "    model: mock-v2",
            ]
        ),
        encoding="utf-8",
    )

    out_dir = run_drift(matrix, runs_dir=tmp_path)
    assert (out_dir / "drift_report.json").exists()
    report = json.loads((out_dir / "drift_report.json").read_text(encoding="utf-8"))
    assert report["suite"] == "drift"
    assert "drift_score" in report