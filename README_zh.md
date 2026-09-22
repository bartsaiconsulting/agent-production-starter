# BartsAI Agent 生产级评估脚手架与确定性硬护栏 (Python / DeepEval Starter Kit)

[![CI](https://img.shields.io/badge/CI-Passing-emerald)](ci/agent-eval-ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![准入基准: BartsAI 50条生产清单](https://img.shields.io/badge/基准-BartsAI%2050条生产清单-purple)](https://www.bartsaiconsulting.com/zh/checklists/production-readiness/)

专为具备自主工具调用（Tool Calling）、代码执行与 API 编排能力的生产级 AI Agent 设计的开源评测与防御脚手架。

---

## 🎯 核心工程哲学

> **“提示词（Prompt）只是弱建议；生产级护栏必须是确定性的软件硬防线。”**

许多企业团队在发布 Agent 时误以为 System Prompt 写明 *“请严格遵守安全原则，严禁执行破坏性指令”* 就是安全防护。然而当 Agent 进入自主循环调用时，极易发生**内部安全崩溃 (Internal Safety Collapse, ISC)** —— 模型为了通过某个测试或解决中间报错，会自动篡改断言、读取敏感文件或陷入死循环重试。

本脚手架在工具真正调用之前，提供**纯代码层面的确定性硬拦截**，并结合 **CI/CD 流水线（DeepEval + Pytest）**，在代码合并前拦截任何存在越权风险的变更。

---

## 🛡️ 四层确定性工程防线

| 防御层级 | 核心模块 | 拦截威胁 | 控制机制 |
| :--- | :--- | :--- | :--- |
| **1. 递归步数与资源硬熔断** | `CircuitBreaker` | 无限递归、Token 费用失控、重复参数死循环 | 硬编码步数阈值、累计 Token/费用追踪、调用哈希比对 |
| **2. 工具最小权限分级** | `ToolGuard` | 越权调用未授权接口、间接提示词注入接管 | 严格工具白名单、读写权限隔离、破坏性操作二次人机确认 (2PC) |
| **3. 运行时沙箱目录约束** | `ToolGuard` | 路径遍历逃逸（`../../../../etc/passwd`） | 绝对路径解析校验，强制锚定在 Sandbox 根目录 |
| **4. 强类型与入参约束** | `SchemaValidator` | 无条件清空数据库、模糊参数幻觉、恶意字段注入 | JSON Schema 与 Pydantic 校验、强制 `WHERE` 条件非空 |

---

## 🚀 10 秒快速上手

### 1. 运行完整测试套件（零外部依赖）

本项目内置通用测试启动器，直接使用系统原生 Python 即可运行：

```bash
cd starters/agent-production-starter
python3 run_tests.py
```

终端输出示例：
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

### 2. 运行端到端拦截演示

```bash
PYTHONPATH=. python3 examples/guard_demo.py
```

查看在未授权工具调用、文件逃逸越权写入、无授权删除场景下，护栏是如何在代码层实施硬拦截的。

---

## 💻 如何接入你的 Agent 代码库

你可以无缝将本护栏嵌入 LangChain、CrewAI、AutoGen 或自定义 Tool Calling 循环中：

```python
from pathlib import Path
from bartsai_guard import ToolGuard, ToolPermissionLevel, CircuitBreaker

# 1. 初始化工具守卫
guard = ToolGuard(
    allowed_tools={"query_db", "write_file", "drop_table"},
    tool_permissions={
        "query_db": ToolPermissionLevel.READ_ONLY,
        "write_file": ToolPermissionLevel.MUTATIVE_WRITE,
        "drop_table": ToolPermissionLevel.DESTRUCTIVE,  # 必须具备人工确认凭据
    },
    sandbox_root=Path("./agent_workspace").resolve(),
    require_human_approval_for_destructive=True,
    valid_approval_tokens={"user_session_token_xyz"}
)

# 2. 配置熔断器
breaker = CircuitBreaker(
    max_steps=10,        # 单会话最大调用步数
    max_cost_usd=0.50,   # 最大单次预算
    max_consecutive_identical_calls=3  # 连续 3 次相同入参即判定为死循环
)

def safe_tool_executor(tool_name: str, arguments: dict, token: str = None):
    # A 步：步数与死循环熔断检查
    breaker.record_step(tool_name, arguments, step_tokens=400, step_cost_usd=0.005)

    # B 步：白名单授权与沙箱路径检查
    guard.inspect_and_authorize(tool_name, arguments, approval_token=token)

    # C 步：校验通过后才真正执行真实业务代码
    return actual_tool_implementation(tool_name, arguments)
```

---

## 🧪 CI/CD 自动化评测流水线

将 [`ci/agent-eval-ci.yml`](ci/agent-eval-ci.yml) 复制到你的仓库 `.github/workflows/agent-eval.yml` 中，即可在每次 PR 时自动触发安全与回归测试：

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

## 📚 延伸资源与独立准入审查

- **在线交互式 50 条生产就绪核验清单**：[BartsAI Production Readiness Checklist](https://www.bartsaiconsulting.com/zh/checklists/production-readiness/)
- **30 秒架构风险分诊器**：[BartsAI Risk Probe](https://www.bartsaiconsulting.com/zh/risk-probe/)
- **需要专家级独立生产发布审查 (Launch Gate Review)？** 欢迎访问 [bartsaiconsulting.com](https://www.bartsaiconsulting.com/zh/#contact) 联系 BartsAI 咨询团队。

---

## 📄 开源许可证

MIT License. 由 [BartsAI](https://www.bartsaiconsulting.com) 架构团队设计与维护。
