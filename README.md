# LLM Systems Reliability Lab

![CI](https://github.com/MalenaPS/llm-systems-reliability-lab/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-Apache%202.0-blue)
![Python](https://img.shields.io/badge/python-3.11-blue)

Engineering reliable LLM systems: evaluation, adversarial testing,
behavioral drift monitoring and deterministic pipelines.

------------------------------------------------------------------------

## Why this project exists

LLM systems often perform well in demos but fail in production
environments.

Typical failure modes include:

• tool calls that fail or return malformed outputs\
• outputs that break JSON contracts\
• prompt injection attacks and tool hijacking\
• behavioral drift between model versions\
• lack of reproducible execution artifacts

This repository provides a **reproducible laboratory for evaluating LLM
system reliability**.

It simulates a realistic LLM pipeline (RAG + tools + guardrails) and
measures how it behaves under:

• failures\
• adversarial attacks\
• model changes

The goal is to make **LLM reliability measurable, testable, and
reproducible**.

------------------------------------------------------------------------

## What this project provides

• Contract-first LLM pipelines (strict JSON schemas)\
• Tool-calling robustness evaluation\
• Fault injection for tool failures\
• Retry / recovery policies\
• Red-team adversarial prompt testing\
• Model behavior drift monitoring\
• Deterministic execution manifests\
• Structured run artifacts and metrics\
• Fully reproducible local experiments

------------------------------------------------------------------------

## Architecture Overview

The system evaluates an LLM pipeline as a **System Under Test (SUT)**.

## Architecture Overview

The system evaluates an LLM pipeline as a **System Under Test (SUT)**.

Benchmark Case  

      |  

      v  

Evaluation Runner  

      |  

      v  

SUT Pipeline  

(prompt + retrieval + 
tools)  

      |  

      v  

Output Validator  

(schema + policies)  

      |  

      v  

Run Artifacts  

(metrics, events, manifest)

------------------------------------------------------------------------

## Quickstart

Run the deterministic demo pipeline:

``` bash
python -m llm_lab.cli demo --backend mock
```

Example output:

    schema_compliance_rate: 1.0
    tool_success_rate: 1.0
    success_rate: 1.0

Artifacts will appear in:

    runs/<timestamp>/

Example artifacts:

    runs/<timestamp>/
      output.json
      metrics.json
      events.jsonl
      run_manifest.json

------------------------------------------------------------------------

## Running evaluations

### Reliability suite

Simulates tool failures and evaluates recovery behavior.

``` bash
python -m llm_lab.cli eval --suite reliability \
  --fault-matrix configs/fault_matrix.yaml
```

Metrics produced:

• tool_success_rate\
• tool_retry_rate\
• recovery_rate\
• schema_compliance_rate

Artifacts:

    reliability_report.json
    metrics.json

------------------------------------------------------------------------

### Red Team testing

Runs adversarial prompt injection attacks.

``` bash
python -m llm_lab.cli redteam --backend mock
```

Example result:

    attack_success_rate: 0.0

Security guardrails detect leaks such as:

    LEAKED:

------------------------------------------------------------------------

### Drift observatory

Compare behavior across model versions.

``` bash
python -m llm_lab.cli drift \
  --matrix configs/drift_matrix.yaml
```

Produces:

    drift_report.json
    drift_report.md

Example metrics:

• drift_score\
• answer_hash_stability_rate\
• metric deltas across models

------------------------------------------------------------------------

## Example Metrics

Example `metrics.json`:

``` json
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

``` json
{
  "drift_score": 0.5,
  "answer_hash_stability_rate": 0.0
}
```

------------------------------------------------------------------------

## Reliability Metrics

  Metric                       Description
  ---------------------------- ------------------------------------------
  schema_compliance_rate       \% outputs valid JSON
  tool_success_rate            successful tool executions
  recovery_rate                failures recovered via retry
  attack_success_rate          adversarial prompts that bypass defenses
  drift_score                  behavioral change between models
  answer_hash_stability_rate   behavioral stability

------------------------------------------------------------------------

## Deterministic CI Mode vs Local Real Execution

The project supports two execution modes.

### Mode A --- Deterministic CI Mode

Used for reproducible testing.

Backend:

    mock

Characteristics:

• deterministic outputs\
• fast execution\
• CI-compatible

Typical commands:

    python -m pytest
    python -m llm_lab.cli demo --backend mock
    python -m llm_lab.cli eval --suite reliability --backend mock

------------------------------------------------------------------------

### Mode B --- Local Real Mode

Used for real model experimentation.

Backend:

    ollama

Example:

    python -m llm_lab.cli demo --backend ollama --model qwen2.5:7b-instruct
    python -m llm_lab.cli drift --matrix configs/drift_matrix_local.yaml

Characteristics:

• real model inference\
• real latency\
• real drift observation

------------------------------------------------------------------------

## Design Principles

• Contract-first outputs\
• Deterministic execution\
• Observable pipelines\
• Failure-aware design\
• Reproducible evaluation

------------------------------------------------------------------------

## Repository Structure

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
    docs/

------------------------------------------------------------------------

## CI

GitHub Actions runs:

• ruff\
• black\
• pytest\
• reliability smoke tests

------------------------------------------------------------------------

## Roadmap

Future improvements:

• vector retrieval (FAISS)\
• tool-call parsing from model outputs\
• OpenTelemetry tracing\
• model-based grading\
• distributed evaluation\
• richer adversarial datasets

------------------------------------------------------------------------

# License

Apache License 2.0

Copyright (c) 2026 Malena Pérez Sevilla

Licensed under the Apache License, Version 2.0.

You may obtain a copy of the License at:

http://www.apache.org/licenses/LICENSE-2.0