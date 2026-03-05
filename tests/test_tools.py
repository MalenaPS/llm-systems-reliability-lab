from llm_lab.pipeline.contracts import ToolCall
from llm_lab.tools.registry import default_registry


def test_tool_router_executes_search():
    registry = default_registry()

    call = ToolCall(name="search_kb", args={"query": "bm25"})
    result = registry.execute(call)

    assert result.ok is True
    assert "data" in result.result
    assert isinstance(result.result["data"], list)
    assert len(result.result["data"]) >= 1
    assert all(isinstance(x, dict) for x in result.result["data"])


def test_tool_router_rejects_unknown_tool():
    registry = default_registry()
    call = ToolCall(name="hack_tool", args={})
    result = registry.execute(call)
    assert result.ok is False
    assert result.error == "tool_not_allowed"


def test_tool_router_validates_schema():
    registry = default_registry()
    call = ToolCall(name="search_kb", args={"wrong": "field"})
    result = registry.execute(call)
    assert result.ok is False
    assert "invalid_args" in result.error
