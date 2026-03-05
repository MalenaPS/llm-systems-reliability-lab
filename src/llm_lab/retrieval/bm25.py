from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi

from llm_lab.pipeline.contracts import EvidenceChunk

_WORD_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


@dataclass
class BM25Index:
    chunks: list[EvidenceChunk]
    bm25: BM25Okapi
    tokenized: list[list[str]]

    @classmethod
    def from_markdown(cls, path: Path, source: str = "kb.md") -> "BM25Index":
        text = path.read_text(encoding="utf-8")
        # Very simple chunking: split by blank lines; keep only non-empty
        raw_chunks = [c.strip() for c in re.split(r"\n\s*\n", text) if c.strip()]
        chunks: list[EvidenceChunk] = []
        tokenized: list[list[str]] = []

        for i, c in enumerate(raw_chunks, start=1):
            chunk_id = f"{source}:{i}"
            chunks.append(EvidenceChunk(chunk_id=chunk_id, source=source, text=c))
            tokenized.append(_tokenize(c))

        bm25 = BM25Okapi(tokenized)
        return cls(chunks=chunks, bm25=bm25, tokenized=tokenized)

    def search(self, query: str, top_k: int = 5) -> list[EvidenceChunk]:
        q = _tokenize(query)
        if not q:
            return []
        scores = self.bm25.get_scores(q)
        # rank indices by score desc
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        results: list[EvidenceChunk] = []
        for i in ranked[: max(1, top_k)]:
            if scores[i] <= 0:
                continue
            results.append(self.chunks[i])
        return results


def build_default_kb_index() -> BM25Index:
    kb_path = Path("data") / "corpus" / "kb.md"
    return BM25Index.from_markdown(kb_path, source="kb.md")
