from __future__ import annotations

import json
from typing import Any

import jsonschema

from llm_lab.pipeline.contracts import (
    FinalAnswerAction,
    ModelActionEnvelope,
    ToolCallAction,
)

MODEL_ACTION_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "ModelActionEnvelope",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "action": {
            "type": "string",
            "enum": ["tool_call", "final_answer"],
        },
        "tool_name": {"type": "string", "minLength": 1},
        "args": {"type": "object"},
        "answer": {"type": "string", "minLength": 1},
        "insufficient_evidence": {"type": "boolean"},
    },
    "required": ["action"],
    "allOf": [
        {
            "if": {"properties": {"action": {"const": "tool_call"}}},
            "then": {"required": ["tool_name", "args"]},
        },
        {
            "if": {"properties": {"action": {"const": "final_answer"}}},
            "then": {"required": ["answer", "insufficient_evidence"]},
        },
    ],
}


def extract_first_json_object(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for idx, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[idx:])
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue
    raise ValueError("no_valid_json_object_found")


def parse_model_action(text: str) -> ToolCallAction | FinalAnswerAction:
    raw = extract_first_json_object(text)
    jsonschema.validate(raw, MODEL_ACTION_SCHEMA)

    env = ModelActionEnvelope.model_validate(raw)

    if env.action == "tool_call":
        return ToolCallAction(
            action="tool_call",
            tool_name=str(env.tool_name),
            args=dict(env.args or {}),
        )

    return FinalAnswerAction(
        action="final_answer",
        answer=str(env.answer),
        insufficient_evidence=bool(env.insufficient_evidence),
    )
