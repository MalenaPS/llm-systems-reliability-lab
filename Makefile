PYTHON ?= python

.PHONY: setup lint format test smoke demo eval redteam drift

setup:
	$(PYTHON) -m pip install -e .[dev]

lint:
	ruff check .

format:
	black .
	ruff check . --fix

test:
	$(PYTHON) -m pytest -q

smoke:
	$(PYTHON) -m llm_lab.cli demo --backend mock --model mock-v1 --case-id tool_success_01

demo:
	$(PYTHON) -m llm_lab.cli demo --backend mock --model mock-v1 --case-id tool_success_01

eval:
	$(PYTHON) -m llm_lab.cli eval --suite full --backend mock --model mock-v1

redteam:
	$(PYTHON) -m llm_lab.cli redteam --backend mock --model mock-v1

drift:
	$(PYTHON) -m llm_lab.cli drift --matrix configs/drift_matrix.yaml