#!/usr/bin/env python3
"""
BartsAI Agent Starter: Universal Test Runner.
Executes all safety & evaluation test suites with zero external setup.
"""

import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()

TEST_FILES = [
    "tests/test_circuit_breakers.py",
    "tests/test_schema_integrity.py",
    "tests/test_tool_calling_trajectory.py",
]


def run_all_tests():
    print("=" * 60)
    print("  BartsAI Production Evaluation & Hard Guardrails Test Suite")
    print("=" * 60)

    total_failed = 0

    for test_rel in TEST_FILES:
        test_path = BASE_DIR / test_rel
        print(f"\n▶ Running: {test_rel}...")
        proc = subprocess.run(
            [sys.executable, str(test_path)],
            cwd=str(BASE_DIR),
            env={"PYTHONPATH": str(BASE_DIR)},
            capture_output=True,
            text=True,
        )

        if proc.returncode == 0:
            print(f"  ✓ {proc.stdout.strip()}")
        else:
            print(f"  ❌ FAILED (exit code {proc.returncode})")
            if proc.stdout:
                print(proc.stdout)
            if proc.stderr:
                print(proc.stderr)
            total_failed += 1

    print("\n" + "=" * 60)
    if total_failed == 0:
        print("  ✅ All test suites passed successfully! 100% Green.")
        print("=" * 60)
        return 0
    else:
        print(f"  ❌ {total_failed} test suite(s) failed.")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
