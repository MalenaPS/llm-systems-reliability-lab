from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from llm_lab.pipeline.contracts import Output


def test_output_schema_is_valid_jsonschema() -> None:
    schema = Output.model_json_schema()
    jsonschema.Draft202012Validator.check_schema(schema)


def test_example_output_validates_against_schema(tmp_path: Path) -> None:
    schema = Output.model_json_schema()
    example = {
        "run_id": "r1",
        "case_id": "c1",
        "success": True,
        "answer": "BM25 is a ranking function used in information retrieval.",
        "evidence": [],
        "citation_ids": [],
        "tool_calls": [],
        "tool_results": [],
        "insufficient_evidence": False,
        "policy_violations": [],
        "backend": "mock",
        "model": "mock",
    }
    jsonschema.validate(instance=example, schema=schema)

    # Also verify we can dump/load JSON cleanly
    p = tmp_path / "output.json"
    p.write_text(json.dumps(example, indent=2), encoding="utf-8")
    loaded = json.loads(p.read_text(encoding="utf-8"))
    jsonschema.validate(instance=loaded, schema=schema)
