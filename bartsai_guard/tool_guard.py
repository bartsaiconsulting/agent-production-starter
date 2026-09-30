"""
Tool Guard Module: Tool allowlists, recognized path argument checks, and approval gates.
These checks do not isolate the executor or provide filesystem confinement.
"""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class ToolPermissionLevel(str, Enum):
    READ_ONLY = "READ_ONLY"
    MUTATIVE_WRITE = "MUTATIVE_WRITE"
    DESTRUCTIVE = "DESTRUCTIVE"


class ToolGuardError(Exception):
    """Base exception for tool authorization failures."""
    pass


class ToolPermissionDeniedError(ToolGuardError):
    """Raised when an agent attempts to invoke a tool that is not in the allowlist."""
    pass


class PathTraversalError(ToolGuardError):
    """Raised when a recognized path argument is invalid or resolves outside the declared root."""
    pass


class HumanApprovalRequiredError(ToolGuardError):
    """Raised when an irreversible or destructive action is attempted without human authorization."""
    pass


class ToolGuard:
    """
    Guards tool execution requests by validating:
    1. Tool Allowlist and Permission Scoping
    2. Recognized path argument validation (not OS sandboxing)
    3. Human-in-the-Loop Two-Phase Commit for Destructive actions
    """

    def __init__(
        self,
        allowed_tools: Set[str],
        tool_permissions: Optional[Dict[str, ToolPermissionLevel]] = None,
        sandbox_root: Optional[Path] = None,
        require_human_approval_for_destructive: bool = True,
        valid_approval_tokens: Optional[Set[str]] = None,
    ) -> None:
        self.allowed_tools = set(allowed_tools)
        self.tool_permissions = tool_permissions or {}
        self.sandbox_root = sandbox_root.resolve() if sandbox_root else None
        self.require_human_approval_for_destructive = require_human_approval_for_destructive
        self.valid_approval_tokens = valid_approval_tokens or set()

    def inspect_and_authorize(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        approval_token: Optional[str] = None,
    ) -> None:
        """
        Validates the proposed tool call before execution.
        Raises an exception if any safety rule is violated.
        """
        # 1. Tool Allowlist Check
        if tool_name not in self.allowed_tools:
            raise ToolPermissionDeniedError(
                f"Unauthorized tool execution: '{tool_name}' is not in the approved tool allowlist."
            )

        # 2. Permission Level & Human Approval Check
        permission_level = self.tool_permissions.get(tool_name, ToolPermissionLevel.READ_ONLY)
        if (
            permission_level == ToolPermissionLevel.DESTRUCTIVE
            and self.require_human_approval_for_destructive
        ):
            if not approval_token or approval_token not in self.valid_approval_tokens:
                raise HumanApprovalRequiredError(
                    f"Two-phase approval required: Tool '{tool_name}' is categorized as DESTRUCTIVE. "
                    f"Execution blocked pending explicit human sign-off."
                )

        # 3. Recognized path argument checks
        if self.sandbox_root:
            self._validate_path_arguments(arguments)

    def _validate_path_arguments(self, arguments: Any) -> None:
        """Inspect known path keys in dictionaries and lists, including nested values."""
        path_keys = {"path", "file_path", "filepath", "target_file", "dest", "destination", "output_path"}

        if isinstance(arguments, list):
            for value in arguments:
                self._validate_path_arguments(value)
            return

        if not isinstance(arguments, dict):
            return

        for key, value in arguments.items():
            if isinstance(key, str) and key.lower() in path_keys:
                if not isinstance(value, str) or not value or "\0" in value:
                    raise PathTraversalError(f"Invalid path argument for '{key}': expected a non-empty string")
                target_path = Path(value)
                resolved = (self.sandbox_root / target_path).resolve() if not target_path.is_absolute() else target_path.resolve()
                try:
                    resolved.relative_to(self.sandbox_root)
                except ValueError as exc:
                    raise PathTraversalError(
                        f"Path traversal detected: Target path '{value}' resolves to '{resolved}', "
                        f"which escapes the designated sandbox root '{self.sandbox_root}'."
                    ) from exc
            elif isinstance(value, (dict, list)):
                self._validate_path_arguments(value)
