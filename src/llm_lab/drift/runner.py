from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from llm_lab.drift.compare import compute_drift_report
from llm_lab.pipeline.contracts import Case
from llm_lab.pipeline.sut import PipelineConfig, SUTPipeline


def _run_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]


def _load_cases(path: Path) -> list[Case]:
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    cases: list[Case] = []
    for r in rows:
        cases.append(Case(case_id=r["case_id"], prompt=r["prompt"], expected=r.get("expected", {})))
    return cases


def _aggregate_metrics(run_root: Path) -> dict[str, float]:
    """
    Aggregate numeric metrics across per-case metrics.json.
    Also compute avg_answer_len if present.
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

def _collect_answer_hashes(run_root: Path) -> dict[str, str]:
    """
    Return case_dir_name -> answer_sha256 (from per-case metrics.json).
    """
    hashes: dict[str, str] = {}
    metrics_files = list(run_root.rglob("metrics.json"))
    per_case = [p for p in metrics_files if p.parent != run_root]
    for p in per_case:
        m = json.loads(p.read_text(encoding="utf-8"))
        h = m.get("answer_sha256")
        if isinstance(h, str):
            # use the case run directory name as key (unique within run)
            hashes[p.parent.name] = h
    return hashes


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
        # store per-case answer hashes for stability comparison
        per_run_metrics[rid]["_case_count"] = float(len(cases))

    # Compare first two entries (MVP)
        baseline_id = runs[0]["id"]
    candidate_id = runs[1]["id"]

    # Compare numeric metrics
    report = compute_drift_report(per_run_metrics[baseline_id], per_run_metrics[candidate_id])

    # Answer hash stability across cases (drift-sensitive)
    baseline_hashes = _collect_answer_hashes(out_dir / baseline_id)
    candidate_hashes = _collect_answer_hashes(out_dir / candidate_id)
    common = set(baseline_hashes.keys()) & set(candidate_hashes.keys())

    same = 0
    for k in common:
        if baseline_hashes[k] == candidate_hashes[k]:
            same += 1

    answer_hash_stability_rate = same / max(1, len(common))

    drift_report = {
        "suite": "drift",
        "matrix": str(matrix_path),
        "baseline": baseline_id,
        "candidate": candidate_id,
        "baseline_metrics": per_run_metrics[baseline_id],
        "candidate_metrics": per_run_metrics[candidate_id],
        "answer_hash_stability_rate": answer_hash_stability_rate,
        **report,
    }

    (out_dir / "drift_report.json").write_text(json.dumps(drift_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Simple markdown view
    lines = []
    lines.append("# Drift Report")
    lines.append("")
    lines.append(f"- baseline: `{baseline_id}`")
    lines.append(f"- candidate: `{candidate_id}`")
    lines.append(f"- drift_score: `{drift_report['drift_score']}`")
    lines.append(f"- answer_hash_stability_rate: `{drift_report['answer_hash_stability_rate']}`")
    lines.append("")
    lines.append("| metric | baseline | candidate | delta |")
    lines.append("|---|---:|---:|---:|")
    for d in drift_report["deltas"]:
        lines.append(f"| {d['metric']} | {d['baseline']:.3f} | {d['candidate']:.3f} | {d['delta']:.3f} |")
    (out_dir / "drift_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return out_dir