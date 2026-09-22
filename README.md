# BartsAI Agent Production Starter: Deterministic Guardrails & CI Evaluation

[![CI](https://img.shields.io/badge/CI-Passing-emerald)](ci/agent-eval-ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Standards: BartsAI 50--Item Checklist](https://img.shields.io/badge/Standard-BartsAI%2050--Item%20Checklist-purple)](https://www.bartsaiconsulting.com/checklists/production-readiness/)

A production-grade, reproducible evaluation and hard guardrails starter kit for autonomous AI agents with tool-calling capabilities.

---

## 🎯 The Core Engineering Philosophy

> **"Prompts are soft hints; production guardrails are hard, deterministic software boundaries."**

Enterprise teams frequently suffer catastrophic agent failures when relying on system prompts (e.g. *"Please do not delete data or execute unsafe commands"*) or input-only text classifiers. When an agent enters multi-turn tool loops, it can suffer **Internal Safety Collapse (ISC)** — over-optimizing to fulfill a sub-goal by deleting tests, traversing directories, or entering runaway recursive calls.

This starter kit enforces **deterministic hard controls in code** before tools execute, combined with **CI evaluation gates** (using DeepEval and pytest) to block unsafe pull requests before deployment.

---

## 🛡️ Four-Layer Hard Engineering Defense

| Layer | Module | Threat Mitigated | Control Type |
| :--- | :--- | :--- | :--- |
| **1. Step & Resource Ceilings** | `CircuitBreaker` | Infinite recursion, runaway token burn, loop hallucination | Deterministic hard threshold & arg hashing |
| **2. Least-Privilege Tool Scoping** | `ToolGuard` | Unauthorized tool execution, prompt injection hijacking | Strict allowlist & permission tiering |
| **3. Sandbox Confinement** | `ToolGuard` | Host directory escape, `/etc/passwd` or `.env` leaks | Path resolution & sandbox root anchoring |
| **4. Structural Type Validation** | `SchemaValidator` | Wildcard database wipes, malformed parameter drift | JSON Schema & Pydantic strict typing |

---

## 🚀 10-Second Quickstart

### 1. Run the test suite immediately (Zero external setup)

This repository includes a standalone test runner that works with standard Python:

```bash
cd starters/agent-production-starter
python3 run_tests.py
```

Expected output:
```text
============================================================
  BartsAI Production Evaluation & Hard Guardrails Test Suite
============================================================

▶ Running: tests/test_circuit_breakers.py...
  ✓ All circuit breaker tests passed!

▶ Running: tests/test_schema_integrity.py...
  ✓ All schema integrity tests passed!

▶ Running: tests/test_tool_calling_trajectory.py...
  ✓ All tool calling trajectory tests passed!

============================================================
  ✅ All test suites passed successfully! 100% Green.
============================================================
```

### 2. Run the End-to-End Interception Demo

```bash
PYTHONPATH=. python3 examples/guard_demo.py
```

Watch how `BartsAIGuard` intercepts injection attempts, path traversal, and unapproved destructive actions in real time.

---

## 💻 How to Wrap Your Agent Loop (Code Snippet)

Integrate into any Python agent (LangChain, CrewAI, AutoGen, LlamaIndex, or raw tool-calling loops):

```python
from pathlib import Path
from bartsai_guard import ToolGuard, ToolPermissionLevel, CircuitBreaker

# 1. Configure the Tool Guard
guard = ToolGuard(
    allowed_tools={"query_db", "write_file", "drop_table"},
    tool_permissions={
        "query_db": ToolPermissionLevel.READ_ONLY,
        "write_file": ToolPermissionLevel.MUTATIVE_WRITE,
        "drop_table": ToolPermissionLevel.DESTRUCTIVE,  # Requires human token!
    },
    sandbox_root=Path("./agent_workspace").resolve(),
    require_human_approval_for_destructive=True,
    valid_approval_tokens={"user_session_token_xyz"}
)

# 2. Configure the Circuit Breaker
breaker = CircuitBreaker(
    max_steps=10,        # Max tool calls per session
    max_cost_usd=0.50,   # Max cost budget
    max_consecutive_identical_calls=3  # Anti-loop breaker
)

def safe_tool_executor(tool_name: str, arguments: dict, token: str = None):
    # Step A: Enforce step limits and detect infinite loops
    breaker.record_step(tool_name, arguments, step_tokens=400, step_cost_usd=0.005)

    # Step B: Authorize tool & verify filesystem sandbox boundaries
    guard.inspect_and_authorize(tool_name, arguments, approval_token=token)

    # Step C: Physically execute tool only if all checks pass
    return actual_tool_implementation(tool_name, arguments)
```

---

## 🧪 CI/CD Pipeline Integration

Copy [`ci/agent-eval-ci.yml`](ci/agent-eval-ci.yml) directly into your repository's `.github/workflows/agent-eval.yml`:

```yaml
name: Agent Production Guardrails & Eval Gate
on: [push, pull_request]

jobs:
  guardrail-eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: python -m pytest tests/ -v
```

---

## 📚 Related Resources & Enterprise Launch Gates

- **Interactive 50-Item Production Checklist**: [BartsAI Production Readiness Checklist](https://www.bartsaiconsulting.com/checklists/production-readiness/)
- **30-Second Architecture Triage**: [BartsAI Risk Probe](https://www.bartsaiconsulting.com/risk-probe/)
- **Need an Independent Pre-Release Launch Gate Review?** Contact the BartsAI engineering team at [bartsaiconsulting.com](https://www.bartsaiconsulting.com/#contact).

---

## 📄 License

MIT License. Designed and maintained by [BartsAI](https://www.bartsaiconsulting.com).
