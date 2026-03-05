from llm_lab.llm.mock import MockLLM


def test_mock_llm_deterministic():
    llm = MockLLM()

    prompt = "hello world"

    r1 = llm.generate(prompt)
    r2 = llm.generate(prompt)

    assert r1 == r2