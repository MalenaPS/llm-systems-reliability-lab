from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from llm_lab.evals.grader_llm import build_grader_llm, grade_output_with_llm
from llm_lab.pipeline.contracts import Case
from llm_lab.pipeline.sut import PipelineConfig, SUTPipeline


def _run_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]


def _load_cases(path: Path) -> list[Case]:
    lines = path.read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in lines if line.strip()]
    return [
        Case(case_id=row["case_id"], prompt=row["prompt"], expected=row.get("expected", {}))
        for row in rows
    ]


def run_full_eval(
    backend: str,
    model: str,
    cases_path: Path = Path("data") / "benchmarks" / "cases.jsonl",
    runs_dir: Path = Path("runs"),
) -> Path:
    cases = _load_cases(cases_path)

    run_id = _run_id()
    out_dir = runs_dir / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    pipe = SUTPipeline(cfg=PipelineConfig(backend=backend, model=model, runs_dir=out_dir))
    grader_llm = build_grader_llm(backend, model)

    per_case_metrics: list[dict] = []
    per_case_grades: list[dict] = []

    for case in cases:
        output, case_dir = pipe.run(case)

        metrics_path = case_dir / "metrics.json"
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        per_case_metrics.append(
            {
                "case_id": case.case_id,
                "run_id": output.run_id,
                **metrics,
            }
        )

        grade = grade_output_with_llm(case, output, grader_llm)
        grade_dict = {
            "case_id": case.case_id,
            "run_id": output.run_id,
            **grade.model_dump(),
        }
        per_case_grades.append(grade_dict)

    # Aggregate numeric metrics
    agg_metrics: dict[str, float] = {}
    if per_case_metrics:
        numeric_keys = {
            k
            for row in per_case_metrics
            for k, v in row.items()
            if isinstance(v, (int, float))
        }
        for key in numeric_keys:
            values = [float(row[key]) for row in per_case_metrics if key in row]
            if values:
                agg_metrics[key] = sum(values) / len(values)

    if per_case_grades:
        agg_metrics["llm_score_avg"] = sum(g["score"] for g in per_case_grades) / len(per_case_grades)
        agg_metrics["llm_helpfulness_avg"] = (
            sum(g["helpfulness"] for g in per_case_grades) / len(per_case_grades)
        )
        agg_metrics["llm_constraint_adherence_avg"] = (
            sum(g["constraint_adherence"] for g in per_case_grades) / len(per_case_grades)
        )
        agg_metrics["llm_evidence_use_avg"] = (
            sum(g["evidence_use"] for g in per_case_grades) / len(per_case_grades)
        )

    (out_dir / "metrics.json").write_text(
        json.dumps(agg_metrics, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / "llm_grades.json").write_text(
        json.dumps(per_case_grades, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Evaluation Leaderboard",
        "",
        f"- backend: `{backend}`",
        f"- model: `{model}`",
        "",
        "## Aggregate metrics",
        "",
    ]
    for key in sorted(agg_metrics):
        value = agg_metrics[key]
        if isinstance(value, float):
            lines.append(f"- {key}: `{value:.3f}`")
        else:
            lines.append(f"- {key}: `{value}`")

    lines.extend(
        [
            "",
            "## Per-case LLM grades",
            "",
            "| case_id | score | helpfulness | constraint_adherence | evidence_use |",
            "|---|---:|---:|---:|---:|",
        ]
    )

    for g in per_case_grades:
        lines.append(
            f"| {g['case_id']} | {g['score']} | {g['helpfulness']} | "
            f"{g['constraint_adherence']} | {g['evidence_use']} |"
        )

    (out_dir / "leaderboard.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_dir