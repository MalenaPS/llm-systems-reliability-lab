.PHONY: setup lint test demo

setup:
	uv venv --python 3.11 || true
	uv pip install -e ".[dev]"

lint:
	ruff check .
	black --check .

test:
	pytest -q

demo:
	python -m llm_lab.cli demo --backend mock