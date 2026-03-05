from __future__ import annotations

from llm_lab.retrieval.bm25 import build_default_kb_index


def test_bm25_retrieval_finds_bm25_chunk() -> None:
    idx = build_default_kb_index()
    res = idx.search("What is BM25?", top_k=3)
    assert len(res) >= 1
    joined = "\n".join([c.text for c in res]).lower()
    assert "bm25" in joined


def test_bm25_retrieval_empty_query_returns_empty() -> None:
    idx = build_default_kb_index()
    res = idx.search("", top_k=3)
    assert res == []
