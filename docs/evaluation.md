# Evaluation Methodology

This document describes how the reliability lab evaluates LLM systems.

---

## Evaluation datasets

Two datasets are used.

### cases.jsonl

Benchmark tasks.

Each case defines:

• input query  
• expected tool usage  
• expected schema  

---

### attacks.jsonl

Adversarial prompts used for red-team evaluation.

Examples:

• prompt injection  
• tool misuse  
• context manipulation

---

## Code-based grading

Deterministic evaluation checks:

• schema compliance  
• tool success  
• retry recovery  
• latency metrics

---

## Model-based grading

Optional LLM grading evaluates qualitative aspects.

Rubric dimensions:

• helpfulness  
• constraint adherence  
• evidence usage

---

## Drift evaluation

Drift compares model behaviour across runs.

Example metric:
drift_score = difference in reliability metrics between models

Low drift score indicates stable behaviour.