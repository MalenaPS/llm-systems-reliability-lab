from pathlib import Path

from llm_lab.llm.mock import MockLLM
from llm_lab.llm.ollama import OllamaLLM
from llm_lab.pipeline.sut import PipelineConfig, SUTPipeline


def test_pipeline_uses_mock_backend(tmp_path: Path) -> None:
    pipe = SUTPipeline(cfg=PipelineConfig(backend="mock", model="mock-v1", runs_dir=tmp_path))
    assert isinstance(pipe.llm, MockLLM)


def test_pipeline_uses_ollama_backend(tmp_path: Path) -> None:
    pipe = SUTPipeline(
        cfg=PipelineConfig(
            backend="ollama",
            model="qwen2.5:7b-instruct",
            runs_dir=tmp_path,
        )
    )
    assert isinstance(pipe.llm, OllamaLLM)
