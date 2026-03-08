from __future__ import annotations

import json
from pathlib import Path

from llm_lab.drift.runner import run_drift


def test_drift_report_includes_answer_similarity(tmp_path: Path) -> None:
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

    matrix = tmp_path / "drift_mock.yaml"
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
    report = json.loads((out_dir / "drift_report_mock.json").read_text(encoding="utf-8"))

    assert "answer_similarity_avg" in report
    assert 0.0 <= report["answer_similarity_avg"] <= 1.0
    assert "answer_hash_stability_rate" in report
    assert 0.0 <= report["answer_hash_stability_rate"] <= 1.0