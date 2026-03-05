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
from llm_lab.llm.mock import MockLLM
from llm_lab.pipeline.contracts import Case, Output, ToolCall
from llm_lab.pipeline.manifests import RunManifest, sha256_text, sha256_file
from llm_lab.pipeline.tracing import Tracer
from llm_lab.tools.registry import ToolRegistry, default_registry


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
        self.llm = llm or MockLLM()
        self.tools = tools or default_registry()

    def run(self, case: Case) -> tuple[Output, Path]:
        run_id = _now_run_id()
        out_dir = self.cfg.runs_dir / run_id
        out_dir.mkdir(parents=True, exist_ok=True)

        tracer = Tracer(events_path=out_dir / "events.jsonl")
        tracer.emit("run_start", run_id=run_id, case_id=case.case_id, backend=self.cfg.backend, model=self.cfg.model)

        # 1) retrieval via tool
        tracer.emit("tool_call", tool_name="search_kb")
        tool_call = ToolCall(name="search_kb", args={"query": case.prompt, "top_k": 5})
        tool_res = self.tools.execute(tool_call)
        tracer.emit("tool_result", tool_name="search_kb", ok=tool_res.ok, error=tool_res.error)

        evidence: list[dict[str, Any]] = []
        if tool_res.ok:
            evidence = tool_res.result.get("data", []) or []
        else:
            evidence = []

        # 2) evidence gating
        insufficient = len(evidence) < self.cfg.min_evidence_chunks

        # 3) compose prompt (MVP)
        prompt = {
            "instruction": "You are a JSON-only assistant. Return ONLY valid JSON object.",
            "task": case.prompt,
            "evidence": evidence,
            "requirements": {
                "fields": ["answer", "insufficient_evidence"],
                "insufficient_evidence_rule": "true if evidence is missing or irrelevant",
            },
        }
        prompt_text = json.dumps(prompt, ensure_ascii=False)

        tracer.emit("llm_generate_start")
        llm_text = self.llm.generate(prompt_text)
        tracer.emit("llm_generate_end", n_chars=len(llm_text))

        # 4) parse LLM JSON (strict; if fails, fallback)
        parsed: dict[str, Any]
        try:
            parsed = json.loads(llm_text)
        except Exception:
            parsed = {"answer": "Invalid JSON from model.", "insufficient_evidence": True}

        # 5) build Output
        policy_violations: list[str] = []
        if tool_res.ok is False:
            policy_violations.append("tool_failed")

        # Enforce evidence gating deterministically (override model if needed)
        if insufficient:
            parsed["insufficient_evidence"] = True

        answer = str(parsed.get("answer") or "").strip() or "No answer."
        out = Output(
            run_id=run_id,
            case_id=case.case_id,
            success=(not bool(parsed.get("insufficient_evidence"))),
            answer=answer,
            evidence=[{"chunk_id": e["chunk_id"], "source": e["source"], "text": e["text"]} for e in evidence],
            citation_ids=[e["chunk_id"] for e in evidence[:1]] if evidence else [],
            tool_calls=[tool_call],
            tool_results=[tool_res],
            insufficient_evidence=bool(parsed.get("insufficient_evidence")),
            policy_violations=policy_violations,
            backend=self.cfg.backend,
            model=self.cfg.model,
        )

        # Normalize evidence into pydantic objects
        out = Output.model_validate(out.model_dump())

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

        metrics = compute_metrics(out, schema_ok=schema_ok)
        (out_dir / "metrics.json").write_text(
            json.dumps(metrics.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

        # 7) manifest (hash prompt+config+artifacts)
        config_blob = json.dumps(
            {"backend": self.cfg.backend, "model": self.cfg.model, "min_evidence_chunks": self.cfg.min_evidence_chunks},
            sort_keys=True,
        )

        artifacts: dict[str, str] = {}
        for fname in ["output.json", "metrics.json", "events.jsonl"]:
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

        tracer.emit("run_end", run_id=run_id, success=out.success, insufficient_evidence=out.insufficient_evidence)
        return out, out_dir