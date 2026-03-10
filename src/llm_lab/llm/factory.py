from __future__ import annotations

from llm_lab.llm.base import LLMAdapter
from llm_lab.llm.mock import MockLLM
from llm_lab.llm.ollama import OllamaLLM


def build_llm(backend: str, model: str) -> LLMAdapter:
    if backend == "mock":
        return MockLLM(model=model)

    if backend == "ollama":
        return OllamaLLM(model=model)

    raise ValueError(f"Unsupported backend: {backend}")
