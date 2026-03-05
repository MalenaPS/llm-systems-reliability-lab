from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import jsonschema

from llm_lab.pipeline.contracts import ToolCall, ToolResult
from llm_lab.tools.impl.search_kb import SearchKBTool


class ToolRegistry:
    """
    Tool router with JSON Schema validation and allowlist.
    """

    def __init__(self) -> None:
        self.tools: dict[str, Callable[..., Any]] = {}
        self.schemas: dict[str, dict] = {}

    def register(self, name: str, func: Callable[..., Any], schema_path: Path) -> None:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.tools[name] = func
        self.schemas[name] = schema

    def execute(self, call: ToolCall) -> ToolResult:
        if call.name not in self.tools:
            return ToolResult(
                name=call.name,
                ok=False,
                result={},
                error="tool_not_allowed",
            )

        schema = self.schemas[call.name]

        try:
            jsonschema.validate(call.args, schema)
        except jsonschema.ValidationError as e:
            return ToolResult(
                name=call.name,
                ok=False,
                result={},
                error=f"invalid_args: {e.message}",
            )

        try:
            raw = self.tools[call.name](**call.args)

            # Normalize output to JSON-serializable shape.
            if isinstance(raw, list):
                norm_list = []
                for item in raw:
                    if hasattr(item, "model_dump"):
                        norm_list.append(item.model_dump())
                    elif isinstance(item, dict):
                        norm_list.append(item)
                    else:
                        raise TypeError("tool_return_item_invalid_type")
                norm: Any = norm_list
            elif isinstance(raw, dict):
                norm = raw
            else:
                raise TypeError("tool_return_invalid_type")

            return ToolResult(
                name=call.name,
                ok=True,
                result={"data": norm},
                error=None,
            )

        except Exception as e:
            return ToolResult(
                name=call.name,
                ok=False,
                result={},
                error=str(e),
            )


def default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    search_tool = SearchKBTool.default()
    registry.register(
        "search_kb",
        search_tool,
        Path("src/llm_lab/tools/schemas/tool_search_kb.schema.json"),
    )
    return registry
