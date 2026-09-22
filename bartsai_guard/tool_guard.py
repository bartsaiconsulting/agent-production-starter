"""
Tool Guard Module: Least-Privilege Scoping, Path Traversal Defense, and Approval Gates.
Enforces physical tool permissions, filesystem boundaries, and human sign-off.
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
    """Raised when a tool argument attempts to escape the designated sandbox filesystem root."""
    pass


class HumanApprovalRequiredError(ToolGuardError):
    """Raised when an irreversible or destructive action is attempted without human authorization."""
    pass


class ToolGuard:
    """
    Guards tool execution requests by validating:
    1. Tool Allowlist and Permission Scoping
    2. Filesystem sandbox boundary confinement (Anti-Traversal)
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

        # 3. Path Traversal & Sandbox Confinement
        if self.sandbox_root:
            self._validate_path_arguments(arguments)

    def _validate_path_arguments(self, arguments: Dict[str, Any]) -> None:
        """Inspects arguments for filepath keys and ensures they stay within sandbox_root."""
        path_keys = {"path", "file_path", "filepath", "target_file", "dest", "destination", "output_path"}

        for key, val in arguments.items():
            if key.lower() in path_keys and isinstance(val, str):
                target_path = Path(val)
                # Resolve path relative to sandbox_root if relative
                if not target_path.is_absolute():
                    resolved = (self.sandbox_root / target_path).resolve()
                else:
                    resolved = target_path.resolve()

                try:
                    resolved.relative_to(self.sandbox_root)
                except ValueError:
                    raise PathTraversalError(
                        f"Path traversal detected: Target path '{val}' resolves to '{resolved}', "
                        f"which escapes the designated sandbox root '{self.sandbox_root}'."
                    )
            elif isinstance(val, dict):
                self._validate_path_arguments(val)
