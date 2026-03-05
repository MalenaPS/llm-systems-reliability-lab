from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DriftDelta:
    metric: str
    baseline: float
    candidate: float
    delta: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "baseline": self.baseline,
            "candidate": self.candidate,
            "delta": self.delta,
        }


def compute_drift_report(baseline_metrics: dict[str, float], candidate_metrics: dict[str, float]) -> dict[str, Any]:
    keys = sorted(set(baseline_metrics.keys()) | set(candidate_metrics.keys()))
    deltas: list[DriftDelta] = []
    drift_score = 0.0

    for k in keys:
        b = float(baseline_metrics.get(k, 0.0))
        c = float(candidate_metrics.get(k, 0.0))
        d = c - b
        deltas.append(DriftDelta(metric=k, baseline=b, candidate=c, delta=d))
        drift_score += abs(d)

    return {
        "deltas": [x.to_dict() for x in deltas],
        "drift_score": drift_score,
    }