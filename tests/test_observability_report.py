from __future__ import annotations

import json
from pathlib import Path

from llm_lab.observability.report import build_step_metrics


def test_build_step_metrics(tmp_path: Path) -> None:
    events_path = tmp_path / "events.jsonl"
    events = [
        {
            "timestamp_ms": 1,
            "run_id": "r1",
            "step": "tool.search_kb",
            "event_type": "tool_result",
            "latency_ms": 10,
            "success": True,
            "error_type": None,
            "tool_name": "search_kb",
        },
        {
            "timestamp_ms": 2,
            "run_id": "r1",
            "step": "llm.action",
            "event_type": "end",
            "latency_ms": 25,
            "success": True,
            "error_type": None,
        },
        {
            "timestamp_ms": 3,
            "run_id": "r1",
            "step": "tool.model_call",
            "event_type": "tool_result",
            "latency_ms": 5,
            "success": False,
            "error_type": "tool_not_allowed",
            "tool_name": "hack_tool",
        },
        {
            "timestamp_ms": 4,
            "run_id": "r1",
            "step": "pipeline.retry",
            "event_type": "retry",
            "latency_ms": 0,
            "success": False,
            "error_type": "transient_error",
        },
    ]
    events_path.write_text(
        "\n".join(json.dumps(e) for e in events) + "\n",
        encoding="utf-8",
    )

    out_path = tmp_path / "step_metrics.json"
    build_step_metrics(events_path, out_path)

    report = json.loads(out_path.read_text(encoding="utf-8"))
    assert "steps" in report
    assert "tool_failures" in report
    assert report["retries_total"] == 1
    assert report["tool_failures"]["hack_tool"] == 1
    assert report["slowest_step_by_avg_latency"]["step"] == "llm.action"