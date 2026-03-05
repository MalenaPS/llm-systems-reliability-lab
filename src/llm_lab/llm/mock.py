from __future__ import annotations

import hashlib
import json
from typing import Any

from llm_lab.llm.base import LLMAdapter


class MockLLM(LLMAdapter):
    """
    Deterministic mock LLM used for CI and local testing.
    Interprets our pipeline prompt JSON and decides insufficient_evidence based on evidence presence.
    """

    def generate(self, prompt: str) -> str:
        h = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]

        payload: dict[str, Any] = {}
        try:
            payload = json.loads(prompt)
        except Exception:
            payload = {}

        task = str(payload.get("task") or "").strip()
        evidence = payload.get("evidence") or []
        has_evidence = isinstance(evidence, list) and len(evidence) > 0

        # Deterministic rule: if no evidence -> insufficient_evidence=true
        insufficient = not has_evidence

        if insufficient:
            answer = "Cannot answer with available evidence."
        else:
            # Minimal, deterministic "helpful" answer based on task keywords
            t = task.lower()
            if "bm25" in t:
                answer = "BM25 is a ranking function used in information retrieval."
            elif "prompt injection" in t:
                answer = "Prompt injection is an attack that tries to override system rules with malicious instructions."
            else:
                answer = "Answer based on provided evidence."

        return json.dumps(
            {"answer": answer, "insufficient_evidence": insufficient, "mock_hash": h},
            ensure_ascii=False,
        )