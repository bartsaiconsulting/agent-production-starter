"""
Pytest configuration and shared test fixtures for BartsAI Agent Starter.
"""

import tempfile
import shutil
from pathlib import Path
import pytest
from bartsai_guard import ToolGuard, ToolPermissionLevel, CircuitBreaker


@pytest.fixture
def temp_sandbox_dir():
    """Provides an isolated temporary directory simulating an agent runtime sandbox."""
    tmp = tempfile.mkdtemp(prefix="bartsai_sandbox_")
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def production_tool_guard(temp_sandbox_dir):
    """
    Standard production tool guard configuration:
    - Only read-only and specific business write tools allowed.
    - Destructive tools require explicit approval tokens.
    """
    allowed_tools = {
        "read_documentation",
        "query_customer_profile",
        "draft_email_response",
        "delete_customer_record",  # Destructive, requires 2PC token
    }

    tool_permissions = {
        "read_documentation": ToolPermissionLevel.READ_ONLY,
        "query_customer_profile": ToolPermissionLevel.READ_ONLY,
        "draft_email_response": ToolPermissionLevel.MUTATIVE_WRITE,
        "delete_customer_record": ToolPermissionLevel.DESTRUCTIVE,
    }

    valid_tokens = {"valid_2pc_human_token_xyz"}

    return ToolGuard(
        allowed_tools=allowed_tools,
        tool_permissions=tool_permissions,
        sandbox_root=temp_sandbox_dir,
        require_human_approval_for_destructive=True,
        valid_approval_tokens=valid_tokens,
    )


@pytest.fixture
def default_circuit_breaker():
    """Standard circuit breaker with 5-step limit for fast test execution."""
    return CircuitBreaker(
        max_steps=5,
        max_tokens=10_000,
        max_cost_usd=0.10,
        max_consecutive_identical_calls=3,
    )
