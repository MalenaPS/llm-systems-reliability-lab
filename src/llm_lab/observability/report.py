from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_step_metrics(events_path: Path, out_path: Path) -> None:
    lines = events_path.read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in lines if line.strip()]

    per_step: dict[str, dict[str, Any]] = {}
    retries_total = 0
    tool_failures: dict[str, int] = {}

    for evt in events:
        step = str(evt.get("step", "unknown"))
        latency_ms = evt.get("latency_ms")
        success = evt.get("success")
        error_type = evt.get("error_type")
        tool_name = evt.get("tool_name")

        bucket = per_step.setdefault(
            step,
            {
                "count": 0,
                "success_count": 0,
                "failure_count": 0,
                "latency_ms_sum": 0,
                "latency_ms_avg": 0.0,
                "error_types": {},
            },
        )

        bucket["count"] += 1

        if success is True:
            bucket["success_count"] += 1
        elif success is False:
            bucket["failure_count"] += 1

        if isinstance(latency_ms, int):
            bucket["latency_ms_sum"] += latency_ms

        if error_type:
            bucket["error_types"][error_type] = bucket["error_types"].get(error_type, 0) + 1

        if evt.get("event_type") == "retry":
            retries_total += 1

        if evt.get("event_type") == "tool_result" and success is False and tool_name:
            tool_failures[str(tool_name)] = tool_failures.get(str(tool_name), 0) + 1

    for step, bucket in per_step.items():
        count = bucket["count"]
        bucket["latency_ms_avg"] = bucket["latency_ms_sum"] / count if count else 0.0

    report = {
        "steps": per_step,
        "retries_total": retries_total,
        "tool_failures": tool_failures,
        "slowest_step_by_avg_latency": None,
    }

    if per_step:
        slowest = max(per_step.items(), key=lambda kv: kv[1]["latency_ms_avg"])
        report["slowest_step_by_avg_latency"] = {
            "step": slowest[0],
            "latency_ms_avg": slowest[1]["latency_ms_avg"],
        }

    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")