# Changelog

All notable changes to the BartsAI Agent Production Starter are documented here.

## [0.2.0] - 2026-10-01

### Changed

- JSON Schema validation now fails closed when `jsonschema` is unavailable instead of using a partial fallback.
- `run_tests.py` now requires an explicit `--demo` or `--full` mode and reports skipped optional checks.
- Recognized path arguments are checked recursively in nested dictionaries and lists.
- Core test dependencies are separated from the optional DeepEval integration.

### Added

- Dependency-free regression tests for missing-schema and nested-path boundaries.
- A read-only GitHub Actions matrix for Python 3.10, 3.11 and 3.12.
- Explicit migration, CI-evidence and executor-isolation limitations in both READMEs.

### Migration notes

- Install `requirements-core.txt` before calling JSON Schema or Pydantic validation and before running `python3 run_tests.py --full`.
- Update scripts that called `run_tests.py` without a mode.
- Add regression cases for every nested path shape used by your tool adapters.
- Verify that the real executor uses a root-anchored target and cannot bypass the guard. Passing these sample tests does not prove OS-level isolation.
