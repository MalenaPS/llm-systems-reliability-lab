from __future__ import annotations

import json
from pathlib import Path

from llm_lab.evals.full import run_full_eval


def test_full_eval_writes_expected_artifacts(tmp_path: Path) -> None:
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

    out_dir = run_full_eval(
        backend="mock",
        model="mock-v1",
        cases_path=cases,
        runs_dir=tmp_path,
    )

    assert (out_dir / "metrics.json").exists()
    assert (out_dir / "llm_grades.json").exists()
    assert (out_dir / "leaderboard.md").exists()

    grades = json.loads((out_dir / "llm_grades.json").read_text(encoding="utf-8"))
    assert len(grades) == 2
    assert "score" in grades[0]
    assert "reason" in grades[0]

    metrics = json.loads((out_dir / "metrics.json").read_text(encoding="utf-8"))
    assert "llm_score_avg" in metrics
