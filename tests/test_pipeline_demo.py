from __future__ import annotations

import json
from pathlib import Path

from llm_lab.pipeline.contracts import Case
from llm_lab.pipeline.sut import PipelineConfig, SUTPipeline


def test_pipeline_writes_artifacts(tmp_path: Path) -> None:
    cfg = PipelineConfig(runs_dir=tmp_path, backend="mock", model="mock")
    pipe = SUTPipeline(cfg=cfg)

    case = Case(case_id="c1", prompt="What is BM25?", expected={})
    out, out_dir = pipe.run(case)

    assert (out_dir / "output.json").exists()
    assert (out_dir / "metrics.json").exists()
    assert (out_dir / "events.jsonl").exists()
    assert (out_dir / "run_manifest.json").exists()

    data = json.loads((out_dir / "output.json").read_text(encoding="utf-8"))
    assert data["case_id"] == "c1"
