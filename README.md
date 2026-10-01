# BartsAI Agent Production Starter: Deterministic Guardrails & CI Evaluation

[![Starter guardrail tests](https://github.com/bartsaiconsulting/agent-production-starter/actions/workflows/guardrail-tests.yml/badge.svg?branch=main)](https://github.com/bartsaiconsulting/agent-production-starter/actions/workflows/guardrail-tests.yml)
[![Python target 3.10+](https://img.shields.io/badge/python-target%203.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Standards: BartsAI 50--Item Checklist](https://img.shields.io/badge/Standard-BartsAI%2050--Item%20Checklist-purple)](https://www.bartsaiconsulting.com/checklists/production-readiness/)

A local example of deterministic checks to adapt before using an AI agent with tools. Its tests exercise sample inputs, not your application's executor or production environment.

`pyproject.toml` targets Python 3.10 and newer. The [hosted CI matrix for published commit `024a53b`](https://github.com/bartsaiconsulting/agent-production-starter/actions/runs/36768742555) passed on Python 3.10, 3.11 and 3.12. Newer versions remain a compatibility target, not a tested claim. CI checks this example repository, not your application's executor.

---

## 🎯 The Core Engineering Philosophy

> **"Prompts are soft hints; production guardrails are hard, deterministic software boundaries."**

Enterprise teams frequently suffer catastrophic agent failures when relying on system prompts (e.g. *"Please do not delete data or execute unsafe commands"*) or input-only text classifiers. When an agent enters multi-turn tool loops, it can suffer **Internal Safety Collapse (ISC)** — over-optimizing to fulfill a sub-goal by deleting tests, traversing directories, or entering runaway recursive calls.

The example checks tool names, selected path arguments, schemas and budgets before calling a sample executor. Integrating it into a real application requires routing every tool call through the checks and testing the actual executor.

---

## 🛡️ Four-Layer Hard Engineering Defense

| Layer | Module | Threat Mitigated | Control Type |
| :--- | :--- | :--- | :--- |
| **1. Step & Resource Ceilings** | `CircuitBreaker` | Infinite recursion, runaway token burn, loop hallucination | Deterministic hard threshold & arg hashing |
| **2. Least-Privilege Tool Scoping** | `ToolGuard` | Unauthorized tool execution, prompt injection hijacking | Strict allowlist & permission tiering |
| **3. Recognized Path Arguments** | `ToolGuard` | Traversal in supported path fields | Resolve known path keys against a declared root; not OS isolation |
| **4. Structural Type Validation** | `SchemaValidator` | Wildcard database wipes, malformed parameter drift | JSON Schema & Pydantic strict typing |

---

## Quickstart

### 1. Run the dependency-free demonstration

This repository includes a standalone test runner that works with standard Python:

```bash
git clone https://github.com/bartsaiconsulting/agent-production-starter.git
cd agent-production-starter
git checkout v0.2.0
python3 --version
python3 run_tests.py --demo
```

Expected output:
```text
Demo: checking tool guards and fail-closed behavior with the Python standard library.
Skipped: JSON Schema evaluation, Pydantic validation, DeepEval record construction, and full pytest suite.
Ran 2 tests ... OK
Demo passed; see runner output for executed checks.
```

Strict `SchemaValidator.validate_json_schema()` calls require `jsonschema` even in demo mode. Missing dependencies cause an explicit error; they never switch to a weaker validator.

See [CHANGELOG.md](CHANGELOG.md) for migration notes and the supported release boundary.

### 2. Run the full local verification

```bash
python3 -m pip install -r requirements-core.txt
python3 run_tests.py --full
```

Missing mandatory packages cause a nonzero exit with an install hint. The full run exercises sample schema, path and budget tests. DeepEval record construction is optional and reported as skipped when absent; install `requirements.txt` only if you need that integration. Neither mode calls a paid model API or scores a DeepEval metric. Pytest reports passed, failed and skipped tests; a skipped check is not a pass.

### 3. Run the interception example

```bash
PYTHONPATH=. python3 examples/guard_demo.py
```

This example shows allowlist, recognized path-argument and approval-token checks. It does not execute a customer's tool or prove OS sandboxing.

`ToolGuard` checks `path`, `file_path`, `filepath`, `target_file`, `dest`, `destination` and `output_path` in nested dictionaries and lists. Relative paths resolve against `sandbox_root`. Your executor must use the same normalized target and enforce OS isolation, permissions and business authorization. Unknown fields, direct executor calls, shell/SQL behavior and symlink changes after validation remain outside this example's boundary.

### Upgrading from the earlier demo

The runner now requires an explicit `--demo` or `--full` mode. The demo is not a substitute for full schema tests: install `requirements-core.txt` and run `python3 run_tests.py --full` before relying on the sample validation checks. Direct JSON Schema calls without `jsonschema` now raise `SchemaValidationError` instead of accepting a partial check.

Review any tool adapter that passes nested path arguments or lists: recognized path fields that resolve outside `sandbox_root`, or have unsupported value types, now fail before dispatch. Add a regression case for each path shape your application uses. Do not treat a passing Starter test as proof that your executor uses the checked target; verify that integration separately.

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

    # Step B: Authorize tool & inspect recognized path arguments
    guard.inspect_and_authorize(tool_name, arguments, approval_token=token)

    # Step C: Your executor must use the validated target and enforce its own isolation
    return actual_tool_implementation(tool_name, arguments)
```

---

## 🧪 CI/CD Pipeline Integration

This repository runs [Starter guardrail tests](.github/workflows/guardrail-tests.yml) on its own branches and pull requests. [`ci/agent-eval-ci.yml`](ci/agent-eval-ci.yml) remains a copyable template, not evidence that your repository runs CI. It assumes this package, `requirements-core.txt` and `tests/` are present at repository root. Adapt those paths and permissions before adding it to your own `.github/workflows/` directory:

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
      - run: pip install -r requirements-core.txt
      - run: python run_tests.py --full
```

---

## 📚 Related Resources & Enterprise Launch Gates

- **Interactive 50-Item Production Checklist**: [BartsAI Production Readiness Checklist](https://www.bartsaiconsulting.com/checklists/production-readiness/)
- **30-Second Architecture Triage**: [BartsAI Risk Probe](https://www.bartsaiconsulting.com/risk-probe/)
- **Need an Independent Pre-Release Launch Gate Review?** Contact the BartsAI engineering team at [bartsaiconsulting.com](https://www.bartsaiconsulting.com/#contact).

---

## 📄 License

MIT License. Designed and maintained by [BartsAI](https://www.bartsaiconsulting.com).
