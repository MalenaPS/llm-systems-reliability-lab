from __future__ import annotations

import jsonschema
import pytest

from llm_lab.pipeline.action_parser import (
    MODEL_ACTION_SCHEMA,
    parse_model_action,
)
from llm_lab.pipeline.contracts import FinalAnswerAction, ToolCallAction


def test_model_action_schema_is_valid() -> None:
    jsonschema.Draft202012Validator.check_schema(MODEL_ACTION_SCHEMA)


def test_parse_tool_call_action() -> None:
    text = '{"action":"tool_call","tool_name":"search_kb","args":{"query":"BM25","top_k":3}}'
    action = parse_model_action(text)

    assert isinstance(action, ToolCallAction)
    assert action.tool_name == "search_kb"
    assert action.args["query"] == "BM25"


def test_parse_final_answer_action() -> None:
    text = '{"action":"final_answer","answer":"BM25 is a ranking function.","insufficient_evidence":false}'
    action = parse_model_action(text)

    assert isinstance(action, FinalAnswerAction)
    assert action.answer.startswith("BM25")
    assert action.insufficient_evidence is False


def test_parse_wrapped_json_action() -> None:
    text = (
        "Here is the result:\n"
        '{"action":"final_answer","answer":"Safe answer.","insufficient_evidence":false}\n'
        "Done."
    )
    action = parse_model_action(text)

    assert isinstance(action, FinalAnswerAction)
    assert action.answer == "Safe answer."


def test_invalid_action_raises() -> None:
    text = '{"action":"tool_call","args":{"query":"BM25"}}'
    with pytest.raises(Exception):
        parse_model_action(text)
