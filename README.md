# 🤖 AI/LLM Test Strategy — E-Commerce Product Recommendation Engine

[![Prompt Regression](https://img.shields.io/badge/prompt--regression-promptfoo-blueviolet?logo=openai)](https://promptfoo.dev)
[![Output Validation](https://img.shields.io/badge/output--validation-pydantic%20%2B%20pytest-green?logo=python)](https://docs.pydantic.dev)
[![Contract Testing](https://img.shields.io/badge/contract--testing-pact-orange)](https://docs.pact.io)
[![Performance](https://img.shields.io/badge/performance-k6-7D64FF)](https://k6.io)
[![Safety Gate](https://img.shields.io/badge/safety-perspective--api-red)](https://perspectiveapi.com)
[![CI](https://github.com/Djones-qa/ai-ecommerce-qa-strategy/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/Djones-qa/ai-ecommerce-qa-strategy/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue?logo=python)](https://www.python.org)

> A production-grade QA framework for testing AI-powered features — covering prompt regression, output schema validation, hallucination detection, toxicity safety gates, latency SLOs, and API contract testing. Built around an AI-powered e-commerce product recommendation engine to demonstrate every layer of the modern LLM testing stack.

---

## 📋 Table of Contents

- [Why This Matters](#-why-this-matters)
- [Architecture Overview](#-architecture-overview)
- [Test Layers](#-test-layers)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [Running Each Layer](#-running-each-layer)
- [CI Pipeline](#-ci-pipeline)
- [Author](#-author)
- [License](#-license)

---

## 🎯 Why This Matters

Testing AI features is fundamentally different from testing deterministic software. LLM responses are probabilistic — the same prompt can return different outputs on every call. This repo demonstrates how to build a **repeatable, automated quality gate** for non-deterministic systems.

| Problem | Solution |
|---|---|
| Prompt changes silently degrade quality | Prompt regression with PromptFoo |
| AI API returns unexpected shapes | Schema validation with Pydantic + pytest |
| Model hallucinates product data | Custom hallucination scorer |
| Responses contain harmful content | Perspective API toxicity gate in CI |
| AI endpoint too slow under load | k6 latency SLO tests |
| OpenAI-compatible API breaks contract | Pact consumer/provider contract tests |

---

## 🏗 Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│              AI Recommendation Engine (Mock)             │
│                                                         │
│  POST /v1/recommendations  ──►  LLM (OpenAI-compatible) │
│  GET  /v1/health                                        │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│                    QA Test Layers                        │
│                                                         │
│  1. Prompt Regression    (PromptFoo)                    │
│  2. Output Validation    (Pydantic + pytest)            │
│  3. Hallucination Detect (Custom Scorer)                │
│  4. Toxicity / Safety    (Perspective API)              │
│  5. Latency SLOs         (k6)                           │
│  6. Contract Testing     (Pact)                         │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│              GitHub Actions CI Gate                      │
│   Fails build if any layer drops below threshold        │
└─────────────────────────────────────────────────────────┘
```

---

## 🧪 Test Layers

### 1. Prompt Regression — PromptFoo
Detects when LLM response quality drifts between deploys. Runs a suite of test cases with assertions (contains, similarity, custom scorer) against the recommendation prompt. Fails CI if pass rate drops below 80%.

### 2. Output Validation — Pydantic + pytest
Validates that every AI API response conforms to the expected JSON schema. Catches type errors, missing fields, and out-of-range values before they reach production.

### 3. Hallucination Detection — Custom Scorer
A custom PromptFoo scorer that checks whether recommended products exist in the known product catalog. Flags responses that invent product IDs, names, or prices not present in the source data.

### 4. Toxicity / Safety — Perspective API
Pipes AI-generated recommendation text through Google's Perspective API. Fails CI if any response scores above the toxicity threshold (0.7). Acts as a content safety gate.

### 5. Latency SLOs — k6
Load tests the `/v1/recommendations` endpoint with realistic traffic patterns. Enforces:
- p95 response time < 2000ms
- p99 response time < 4000ms
- Error rate < 1%

### 6. Contract Testing — Pact
Consumer-driven contract tests verify the recommendation API stays OpenAI-compatible. The consumer (frontend) defines expected request/response shapes; the provider (AI service) verifies them independently.

---

## 📁 Project Structure

```
ai-ecommerce-qa-strategy/
├── .github/
│   └── workflows/
│       └── ci.yml                    # Full CI pipeline
├── mock_server/
│   ├── app.py                        # FastAPI mock recommendation server
│   └── requirements.txt
├── tests/
│   ├── output_validation/
│   │   ├── test_schema_validation.py # Pydantic schema tests
│   │   └── models.py                 # Pydantic response models
│   ├── hallucination/
│   │   ├── test_hallucination.py     # Hallucination detection tests
│   │   └── product_catalog.json      # Known product catalog
│   ├── toxicity/
│   │   └── test_toxicity.py          # Perspective API safety tests
│   └── contract/
│       ├── consumer_test.py          # Pact consumer contract test
│       └── provider_test.py          # Pact provider verification
├── prompt_regression/
│   ├── promptfooconfig.yaml          # PromptFoo eval config
│   ├── prompts/
│   │   └── recommendation.txt        # System + user prompt template
│   └── scorers/
│       └── hallucination_scorer.js   # Custom PromptFoo scorer
├── performance/
│   └── k6_load_test.js               # k6 SLO test script
├── pacts/                            # Generated Pact contract files
├── pytest.ini
├── requirements.txt
├── package.json
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- [k6](https://k6.io/docs/get-started/installation/) installed
- OpenAI API key (or any OpenAI-compatible endpoint)
- Perspective API key (optional — toxicity tests skip gracefully without it)

### Install

```bash
git clone https://github.com/Djones-qa/ai-ecommerce-qa-strategy.git
cd ai-ecommerce-qa-strategy

# Python dependencies
pip install -r requirements.txt

# Node dependencies (PromptFoo)
npm install
```

### Environment Variables

```bash
cp .env.example .env
# Fill in your keys:
# OPENAI_API_KEY=sk-...
# PERSPECTIVE_API_KEY=...
# OPENAI_BASE_URL=https://api.openai.com/v1  (or your mock server)
```

---

## 🏃 Running Each Layer

### Start the Mock Server

```bash
cd mock_server
uvicorn app:app --reload --port 8000
```

### 1. Prompt Regression

```bash
npx promptfoo eval --config prompt_regression/promptfooconfig.yaml
npx promptfoo eval --config prompt_regression/promptfooconfig.yaml --ci
```

### 2. Output Validation + Hallucination Detection

```bash
pytest tests/output_validation/ tests/hallucination/ -v
```

### 3. Toxicity / Safety

```bash
pytest tests/toxicity/ -v
```

### 4. Latency SLOs

```bash
# Start mock server first, then:
k6 run performance/k6_load_test.js
```

### 5. Contract Testing

```bash
# Generate consumer pact
pytest tests/contract/consumer_test.py -v

# Verify provider against pact
pytest tests/contract/provider_test.py -v
```

### Run All Python Tests

```bash
pytest --tb=short -v
```

---

## ⚙️ CI Pipeline

The GitHub Actions workflow runs all layers on every push and pull request:

```
push / PR
    │
    ├── install-deps
    ├── start-mock-server
    ├── prompt-regression      ← fails if pass rate < 80%
    ├── output-validation      ← fails on schema errors
    ├── hallucination-tests    ← fails if hallucination detected
    ├── toxicity-gate          ← fails if toxicity score > 0.7
    ├── contract-tests         ← fails on contract violations
    └── performance-slos       ← fails if p95 > 2000ms
```

All gates must pass for the build to be green.

---

## 👤 Author

**Darrius Jones**
QA Engineer | AI/LLM Testing Specialist

[![GitHub](https://img.shields.io/badge/GitHub-Djones--qa-181717?logo=github&style=for-the-badge)](https://github.com/Djones-qa)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Darrius%20Jones-0A66C2?logo=linkedin&style=for-the-badge)](https://www.linkedin.com/in/darrius-jones-28226b350/)

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](./LICENSE) for details.

---

## 🏷️ Topics

`ai-testing` `llm-testing` `prompt-regression` `promptfoo` `pydantic` `pytest` `hallucination-detection` `toxicity-detection` `perspective-api` `k6` `pact` `contract-testing` `github-actions` `qa-automation` `non-deterministic-testing` `ecommerce` `openai` `fastapi` `python` `portfolio`
