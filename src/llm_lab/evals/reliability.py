from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from llm_lab.pipeline.contracts import Case, ToolCall
from llm_lab.pipeline.policies import RetryPolicy, call_with_retry_result
from llm_lab.tools.fault_injection import FaultInjectedTool, FaultSpec
from llm_lab.tools.registry import ToolRegistry, default_registry


def _run_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]


@dataclass
class ReliabilityResult:
    scenario_id: str
    ok: bool
    retries_used: int
    error: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "ok": self.ok,
            "retries_used": self.retries_used,
            "error": self.error,
        }


def run_reliability_suite(fault_matrix_path: Path, runs_dir: Path = Path("runs")) -> Path:
    matrix = yaml.safe_load(fault_matrix_path.read_text(encoding="utf-8"))
    scenarios = matrix.get("scenarios", [])
    run_id = _run_id()
    out_dir = runs_dir / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # Fixed case for tool reliability (MVP)
    case = Case(case_id="reliability_tool_case", prompt="What is BM25?", expected={})

    base_registry = default_registry()
    results: list[ReliabilityResult] = []

    retry_policy = RetryPolicy(max_attempts=3, base_sleep_s=0.01, backoff=2.0)

    tool_total = 0
    tool_ok = 0
    total_retries = 0
    transient_recovered = 0

    for s in scenarios:
        sid = s["id"]
        tool = s["tool"]
        mode = s["mode"]
        transient_failures = int(s.get("transient_failures", 0))

        # Fresh registry per scenario to isolate transient state
        reg = ToolRegistry()
        for name, fn in base_registry.tools.items():
            reg.tools[name] = fn
            reg.schemas[name] = base_registry.schemas[name]

        # Wrap target tool with fault injection
        if tool in reg.tools:
            reg.tools[tool] = FaultInjectedTool(
                reg.tools[tool],
                FaultSpec(mode=mode, transient_failures=transient_failures),
            )

        call = ToolCall(name=tool, args={"query": case.prompt, "top_k": 5})
        tool_total += 1

        def _exec():
            return reg.execute(call)

        # Retry until ToolResult.ok == True (or attempts exhausted)
        res, retries_used = call_with_retry_result(_exec, retry_policy, is_success=lambda r: bool(getattr(r, "ok", False)))
        total_retries += retries_used

        if res.ok:
            tool_ok += 1
            results.append(ReliabilityResult(scenario_id=sid, ok=True, retries_used=retries_used, error=None))
            if mode == "transient_error" and retries_used > 0:
                transient_recovered += 1
        else:
            results.append(ReliabilityResult(scenario_id=sid, ok=False, retries_used=retries_used, error=res.error))

    tool_success_rate = tool_ok / max(1, tool_total)
    tool_retry_rate = total_retries / max(1, tool_total)

    transient_total = sum(1 for s in scenarios if s.get("mode") == "transient_error")
    recovery_rate = transient_recovered / max(1, transient_total)

    report = {
        "suite": "reliability",
        "fault_matrix": str(fault_matrix_path),
        "tool_success_rate": tool_success_rate,
        "tool_retry_rate": tool_retry_rate,
        "recovery_rate": recovery_rate,
        "scenarios": [r.to_dict() for r in results],
    }
    (out_dir / "reliability_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    metrics = {
        "schema_compliance_rate": 1.0,
        "tool_success_rate": tool_success_rate,
        "tool_retry_rate": tool_retry_rate,
        "recovery_rate": recovery_rate,
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return out_dir