"""
Circuit Breaker Module: Deterministic Step & Resource Limits.
Enforces hard ceilings on tool recursion depth, token burn, and loop detection.
"""

from typing import Any, Dict, List, Optional
import hashlib
import json


class CircuitBreakerTrippedError(Exception):
    """Base exception when any execution safety boundary is breached."""
    pass


class StepBudgetExceededError(CircuitBreakerTrippedError):
    """Tripped when an agent exceeds the maximum allowed execution steps."""
    pass


class CostBudgetExceededError(CircuitBreakerTrippedError):
    """Tripped when an agent exceeds cumulative token or cost budgets."""
    pass


class InfiniteLoopDetectedError(CircuitBreakerTrippedError):
    """Tripped when repetitive identical tool calls indicate an unrecoverable hallucination loop."""
    pass


class CircuitBreaker:
    """
    Deterministic Circuit Breaker for Agent loops.
    Must be invoked before every tool execution step.
    """

    def __init__(
        self,
        max_steps: int = 10,
        max_tokens: int = 50_000,
        max_cost_usd: float = 0.50,
        max_consecutive_identical_calls: int = 3,
    ) -> None:
        self.max_steps = max_steps
        self.max_tokens = max_tokens
        self.max_cost_usd = max_cost_usd
        self.max_consecutive_identical_calls = max_consecutive_identical_calls

        self.current_step = 0
        self.consumed_tokens = 0
        self.accumulated_cost_usd = 0.0
        self._history: List[Dict[str, Any]] = []
        self._last_call_hash: Optional[str] = None
        self._consecutive_identical_count = 0

    def record_step(
        self,
        tool_name: str,
        tool_arguments: Dict[str, Any],
        step_tokens: int = 0,
        step_cost_usd: float = 0.0,
    ) -> None:
        """
        Record a step before executing the tool.
        Raises an exception if any safety boundary is tripped.
        """
        self.current_step += 1
        self.consumed_tokens += step_tokens
        self.accumulated_cost_usd += step_cost_usd

        # 1. Hard Step Ceiling
        if self.current_step > self.max_steps:
            raise StepBudgetExceededError(
                f"Execution step limit exceeded: {self.current_step} > {self.max_steps}. "
                f"Halting agent to prevent runaway loops."
            )

        # 2. Token Budget Ceiling
        if self.consumed_tokens > self.max_tokens:
            raise CostBudgetExceededError(
                f"Token budget exceeded: {self.consumed_tokens} > {self.max_tokens}."
            )

        # 3. Cost Budget Ceiling
        if self.accumulated_cost_usd > self.max_cost_usd:
            raise CostBudgetExceededError(
                f"Cost budget exceeded: ${self.accumulated_cost_usd:.4f} > ${self.max_cost_usd:.2f}."
            )

        # 4. Loop Detection: hash of tool_name + sorted arguments
        arg_str = json.dumps(tool_arguments, sort_keys=True, default=str)
        call_hash = hashlib.sha256(f"{tool_name}:{arg_str}".encode()).hexdigest()

        if call_hash == self._last_call_hash:
            self._consecutive_identical_count += 1
        else:
            self._last_call_hash = call_hash
            self._consecutive_identical_count = 1

        if self._consecutive_identical_count >= self.max_consecutive_identical_calls:
            raise InfiniteLoopDetectedError(
                f"Infinite loop detected: Agent invoked tool '{tool_name}' with identical "
                f"parameters {self._consecutive_identical_count} times in a row."
            )

        self._history.append({
            "step": self.current_step,
            "tool": tool_name,
            "tokens": self.consumed_tokens,
            "cost": self.accumulated_cost_usd,
        })

    def reset(self) -> None:
        """Reset internal metrics for a new session."""
        self.current_step = 0
        self.consumed_tokens = 0
        self.accumulated_cost_usd = 0.0
        self._history.clear()
        self._last_call_hash = None
        self._consecutive_identical_count = 0
