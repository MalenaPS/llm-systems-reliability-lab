# LLM Systems Reliability Lab

![CI](https://github.com/MalenaPS/llm-systems-reliability-lab/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-Apache%202.0-blue)
![Python](https://img.shields.io/badge/python-3.11-blue)

Engineering reliable LLM systems: evaluation, adversarial testing,
behavioral drift monitoring and deterministic pipelines.

## Quick Demo

Run the deterministic pipeline:

``` bash
python -m llm_lab.cli demo --backend mock
```

Example output:

``` text
schema_compliance_rate: 1.0
tool_success_rate: 1.0
success_rate: 1.0
```

---

This repository provides a **reproducible testbed for evaluating
reliability and security of LLM-based pipelines**.\
It simulates a production LLM system (RAG + tools + policies) and
measures how it behaves under failures, attacks, and model changes.

The goal is to make **LLM reliability measurable and reproducible**.

---

# Why this matters

LLM systems fail in production for four main reasons:

* **Reliability failures** — tools fail, outputs break contracts.
* **Security vulnerabilities** — prompt injection or tool hijacking.
* **Model drift** — behavior changes across model updates.
* **Lack of reproducibility** — no deterministic artifacts or run manifests.

This project provides a **minimal open-source lab to test and measure these risks.**

---

# Features

* Contract-first LLM pipeline (JSON schema enforced)
* Tool calling with allowlist
* RAG retrieval (BM25)
* Fault injection for tools
* Retry / recovery policies
* Red-team adversarial testing
* Drift observatory across model versions
* Deterministic run manifests
* Structured artifacts and metrics
* Fully reproducible local setup

---

# Quickstart (deterministic mock backend)

Clone the repo:

```
git clone <repo-url>
cd llm-systems-reliability-lab
```

Install dependencies:

```
uv venv

# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

uv pip install -e ".[dev]"
```

Run the deterministic demo:

```
python -m llm_lab.cli demo --backend mock
```

Artifacts will appear in:

```
runs/<timestamp>/
```

Example artifacts:

```
runs/20260305-154606-4c7281d4/
  output.json
  metrics.json
  events.jsonl
  run_manifest.json
```

---

# Running evaluations

## Reliability suite

Simulates tool failures and measures recovery.

```
python -m llm_lab.cli eval --suite reliability \
  --fault-matrix configs/fault_matrix.yaml
```

Output:

```
runs/<id>/reliability_report.json
runs/<id>/metrics.json
```

Metrics include:

* tool_success_rate
* tool_retry_rate
* recovery_rate
* schema_compliance_rate

---

## Red team adversarial testing

Runs prompt-injection and tool-hijacking attacks.

```
python -m llm_lab.cli redteam --backend mock
```

Example result:

```
attack_success_rate: 0.0
```

The pipeline includes a leak-detection guardrail that blocks secrets such as:

```
LEAKED:
```

---

## Drift observatory

Compare model behavior across versions.

```
python -m llm_lab.cli drift \
  --matrix configs/drift_matrix.yaml
```

Produces:

```
drift_report.json
drift_report.md
```

Example metrics:

* drift_score
* answer_hash_stability_rate
* metric deltas

---

# Example output

Example `metrics.json`:

```
{
  "schema_compliance_rate": 1.0,
  "tool_success_rate": 1.0,
  "policy_violation_rate": 0.0,
  "insufficient_evidence_rate": 0.0,
  "success_rate": 1.0,
  "citations_valid_rate": 1.0
}
```

Example `drift_report.json`:

```
{
  "drift_score": 0.5,
  "answer_hash_stability_rate": 0.0
}
```

---

# Architecture

Pipeline components:

```
User Case
   |
Eval Runner
   |
SUT Pipeline
   |
+-------------------+
| Tool Router       |
| (JSON schema)     |
+---------+---------+
          |
     Fault Injection
          |
+---------+---------+
| Tools (mock)      |
+-------------------+
          |
+-------------------+
| Retriever (BM25)  |
+-------------------+
          |
+-------------------+
| LLM Adapter       |
| (Mock / Ollama)   |
+-------------------+
          |
+-------------------+
| Output Validator  |
| (schema + policy) |
+-------------------+
```

Artifacts:

```
runs/
   run_manifest.json
   metrics.json
   events.jsonl
   output.json
```

---

# Metrics

The system tracks:

| Metric                     | Description                           |
| -------------------------- | ------------------------------------- |
| schema_compliance_rate     | outputs matching schema               |
| tool_success_rate          | successful tool executions            |
| recovery_rate              | recovery from transient failures      |
| attack_success_rate        | red-team attacks that bypass defenses |
| drift_score                | metric delta across models            |
| answer_hash_stability_rate | behavioral stability                  |

---

# CI

GitHub Actions pipeline runs:

* ruff
* black
* pytest
* reliability smoke test

---

# Repository Structure

```
src/llm_lab
   pipeline/
   tools/
   retrieval/
   llm/
   drift/
   redteam/
   evals/

configs/
data/
tests/
runs/
```

---

# Roadmap

Future improvements:

* vector retrieval (FAISS)
* tool-call parsing from model outputs
* OpenTelemetry tracing
* model-based grading
* Streamlit dashboard

---

# License

Apache License 2.0

Copyright (c) 2026 Malena Pérez Sevilla

Licensed under the Apache License, Version 2.0.

You may obtain a copy of the License at:

http://www.apache.org/licenses/LICENSE-2.0
