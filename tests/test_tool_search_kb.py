from __future__ import annotations

from llm_lab.tools.impl.search_kb import SearchKBTool


def test_search_kb_tool_returns_evidence_chunks() -> None:
    tool = SearchKBTool.default()
    chunks = tool("prompt injection", top_k=3)
    assert len(chunks) >= 1
    assert all(c.chunk_id and c.source and c.text for c in chunks)
