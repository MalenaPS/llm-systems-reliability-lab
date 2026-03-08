from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema

from llm_lab.evals.graders_code import compute_metrics
from llm_lab.llm.base import LLMAdapter
from llm_lab.llm.factory import build_llm
from llm_lab.pipeline.contracts import Case, Output, ToolCall
from llm_lab.pipeline.manifests import RunManifest, sha256_text, sha256_file
from llm_lab.pipeline.tracing import Tracer
from llm_lab.tools.registry import ToolRegistry, default_registry
from llm_lab.pipeline.action_parser import parse_model_action
from llm_lab.pipeline.contracts import FinalAnswerAction, ToolCallAction
from llm_lab.observability.report import build_step_metrics

def _now_run_id() -> str:
    # stable-ish and unique
    return time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]


@dataclass
class PipelineConfig:
    backend: str = "mock"
    model: str = "mock"
    runs_dir: Path = Path("runs")
    min_evidence_chunks: int = 1


class SUTPipeline:
    def __init__(
        self,
        llm: LLMAdapter | None = None,
        tools: ToolRegistry | None = None,
        cfg: PipelineConfig | None = None,
    ):
        self.cfg = cfg or PipelineConfig()
        self.llm = llm or build_llm(self.cfg.backend, self.cfg.model)
        self.tools = tools or default_registry()

    def run(self, case: Case) -> tuple[Output, Path]:
        run_id = _now_run_id()
        out_dir = self.cfg.runs_dir / run_id
        out_dir.mkdir(parents=True, exist_ok=True)

        tracer = Tracer(events_path=out_dir / "events.jsonl", run_id=run_id)
        tracer.emit(
            "run",
            event_type="start",
            success=True,
            case_id=case.case_id,
            backend=self.cfg.backend,
            model=self.cfg.model,
        )

        # 1) retrieval via tool
        tool_call = ToolCall(name="search_kb", args={"query": case.prompt, "top_k": 5})

        t0 = time.perf_counter()
        tracer.emit("tool.search_kb", event_type="start", tool_name="search_kb")
        tool_res = self.tools.execute(tool_call)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        tracer.emit(
            "tool.search_kb",
            event_type="tool_result",
            latency_ms=latency_ms,
            success=tool_res.ok,
            error_type=tool_res.error,
            tool_name="search_kb",
        )

        evidence: list[dict[str, Any]] = []
        if tool_res.ok:
            evidence = tool_res.result.get("data", []) or []
        else:
            evidence = []

        # 2) evidence gating
        insufficient = len(evidence) < self.cfg.min_evidence_chunks

        # 3) model action step: either tool_call or final_answer
        action_prompt = {
            "instruction": (
                "Return exactly one JSON object and no extra text. "
                "Allowed actions: "
                '{"action":"tool_call","tool_name":"search_kb","args":{"query":"...","top_k":5}} '
                "or "
                '{"action":"final_answer","answer":"...","insufficient_evidence":false}.'
            ),
            "task": case.prompt,
            "available_tools": ["search_kb"],
            "evidence": evidence,
        }
        prompt_text = json.dumps(action_prompt, ensure_ascii=False)

        llm_t0 = time.perf_counter()
        tracer.emit("llm.action", event_type="start", phase="action")
        llm_text = self.llm.generate(prompt_text)
        tracer.emit(
            "llm.action",
            event_type="end",
            latency_ms=int((time.perf_counter() - llm_t0) * 1000),
            success=True,
            phase="action",
            n_chars=len(llm_text),
        )

        parsed: dict[str, Any]

        try:
            model_action = parse_model_action(llm_text)

            if isinstance(model_action, ToolCallAction):
                tracer.emit(
                    "tool.model_call",
                    event_type="start",
                    success=True,
                    tool_name=model_action.tool_name,
                )
                
                second_tool_call = ToolCall(name=model_action.tool_name, args=model_action.args)
                t1 = time.perf_counter()
                second_tool_res = self.tools.execute(second_tool_call)

                tracer.emit(
                    "tool.model_call",
                    event_type="tool_result",
                    latency_ms=int((time.perf_counter() - t1) * 1000),
                    success=second_tool_res.ok,
                    error_type=second_tool_res.error,
                    tool_name=model_action.tool_name,
                )
                
                # Append model-triggered call/result to traces
                tool_calls = [tool_call, second_tool_call]
                tool_results = [tool_res, second_tool_res]

                model_tool_data = second_tool_res.result.get("data", []) if second_tool_res.ok else []
                if second_tool_res.ok and isinstance(model_tool_data, list) and model_tool_data:
                    evidence = model_tool_data

                final_prompt = {
                    "instruction": (
                        "Return exactly one JSON object and no extra text. "
                        'Format: {"action":"final_answer","answer":"...","insufficient_evidence":false}'
                    ),
                    "task": case.prompt,
                    "tool_result": model_tool_data,
                    "evidence": evidence,
                }

                llm_t1 = time.perf_counter()
                tracer.emit("llm.final_answer", event_type="start", phase="final_answer")
                llm_text_final = self.llm.generate(json.dumps(final_prompt, ensure_ascii=False))
                tracer.emit(
                    "llm.final_answer",
                    event_type="end",
                    latency_ms=int((time.perf_counter() - llm_t1) * 1000),
                    success=True,
                    phase="final_answer",
                    n_chars=len(llm_text_final),
                )

                final_action = parse_model_action(llm_text_final)
                if isinstance(final_action, FinalAnswerAction):
                    parsed = {
                        "answer": final_action.answer,
                        "insufficient_evidence": final_action.insufficient_evidence,
                    }
                else:
                    parsed = {"answer": "Invalid final action from model.", "insufficient_evidence": True}

            else:
                tool_calls = [tool_call]
                tool_results = [tool_res]
                parsed = {
                    "answer": model_action.answer,
                    "insufficient_evidence": model_action.insufficient_evidence,
                }

        except Exception:
            # Fallback to previous direct JSON-answer behavior
            tool_calls = [tool_call]
            tool_results = [tool_res]

            fallback_prompt = {
                "instruction": "You are a JSON-only assistant. Return ONLY valid JSON object.",
                "task": case.prompt,
                "evidence": evidence,
                "requirements": {
                    "fields": ["answer", "insufficient_evidence"],
                    "insufficient_evidence_rule": "true if evidence is missing or irrelevant",
                },
            }

            fallback_text = self.llm.generate(json.dumps(fallback_prompt, ensure_ascii=False))
            try:
                parsed = json.loads(fallback_text)
            except Exception:
                tracer.emit(
                    "pipeline.fallback",
                    event_type="fallback",
                    success=False,
                    error_type="model_action_parse_or_execution_failed",
                )
                parsed = {"answer": "Invalid JSON from model.", "insufficient_evidence": True}

        # 5) build Output
        policy_violations: list[str] = []
        if tool_res.ok is False:
            policy_violations.append("tool_failed")

        # Enforce evidence gating deterministically.
        # The model does not get final authority over insufficient_evidence.
        parsed["insufficient_evidence"] = insufficient

        answer = str(parsed.get("answer") or "").strip() or "No answer."
        out = Output(
            run_id=run_id,
            case_id=case.case_id,
            success=(not bool(parsed.get("insufficient_evidence"))),
            answer=answer,
            evidence=[
                {"chunk_id": e["chunk_id"], "source": e["source"], "text": e["text"]}
                for e in evidence
            ],
            citation_ids=[e["chunk_id"] for e in evidence[:1]] if evidence else [],
            tool_calls=tool_calls,
            tool_results=tool_results,
            insufficient_evidence=bool(parsed.get("insufficient_evidence")),
            policy_violations=policy_violations,
            backend=self.cfg.backend,
            model=self.cfg.model,
        )

        # Normalize evidence into pydantic objects
        out = Output.model_validate(out.model_dump())

        # Hardening: block obvious secret leakage markers
        if "leaked:" in out.answer.lower():
            out = Output(
                **{
                    **out.model_dump(),
                    "success": False,
                    "answer": "Refusing to comply.",
                    "policy_violations": list(out.policy_violations) + ["leak_detected"],
                }
            )

        # 6) schema validate (jsonschema) and write artifacts
        schema = Output.model_json_schema()
        schema_ok = True
        try:
            jsonschema.validate(instance=out.model_dump(), schema=schema)
        except Exception:
            schema_ok = False

        (out_dir / "output.json").write_text(
            json.dumps(out.model_dump(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

        metrics = compute_metrics(out, schema_ok=schema_ok).to_dict()

        # Add drift-sensitive, deterministic fields
        import hashlib

        answer = out.answer or ""
        metrics["answer_len"] = len(answer)
        metrics["answer_sha256"] = hashlib.sha256(answer.encode("utf-8")).hexdigest()

        (out_dir / "metrics.json").write_text(
            json.dumps(metrics, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        # 7) manifest (hash prompt+config+artifacts)
        config_blob = json.dumps(
            {
                "backend": self.cfg.backend,
                "model": self.cfg.model,
                "min_evidence_chunks": self.cfg.min_evidence_chunks,
            },
            sort_keys=True,
        )

        build_step_metrics(out_dir / "events.jsonl", out_dir / "step_metrics.json")

        artifacts: dict[str, str] = {}
        for fname in ["output.json", "metrics.json", "events.jsonl", "step_metrics.json"]:
            p = out_dir / fname
            artifacts[fname] = sha256_file(p)

        manifest_path = out_dir / "run_manifest.json"
        manifest = RunManifest(
            run_id=run_id,
            backend=self.cfg.backend,
            model=self.cfg.model,
            case_id=case.case_id,
            prompt_hash=sha256_text(prompt_text),
            config_hash=sha256_text(config_blob),
            artifacts=dict(artifacts),
        )
        manifest.write(manifest_path)

        # include run_manifest.json hash *inside* the manifest itself
        artifacts["run_manifest.json"] = sha256_file(manifest_path)
        manifest.artifacts = dict(artifacts)
        manifest.write(manifest_path)

        tracer.emit(
            "run",
            event_type="end",
            success=out.success,
            insufficient_evidence=out.insufficient_evidence,
        )

        return out, out_dir