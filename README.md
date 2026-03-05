# LLM Systems Reliability Lab

Engineering reliable LLM systems: evaluation, adversarial testing, behavioral drift monitoring and deterministic pipelines.

---

## Quickstart (Mock backend, deterministic)

```bash
uv venv --python 3.11

# activate your venv (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

uv pip install -e ".[dev]"

python -m llm_lab.cli demo --backend mock
```

## What you get

- Reproducible runs in `runs/<run_id>/`
- JSON Schema–validated outputs
- Fault injection + recovery policies (MVP)
- Red teaming suite (MVP)
- Drift observatory across backends/models (MVP)

---

## Project Configuration

### `pyproject.toml`

Create a file named `pyproject.toml`:

```toml
[project]
name = "llm-lab"
version = "0.1.0"
description = "LLM Systems Reliability Lab"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "typer>=0.12.0",
  "pydantic>=2.7.0",
  "jsonschema>=4.22.0",
  "structlog>=24.1.0",
  "httpx>=0.27.0",
  "pyyaml>=6.0.1",
  "rank-bm25>=0.2.2",
  "numpy>=1.26.0",
  "rich>=13.7.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2.0",
  "ruff>=0.5.0",
  "black>=24.4.0",
]

[project.scripts]
llm-lab = "llm_lab.cli:app"

[build-system]
requires = ["setuptools>=69"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.black]
line-length = 100
target-version = ["py311"]
```