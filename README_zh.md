# BartsAI Agent 工具调用校验示例 (Python Starter Kit)

[![CI 模板](https://img.shields.io/badge/CI-template-blue)](ci/agent-eval-ci.yml)
[![Python 目标 3.10+](https://img.shields.io/badge/python-target%203.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![准入基准: BartsAI 50条生产清单](https://img.shields.io/badge/基准-BartsAI%2050条生产清单-purple)](https://www.bartsaiconsulting.com/zh/checklists/production-readiness/)

面向具备工具调用能力的 AI Agent 的开源本地校验示例；真实执行器仍需独立授权和隔离。

`pyproject.toml` 的目标兼容范围为 Python 3.10 及以上。目前仅在 Python 3.12 本地运行了演示与完整测试；3.10/3.11 尚无托管矩阵验证。版本范围是兼容目标，不代表 CI 已通过。

---

## 🎯 核心工程哲学

> **“提示词（Prompt）只是弱建议；生产级护栏必须是确定性的软件硬防线。”**

许多企业团队在发布 Agent 时误以为 System Prompt 写明 *“请严格遵守安全原则，严禁执行破坏性指令”* 就是安全防护。然而当 Agent 进入自主循环调用时，极易发生**内部安全崩溃 (Internal Safety Collapse, ISC)** —— 模型为了通过某个测试或解决中间报错，会自动篡改断言、读取敏感文件或陷入死循环重试。

本脚手架提供工具名称、已知路径参数、Schema 和预算的示例校验。接入真实系统时，必须让每次工具调用经过校验，并对实际执行器单独测试。

---

## 🛡️ 四层确定性工程防线

| 防御层级 | 核心模块 | 拦截威胁 | 控制机制 |
| :--- | :--- | :--- | :--- |
| **1. 递归步数与资源硬熔断** | `CircuitBreaker` | 无限递归、Token 费用失控、重复参数死循环 | 硬编码步数阈值、累计 Token/费用追踪、调用哈希比对 |
| **2. 工具最小权限分级** | `ToolGuard` | 越权调用未授权接口、间接提示词注入接管 | 严格工具白名单、读写权限隔离、破坏性操作二次人机确认 (2PC) |
| **3. 已知路径参数校验** | `ToolGuard` | 已支持字段中的路径遍历 | 按声明的根目录解析路径；不提供操作系统隔离 |
| **4. 强类型与入参约束** | `SchemaValidator` | 无条件清空数据库、模糊参数幻觉、恶意字段注入 | JSON Schema 与 Pydantic 校验、强制 `WHERE` 条件非空 |

---

## 快速上手

### 1. 运行零依赖演示

本项目内置通用测试启动器，直接使用系统原生 Python 即可运行：

```bash
git clone https://github.com/bartsaiconsulting/agent-production-starter.git
cd agent-production-starter
python3 --version
python3 run_tests.py --demo
```

终端输出示例：
```text
Demo: checking tool guards and fail-closed behavior with the Python standard library.
Skipped: JSON Schema evaluation, Pydantic validation, DeepEval record construction, and full pytest suite.
Ran 2 tests ... OK
Demo passed; see runner output for executed checks.
```

演示模式不运行完整 Schema 校验；直接调用 `SchemaValidator.validate_json_schema()` 时若缺少 `jsonschema`，会明确报错，不会自动降级。

### 2. 运行完整本地验证

```bash
python3 -m pip install -r requirements-core.txt
python3 run_tests.py --full
```

缺少必需依赖时以非零状态退出并提示安装。完整模式运行 Schema、路径与预算示例测试；DeepEval 记录构造是可选集成，未安装时明确标记跳过，需要时另装 `requirements.txt`。两种模式都不调用付费模型指标。pytest 输出区分通过、失败和跳过，跳过不等于通过。

### 3. 运行工具拦截示例

```bash
PYTHONPATH=. python3 examples/guard_demo.py
```

示例展示工具白名单、已知路径参数和审批令牌校验，不执行客户工具，也不证明操作系统级隔离。

`ToolGuard` 递归检查字典/列表中的 `path`、`file_path`、`filepath`、`target_file`、`dest`、`destination` 与 `output_path`。相对路径按 `sandbox_root` 解析。真实执行器须使用同一规范化目标并负责 OS 隔离、文件权限和业务授权。未知字段、绕过守卫的调用、Shell/SQL 行为以及校验后的符号链接变化不在示例覆盖范围内。

### 从旧版演示迁移

测试入口现在必须显式指定 `--demo` 或 `--full`。演示模式不能替代完整 Schema 测试；依赖校验能力前，请安装 `requirements-core.txt` 并运行 `python3 run_tests.py --full`。未安装 `jsonschema` 时直接进行 JSON Schema 校验会抛出 `SchemaValidationError`，不再以局部检查代替。

请检查传入嵌套路径或列表的工具适配器：已知路径字段若解析到 `sandbox_root` 外，或使用不支持的值类型，现在会在分发前被拒绝。针对业务中实际使用的每种路径形态添加回归用例。Starter 自身测试通过不代表真实执行器使用了被校验的目标，应单独验证集成。

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

    # B 步：白名单授权与已知路径参数检查
    guard.inspect_and_authorize(tool_name, arguments, approval_token=token)

    # C 步：真实执行器还需使用已校验目标并实施隔离
    return actual_tool_implementation(tool_name, arguments)
```

---

## 🧪 CI/CD 自动化评测流水线

[`ci/agent-eval-ci.yml`](ci/agent-eval-ci.yml) 是模板，不代表托管 CI 已运行。它假定脚手架、`requirements-core.txt` 与 `tests/` 位于仓库根目录；移入自己的 `.github/workflows/` 前需调整路径与权限：

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

## 📚 延伸资源与独立准入审查

- **在线交互式 50 条生产就绪核验清单**：[BartsAI Production Readiness Checklist](https://www.bartsaiconsulting.com/zh/checklists/production-readiness/)
- **30 秒架构风险分诊器**：[BartsAI Risk Probe](https://www.bartsaiconsulting.com/zh/risk-probe/)
- **需要专家级独立生产发布审查 (Launch Gate Review)？** 欢迎访问 [bartsaiconsulting.com](https://www.bartsaiconsulting.com/zh/#contact) 联系 BartsAI 咨询团队。

---

## 📄 开源许可证

MIT License. 由 [BartsAI](https://www.bartsaiconsulting.com) 架构团队设计与维护。
