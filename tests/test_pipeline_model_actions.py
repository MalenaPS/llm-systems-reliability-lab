from __future__ import annotations

from pathlib import Path

from llm_lab.llm.base import LLMAdapter
from llm_lab.pipeline.contracts import Case
from llm_lab.pipeline.sut import PipelineConfig, SUTPipeline


class ToolCallingMockLLM(LLMAdapter):
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        if self.calls == 1:
            return '{"action":"tool_call","tool_name":"search_kb","args":{"query":"BM25","top_k":3}}'
        return '{"action":"final_answer","answer":"BM25 is a ranking function.","insufficient_evidence":false}'


def test_pipeline_accepts_model_tool_call_and_final_answer(tmp_path: Path) -> None:
    pipe = SUTPipeline(
        llm=ToolCallingMockLLM(),
        cfg=PipelineConfig(backend="mock", model="mock-v1", runs_dir=tmp_path),
    )

    case = Case(case_id="c1", prompt="What is BM25?", expected={})
    out, out_dir = pipe.run(case)

    assert out.success is True
    assert out.answer.startswith("BM25")
    assert len(out.tool_calls) >= 2
    assert len(out.tool_results) >= 2
    assert (out_dir / "output.json").exists()