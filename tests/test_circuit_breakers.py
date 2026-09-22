"""
Tests for Circuit Breaker: Enforcing step ceilings, cost controls, and loop detection.
Ref: BartsAI Production Checklist §4 (Deterministic Circuit Breakers).
"""

try:
    import pytest
except ImportError:
    import contextlib
    class _PytestShim:
        @staticmethod
        def raises(expected_exception):
            @contextlib.contextmanager
            def _manager():
                class _ExcInfo:
                    value = None
                info = _ExcInfo()
                try:
                    yield info
                except expected_exception as e:
                    info.value = e
                else:
                    raise AssertionError(f"Expected exception {expected_exception.__name__} was not raised")
            return _manager()

        @staticmethod
        def skip(reason):
            pass
    pytest = _PytestShim()

from bartsai_guard import (
    CircuitBreaker,
    StepBudgetExceededError,
    CostBudgetExceededError,
    InfiniteLoopDetectedError,
)


def test_step_budget_exceeded():
    """Verify that an agent attempting more iterations than allowed is immediately halted."""
    cb = CircuitBreaker(max_steps=3)

    # Steps 1, 2, 3 should succeed
    cb.record_step("search_api", {"query": "attempt 1"})
    cb.record_step("search_api", {"query": "attempt 2"})
    cb.record_step("search_api", {"query": "attempt 3"})

    # Step 4 must breach the hard step ceiling
    with pytest.raises(StepBudgetExceededError) as exc_info:
        cb.record_step("search_api", {"query": "attempt 4"})

    assert "Execution step limit exceeded" in str(exc_info.value)
    assert "Halting agent" in str(exc_info.value)


def test_token_budget_exceeded():
    """Verify that an agent consuming tokens past the safety ceiling is stopped."""
    cb = CircuitBreaker(max_tokens=5000)

    cb.record_step("read_pdf", {"doc_id": "1"}, step_tokens=3000)

    with pytest.raises(CostBudgetExceededError) as exc_info:
        cb.record_step("read_pdf", {"doc_id": "2"}, step_tokens=2500)

    assert "Token budget exceeded" in str(exc_info.value)


def test_cost_budget_exceeded():
    """Verify that an agent spending more than the configured dollar limit is stopped."""
    cb = CircuitBreaker(max_cost_usd=0.20)

    cb.record_step("transcribe_audio", {"file": "clip1.wav"}, step_cost_usd=0.15)

    with pytest.raises(CostBudgetExceededError) as exc_info:
        cb.record_step("transcribe_audio", {"file": "clip2.wav"}, step_cost_usd=0.10)

    assert "Cost budget exceeded" in str(exc_info.value)


def test_infinite_loop_identical_tool_calls():
    """Verify that repeating the exact same tool payload triggers an infinite loop error."""
    cb = CircuitBreaker(max_consecutive_identical_calls=3)

    # First and second identical calls are allowed (e.g. valid single retry)
    cb.record_step("fetch_order", {"order_id": "12345"})
    cb.record_step("fetch_order", {"order_id": "12345"})

    # Third identical call trips the circuit breaker
    with pytest.raises(InfiniteLoopDetectedError) as exc_info:
        cb.record_step("fetch_order", {"order_id": "12345"})

    assert "Infinite loop detected" in str(exc_info.value)
    assert "identical parameters 3 times in a row" in str(exc_info.value)


def test_normal_execution_within_safety_bounds():
    """Verify that an agent operating within defined thresholds completes cleanly."""
    cb = CircuitBreaker(max_steps=5, max_tokens=10_000, max_cost_usd=0.50)

    cb.record_step("lookup_customer", {"id": 1}, step_tokens=500, step_cost_usd=0.01)
    cb.record_step("get_account_balance", {"account_id": "acc_9"}, step_tokens=300, step_cost_usd=0.005)
    cb.record_step("generate_summary", {"format": "bullet"}, step_tokens=1200, step_cost_usd=0.02)

    assert cb.current_step == 3
    assert cb.consumed_tokens == 2000
    assert abs(cb.accumulated_cost_usd - 0.035) < 1e-6


if __name__ == "__main__":
    test_step_budget_exceeded()
    test_token_budget_exceeded()
    test_cost_budget_exceeded()
    test_infinite_loop_identical_tool_calls()
    test_normal_execution_within_safety_bounds()
    print("All circuit breaker tests passed!")
