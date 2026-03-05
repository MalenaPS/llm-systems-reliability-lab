from __future__ import annotations

import os

import httpx
import pytest

from llm_lab.llm.ollama import OllamaLLM


def _ollama_reachable() -> bool:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    try:
        r = httpx.get(f"{base_url}/api/tags", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


@pytest.mark.skipif(
    not _ollama_reachable(), reason="Ollama server not reachable on localhost:11434"
)
def test_ollama_generate_smoke() -> None:
    llm = OllamaLLM(model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct"))
    out = llm.generate("Say 'ok' only.")
    assert isinstance(out, str)
    assert len(out) > 0
