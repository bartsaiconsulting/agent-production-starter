"""
End-to-End Example: Securing an Agent Tool Execution Loop with BartsAI Guard.
Demonstrates how hard deterministic boundaries intercept attacks before execution.
"""

from pathlib import Path
from bartsai_guard import (
    ToolGuard,
    ToolPermissionLevel,
    CircuitBreaker,
    SchemaValidator,
    ToolGuardError,
    CircuitBreakerTrippedError,
    SchemaValidationError,
)

# 1. Initialize Runtime Sandbox & Tool Guard
sandbox_dir = Path("./sandbox_workspace").resolve()
sandbox_dir.mkdir(exist_ok=True)

guard = ToolGuard(
    allowed_tools={"query_database", "write_local_report", "delete_record"},
    tool_permissions={
        "query_database": ToolPermissionLevel.READ_ONLY,
        "write_local_report": ToolPermissionLevel.MUTATIVE_WRITE,
        "delete_record": ToolPermissionLevel.DESTRUCTIVE,
    },
    sandbox_root=sandbox_dir,
    require_human_approval_for_destructive=True,
    valid_approval_tokens={"admin_session_token_123"},
)

breaker = CircuitBreaker(max_steps=5, max_cost_usd=0.20)


def execute_agent_tool(tool_name: str, arguments: dict, approval_token: str = None) -> str:
    """
    Standard production tool execution wrapper.
    Evaluates:
    1. Circuit breaker ceilings
    2. Tool permission & sandbox boundaries
    """
    print(f"\n[Agent Proposed Tool Call]: {tool_name}({arguments})")

    try:
        # Step A: Enforce step & cost limits
        breaker.record_step(tool_name, arguments, step_tokens=300, step_cost_usd=0.005)

        # Step B: Authorize tool & sandbox confinement
        guard.inspect_and_authorize(tool_name, arguments, approval_token=approval_token)

        # Step C: Mock execution
        return f"SUCCESS: Executed {tool_name} with safe boundaries."

    except (CircuitBreakerTrippedError, ToolGuardError, SchemaValidationError) as e:
        return f"BLOCKED by BartsAI Guard: {e}"


if __name__ == "__main__":
    print("=== BartsAI Agent Guardrails Demo ===")

    # Scenario 1: Safe read operation
    res1 = execute_agent_tool("query_database", {"sql": "SELECT id, name FROM users LIMIT 10;"})
    print(f"Result: {res1}")

    # Scenario 2: Attack - Prompt injection asks agent to execute unapproved shell
    res2 = execute_agent_tool("execute_bash", {"command": "cat /etc/passwd"})
    print(f"Result: {res2}")

    # Scenario 3: Attack - Path traversal escaping the sandbox
    res3 = execute_agent_tool("write_local_report", {"path": "../../../etc/crontab", "content": "* * * * * root"})
    print(f"Result: {res3}")

    # Scenario 4: Attack - Destructive action without 2PC human approval token
    res4 = execute_agent_tool("delete_record", {"id": 1001})
    print(f"Result: {res4}")

    # Scenario 5: Authorized destructive action with valid 2PC human token
    res5 = execute_agent_tool("delete_record", {"id": 1001}, approval_token="admin_session_token_123")
    print(f"Result: {res5}")
