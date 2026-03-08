from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path

import yaml

from llm_lab.drift.compare import compute_drift_report
from llm_lab.pipeline.contracts import Case
from llm_lab.pipeline.sut import PipelineConfig, SUTPipeline


def _run_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]


def _load_cases(path: Path) -> list[Case]:
    lines = path.read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in lines if line.strip()]
    cases: list[Case] = []
    for row in rows:
        cases.append(Case(case_id=row["case_id"], prompt=row["prompt"], expected=row.get("expected", {})))
    return cases


def _aggregate_metrics(run_root: Path) -> dict[str, float]:
    """
    Aggregate numeric metrics across per-case metrics.json.
    """
    metrics_files = list(run_root.rglob("metrics.json"))
    per_case = [p for p in metrics_files if p.parent != run_root]

    sums: dict[str, float] = {}
    n = 0
    for p in per_case:
        m = json.loads(p.read_text(encoding="utf-8"))
        for k, v in m.items():
            if isinstance(v, (int, float)):
                sums[k] = sums.get(k, 0.0) + float(v)
        n += 1

    if n == 0:
        return {}

    return {k: v / n for k, v in sums.items()}


def _collect_outputs_by_case(run_root: Path) -> dict[str, dict]:
    """
    Return case_id -> output.json payload.
    Uses output.json contents, not directory names.
    """
    outputs: dict[str, dict] = {}
    output_files = list(run_root.rglob("output.json"))
    per_case = [p for p in output_files if p.parent != run_root]

    for p in per_case:
        data = json.loads(p.read_text(encoding="utf-8"))
        case_id = data.get("case_id")
        if isinstance(case_id, str):
            outputs[case_id] = data

    return outputs


_WORD_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokenize(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def _jaccard_similarity(a: str, b: str) -> float:
    ta = _tokenize(a)
    tb = _tokenize(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def run_drift(matrix_path: Path, runs_dir: Path = Path("runs")) -> Path:
    cfg = yaml.safe_load(matrix_path.read_text(encoding="utf-8"))
    cases_path = Path(cfg["cases_path"])
    runs = cfg["runs"]

    cases = _load_cases(cases_path)

    drift_run_id = _run_id()
    out_dir = runs_dir / drift_run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    per_run_metrics: dict[str, dict[str, float]] = {}

    for r in runs:
        rid = r["id"]
        backend = r["backend"]
        model = r["model"]

        run_root = out_dir / rid
        run_root.mkdir(parents=True, exist_ok=True)

        pipe = SUTPipeline(cfg=PipelineConfig(backend=backend, model=model, runs_dir=run_root))

        for c in cases:
            pipe.run(c)

        per_run_metrics[rid] = _aggregate_metrics(run_root)
        per_run_metrics[rid]["_case_count"] = float(len(cases))

    baseline_id = runs[0]["id"]
    candidate_id = runs[1]["id"]

    report = compute_drift_report(per_run_metrics[baseline_id], per_run_metrics[candidate_id])

    baseline_outputs = _collect_outputs_by_case(out_dir / baseline_id)
    candidate_outputs = _collect_outputs_by_case(out_dir / candidate_id)
    common_cases = set(baseline_outputs.keys()) & set(candidate_outputs.keys())

    same_hash_count = 0
    similarity_values: list[float] = []

    for case_id in common_cases:
        a_answer = str(baseline_outputs[case_id].get("answer", ""))
        b_answer = str(candidate_outputs[case_id].get("answer", ""))

        if a_answer and b_answer:
            if a_answer == b_answer:
                same_hash_count += 1
            similarity_values.append(_jaccard_similarity(a_answer, b_answer))
        else:
            similarity_values.append(0.0)

    answer_hash_stability_rate = same_hash_count / max(1, len(common_cases))
    answer_similarity_avg = sum(similarity_values) / max(1, len(similarity_values))

    schema_delta = per_run_metrics[candidate_id].get("schema_compliance_rate", 0.0) - per_run_metrics[baseline_id].get("schema_compliance_rate", 0.0)
    tool_success_delta = per_run_metrics[candidate_id].get("tool_success_rate", 0.0) - per_run_metrics[baseline_id].get("tool_success_rate", 0.0)
    policy_violation_delta = per_run_metrics[candidate_id].get("policy_violation_rate", 0.0) - per_run_metrics[baseline_id].get("policy_violation_rate", 0.0)
    insufficient_evidence_delta = per_run_metrics[candidate_id].get("insufficient_evidence_rate", 0.0) - per_run_metrics[baseline_id].get("insufficient_evidence_rate", 0.0)

    drift_report = {
        "suite": "drift",
        "matrix": str(matrix_path),
        "baseline": baseline_id,
        "candidate": candidate_id,
        "baseline_metrics": per_run_metrics[baseline_id],
        "candidate_metrics": per_run_metrics[candidate_id],
        "answer_hash_stability_rate": answer_hash_stability_rate,
        "answer_similarity_avg": answer_similarity_avg,
        "schema_delta": schema_delta,
        "tool_success_delta": tool_success_delta,
        "policy_violation_delta": policy_violation_delta,
        "insufficient_evidence_delta": insufficient_evidence_delta,
        **report,
    }

    matrix_name = matrix_path.stem.lower()
    if "mock" in matrix_name:
        report_json_name = "drift_report_mock.json"
        report_md_name = "drift_report_mock.md"
    elif "local" in matrix_name or "dev" in matrix_name:
        report_json_name = "drift_report_local.json"
        report_md_name = "drift_report_local.md"
    else:
        report_json_name = "drift_report.json"
        report_md_name = "drift_report.md"

    (out_dir / "drift_report.json").write_text(
        json.dumps(drift_report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / report_json_name).write_text(
        json.dumps(drift_report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lines = []
    lines.append("# Drift Report")
    lines.append("")
    lines.append(f"- baseline: `{baseline_id}`")
    lines.append(f"- candidate: `{candidate_id}`")
    lines.append(f"- drift_score: `{drift_report['drift_score']}`")
    lines.append(f"- answer_hash_stability_rate: `{drift_report['answer_hash_stability_rate']}`")
    lines.append(f"- answer_similarity_avg: `{drift_report['answer_similarity_avg']}`")
    lines.append(f"- schema_delta: `{drift_report['schema_delta']}`")
    lines.append(f"- tool_success_delta: `{drift_report['tool_success_delta']}`")
    lines.append(f"- policy_violation_delta: `{drift_report['policy_violation_delta']}`")
    lines.append(f"- insufficient_evidence_delta: `{drift_report['insufficient_evidence_delta']}`")
    lines.append("")
    lines.append("| metric | baseline | candidate | delta |")
    lines.append("|---|---:|---:|---:|")
    for d in drift_report["deltas"]:
        lines.append(f"| {d['metric']} | {d['baseline']:.3f} | {d['candidate']:.3f} | {d['delta']:.3f} |")

    markdown_text = "\n".join(lines) + "\n"
    (out_dir / "drift_report.md").write_text(markdown_text, encoding="utf-8")
    (out_dir / report_md_name).write_text(markdown_text, encoding="utf-8")

    return out_dir