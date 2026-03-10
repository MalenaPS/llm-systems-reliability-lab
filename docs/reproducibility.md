# Reproducibility

Reproducibility is a core design goal of **LLM Systems Reliability Lab**.

Every evaluation run generates structured artifacts that describe the full execution context. This allows experiments to be inspected, reproduced, and compared across runs, models, and configurations.

Reproducibility enables:

- experiment tracking
- deterministic testing in CI
- debugging historical runs
- comparison across models
- regression detection

---

# Reproducible Execution

Each run generates a **run manifest** that captures the execution environment.

File:

```
run_manifest.json
```

Example:

```json
{
  "run_id": "20260310-123456",
  "model": "qwen2.5:7b-instruct",
  "backend": "ollama",
  "config_hash": "abc123",
  "prompt_hash": "def456",
  "retrieval_docs": ["doc_1", "doc_2"],
  "metrics": {
    "schema_compliance_rate": 1.0,
    "tool_success_rate": 1.0,
    "success_rate": 1.0
  }
}
```

This manifest ensures that the **exact execution context** of a run can be reconstructed.

---

# Deterministic CI Mode

Continuous integration runs the pipeline in **deterministic mode** using a mock backend.

Characteristics:

- deterministic responses
- stable metrics across runs
- fast execution

Typical commands executed in CI:

```bash
python -m pytest
python -m llm_lab.cli demo --backend mock
python -m llm_lab.cli eval --suite reliability --backend mock
```

Deterministic mode ensures that automated tests remain stable and reproducible.

---

# Local Experimentation Mode

Local runs may use real model backends.

Example:

```bash
python -m llm_lab.cli demo --backend ollama --model qwen2.5:7b-instruct
```

Local execution allows:

- real model behaviour analysis
- latency measurement
- drift evaluation across model versions

However, real-model runs may produce **non-deterministic outputs**, which is expected.

---

# Run Artifacts

Each run produces a structured directory containing all artifacts.

Typical structure:

```
runs/<timestamp>/
  output.json
  metrics.json
  events.jsonl
  run_manifest.json
```

Additional evaluation runs may generate:

```
reliability_report.json
drift_report.json
llm_grades.json
```

These artifacts enable full inspection of the pipeline execution.

---

# Configuration Traceability

The manifest records hashes for configuration and prompt inputs.

Key tracked elements:

| Field | Purpose |
|------|------|
| config_hash | identifies evaluation configuration |
| prompt_hash | identifies prompt template |
| model | identifies model version |
| backend | identifies inference backend |

This prevents ambiguity when comparing experiments.

---

# Dataset Reproducibility

Evaluation runs reference deterministic datasets.

Typical datasets include:

```
cases.jsonl
attacks.jsonl
```

Because datasets are version-controlled, the same evaluation can be reproduced across environments.

---

# Debugging Historical Runs

Run artifacts allow engineers to reconstruct the full execution flow.

For example:

- inspect tool calls in `events.jsonl`
- verify schema compliance in `metrics.json`
- reconstruct execution context from `run_manifest.json`

This capability is critical for diagnosing reliability failures.

---

# Reproducibility Principles

The repository follows several principles to maintain reproducibility:

**Deterministic CI evaluation**

CI runs use mock backends to guarantee stable results.

**Artifact-based experiment tracking**

Every run produces structured artifacts.

**Version-controlled datasets and configs**

Evaluation inputs are stored in the repository.

**Explicit execution manifests**

All important execution parameters are recorded.

---

# Why Reproducibility Matters

LLM systems are inherently probabilistic.

Without careful experiment tracking it becomes difficult to:

- reproduce results
- diagnose regressions
- compare model versions

This repository addresses this by treating **every run as a reproducible experiment**, ensuring that reliability results can always be inspected and replicated.