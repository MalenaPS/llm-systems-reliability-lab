from __future__ import annotations

import json
from pathlib import Path

from llm_lab.pipeline.contracts import Output


def export_output_schema(path: Path) -> None:
    schema = Output.model_json_schema()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
