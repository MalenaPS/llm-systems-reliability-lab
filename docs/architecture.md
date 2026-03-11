# Architecture

This document describes the architecture of **LLM Systems Reliability
Lab** and how the repository evaluates an LLM pipeline as a **System
Under Test (SUT)**.

The project is designed to measure reliability properties of LLM-based
systems under controlled and reproducible conditions, including schema
compliance, tool robustness, adversarial resistance, and behavioral
drift.

---

## System Overview

At a high level, the repository separates the system into two layers:

**1. Evaluation Harness**

Responsible for:

-   loading benchmark cases
-   executing evaluation suites
-   injecting failures
-   collecting metrics
-   generating run artifacts

**2. System Under Test (SUT)**

The actual LLM application pipeline, including:

-   prompt construction
-   retrieval
-   tool execution
-   model inference
-   output validation

This separation is critical because the goal of the repository is **not
only to run an LLM pipeline, but to evaluate its reliability under
controlled conditions**.

---

## High-Level Flow

``` mermaid
flowchart LR

A[Benchmark Cases] --> B[Evaluation Runner]

B --> C[SUT Pipeline]

C --> D[Prompt Builder]
C --> E[Retriever]
C --> F[Tools]

F --> G[Tool Executor]

C --> H[LLM Backend]

H --> I[Output Validator]
F --> I
E --> I

I --> J[Metrics]
I --> K[Events Log]
I --> L[Run Manifest]
I --> M[Reports]
```

---

## Main Components

### Benchmark Cases

Benchmark cases define the tasks used to evaluate the pipeline.

Typical responsibilities:

-   specify the user query
-   define expected system behavior
-   support deterministic evaluation

These cases are loaded by the evaluation runner and executed against the
pipeline.

---

### Evaluation Runner

The evaluation runner orchestrates the experiment lifecycle.

Responsibilities:

-   load benchmark cases
-   run evaluation suites
-   inject failures (when configured)
-   collect reliability metrics
-   store execution artifacts

This layer transforms the project from a demo pipeline into a
**reliability evaluation framework**.

---

### SUT Pipeline

The **System Under Test (SUT)** represents the LLM application pipeline.

The SUT pipeline includes the core stages of an LLM application:

-   prompt construction
-   retrieval
-   tool invocation
-   LLM interaction
-   output generation

The implementation is organized inside:

src/llm_lab/

Key modules include:

pipeline/ tools/ retrieval/ llm/ drift/ redteam/ evals/

---

### Retriever

The retriever provides contextual information before generation.

This simulates a **RAG-style pipeline**, which reflects real production
LLM systems.

Retrieval affects:

-   grounding quality
-   answer stability
-   evidence usage

---

### Tool Layer

The tool layer simulates external operations that the LLM may call.

This is one of the main reliability surfaces in LLM systems.

Typical failure modes include:

-   transient failures
-   tool timeouts
-   malformed responses
-   retry policies

The evaluation framework explicitly measures system behavior under these
failures.

---

### LLM Backend

The system supports two execution modes.

#### Deterministic CI Mode

Uses a mock backend.

Characteristics:

-   deterministic responses
-   reproducible tests
-   CI stability

#### Local Real Execution Mode

Uses real model backends (e.g. Ollama).

Characteristics:

-   real model inference
-   real latency
-   behavioral drift observation

This design ensures CI stability while still allowing realistic
experimentation.

---

### Output Validator

The output validator enforces structural constraints.

Typical checks include:

-   JSON/schema validation
-   output structure
-   policy compliance
-   downstream compatibility

This reflects the **contract-first design** used throughout the
repository.

---

## Execution Flow

A typical execution proceeds through the following steps:

1. The evaluation runner loads a benchmark case.
2. The SUT pipeline builds the prompt and retrieves context.
3. Tool calls may be generated and executed through the tool layer.
4. The selected LLM backend generates a structured response.
5. The output validator checks schema compliance and policy constraints.
6. Reliability metrics are computed from the execution.
7. Execution events are appended to `events.jsonl`.
8. The run manifest is written to `run_manifest.json`.
9. Reports and metrics are stored in the run directory.

This flow ensures that every pipeline execution is observable and reproducible.

---

## Run Artifacts

Each execution generates structured artifacts.

Typical artifacts include:

- `output.json`
- `metrics.json`
- `events.jsonl`
- `run_manifest.json`

Additional reports may include:

-   reliability reports
-   drift reports
-   evaluation summaries

These artifacts support:

-   experiment reproducibility
-   debugging
-   regression detection
-   comparison between models

---

## Repository Mapping

The architecture directly maps to the repository structure.

src/
  llm_lab/
    pipeline/    pipeline orchestration
    tools/       tool schemas and execution
    retrieval/   contextual retrieval
    llm/         model backends
    evals/       evaluation logic
    redteam/     adversarial testing
    drift/       model drift analysis

configs/         pipeline configuration
data/            benchmark datasets
tests/           unit tests
docs/            technical documentation
runs/            generated artifacts

---

## Architectural Principles

The system follows several engineering principles:

### Contract-First Outputs

Outputs must follow machine-checkable schemas to guarantee structural validity and enable automated evaluation.

### Deterministic Evaluation

CI runs must produce reproducible results using a deterministic backend.

### Artifact-Based Observability

Each pipeline execution generates artifacts that allow debugging, auditing and experiment comparison.

### Failure-Aware Design

Failure modes such as tool errors and schema violations are explicitly simulated and measured.

### Pipeline/Evaluation Separation

The evaluation harness remains independent from the SUT pipeline to ensure unbiased reliability measurement.

---

## Why this Architecture Matters

Many LLM repositories demonstrate working pipelines.

This project addresses a different question:

**How reliable is the pipeline when it fails, is attacked, or the model
changes?**

The architecture therefore focuses on **evaluating reliability
properties of LLM systems**, not only building them.