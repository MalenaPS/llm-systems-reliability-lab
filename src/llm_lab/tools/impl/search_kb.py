from __future__ import annotations

from dataclasses import dataclass

from llm_lab.pipeline.contracts import EvidenceChunk
from llm_lab.retrieval.bm25 import BM25Index, build_default_kb_index


@dataclass
class SearchKBTool:
    """
    Minimal retrieval tool for controlled KB.
    """

    index: BM25Index

    @classmethod
    def default(cls) -> "SearchKBTool":
        return cls(index=build_default_kb_index())

    def __call__(self, query: str, top_k: int = 5) -> list[EvidenceChunk]:
        return self.index.search(query=query, top_k=top_k)