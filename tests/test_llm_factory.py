from llm_lab.llm.factory import build_llm
from llm_lab.llm.mock import MockLLM
from llm_lab.llm.ollama import OllamaLLM


def test_build_llm_mock():
    llm = build_llm("mock", "mock-v1")
    assert isinstance(llm, MockLLM)


def test_build_llm_ollama():
    llm = build_llm("ollama", "qwen2.5:7b-instruct")
    assert isinstance(llm, OllamaLLM)
