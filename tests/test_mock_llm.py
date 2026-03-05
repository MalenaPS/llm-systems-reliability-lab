import json

from llm_lab.llm.mock import MockLLM


def test_mock_llm_deterministic():
    llm = MockLLM()
    prompt = '{"task":"hello","evidence":[]}'
    r1 = llm.generate(prompt)
    r2 = llm.generate(prompt)
    assert r1 == r2


def test_mock_llm_sets_insufficient_evidence_when_no_evidence():
    llm = MockLLM()
    prompt = json.dumps({"task": "What is BM25?", "evidence": []})
    out = json.loads(llm.generate(prompt))
    assert out["insufficient_evidence"] is True


def test_mock_llm_clears_insufficient_evidence_when_evidence_present():
    llm = MockLLM()
    prompt = json.dumps(
        {
            "task": "What is BM25?",
            "evidence": [{"chunk_id": "kb.md:2", "source": "kb.md", "text": "BM25 is ..."}],
        }
    )
    out = json.loads(llm.generate(prompt))
    assert out["insufficient_evidence"] is False
    assert "BM25" in out["answer"]