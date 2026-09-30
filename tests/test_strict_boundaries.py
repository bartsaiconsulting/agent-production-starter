"""Dependency-free regression checks for the Starter's fail-closed boundaries."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bartsai_guard import PathTraversalError, SchemaValidationError, SchemaValidator, ToolGuard


class StrictBoundaryTests(unittest.TestCase):
    def test_missing_jsonschema_never_uses_a_partial_validator(self):
        with patch("bartsai_guard.schema_validator.HAS_JSONSCHEMA", False):
            with self.assertRaisesRegex(SchemaValidationError, "requires jsonschema"):
                SchemaValidator.validate_json_schema(
                    {"customer_id": "wrong", "status": "active", "extra": True},
                    {"type": "object", "required": ["customer_id", "status"]},
                )

    def test_nested_paths_and_rejected_calls_never_dispatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            root.mkdir()
            outside = Path(temp_dir) / "outside"
            outside.mkdir()
            (root / "external").symlink_to(outside, target_is_directory=True)
            guard = ToolGuard(allowed_tools={"read_file"}, sandbox_root=root)
            dispatches = []

            def dispatch(arguments):
                guard.inspect_and_authorize("read_file", arguments)
                dispatches.append(arguments)

            safe = {"files": [{"path": "notes.txt"}, {"nested": {"output_path": str(root / "output.txt")}}]}
            dispatch(safe)
            self.assertEqual(len(dispatches), 1)

            invalid = [
                {"path": "../outside/file.txt"},
                {"path": str(outside / "file.txt")},
                {"files": [{"path": "../outside/file.txt"}]},
                {"files": [{"nested": {"dest": str(outside)}}]},
                {"path": 42},
                {"files": [{"path": ["notes.txt"]}]},
                {"path": ""},
                {"path": "external/file.txt"},
            ]
            for arguments in invalid:
                with self.subTest(arguments=arguments):
                    with self.assertRaises(PathTraversalError):
                        dispatch(arguments)
                    self.assertEqual(len(dispatches), 1)


if __name__ == "__main__":
    unittest.main()
