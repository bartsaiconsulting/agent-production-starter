#!/usr/bin/env python3
"""Run dependency-free control checks or the full local Starter verification."""

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
FULL_DEPENDENCIES = ("pytest", "jsonschema", "pydantic")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--demo", action="store_true", help="Run standard-library checks only")
    mode.add_argument("--full", action="store_true", help="Require dependencies and run every test")
    args = parser.parse_args()

    if args.full:
        missing = [name for name in FULL_DEPENDENCIES if importlib.util.find_spec(name) is None]
        if missing:
            print(f"Full verification unavailable: missing {', '.join(missing)}.", file=sys.stderr)
            print("Install dependencies with `pip install -r requirements-core.txt`.", file=sys.stderr)
            return 2
        from pydantic import BaseModel
        if not hasattr(BaseModel, "model_validate"):
            print("Full verification requires Pydantic 2; install requirements-core.txt.", file=sys.stderr)
            return 2
        if importlib.util.find_spec("deepeval") is None:
            print("Optional DeepEval record construction skipped: deepeval is not installed.", flush=True)
        command = [sys.executable, "-m", "pytest", "tests", "-q", "-rs"]
    else:
        print("Demo: checking tool guards and fail-closed behavior with the Python standard library.", flush=True)
        print("Skipped: JSON Schema evaluation, Pydantic validation, DeepEval record construction, and full pytest suite.", flush=True)
        command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_strict_boundaries.py", "-v"]

    result = subprocess.run(command, cwd=BASE_DIR, check=False)
    if result.returncode == 0:
        print(f"{'Full verification' if args.full else 'Demo'} passed; see runner output for executed checks.")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
