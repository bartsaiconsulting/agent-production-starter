"""
Schema Validator Module: Deterministic Type and Structural Verification.
Validates LLM tool arguments and outputs against JSON Schema and Pydantic models.
"""

from typing import Any, Dict, Type

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

try:
    from pydantic import BaseModel, ValidationError
    HAS_PYDANTIC = True
except ImportError:
    BaseModel = Any  # type: ignore
    HAS_PYDANTIC = False


class SchemaValidationError(Exception):
    """Raised when an agent's tool arguments fail structural or type validation."""
    pass


class SchemaValidator:
    """
    Deterministic Schema Validator.
    Rejects malformed arguments or wildcards before hitting business logic.
    """

    @staticmethod
    def validate_json_schema(payload: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """
        Validates payload against a standard JSON Schema.
        Raises SchemaValidationError on mismatch.
        """
        if not HAS_JSONSCHEMA:
            # Fallback basic checks if jsonschema package is not yet installed
            required = schema.get("required", [])
            for field in required:
                if field not in payload:
                    raise SchemaValidationError(f"Missing required property: '{field}'")
            return

        try:
            jsonschema.validate(instance=payload, schema=schema)
        except jsonschema.exceptions.ValidationError as e:
            raise SchemaValidationError(
                f"JSON Schema validation failed at path '{list(e.path)}': {e.message}"
            ) from e

    @staticmethod
    def validate_pydantic(payload: Dict[str, Any], model_cls: Type[BaseModel]) -> Any:
        """
        Validates and parses payload into a Pydantic Model.
        Raises SchemaValidationError on validation failure.
        """
        if not HAS_PYDANTIC:
            raise SchemaValidationError(
                "Pydantic is not installed. Install requirements via `pip install -r requirements.txt`"
            )

        try:
            return model_cls.model_validate(payload)
        except ValidationError as e:
            errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            raise SchemaValidationError(
                f"Pydantic schema validation failed for {model_cls.__name__}: {'; '.join(errors)}"
            ) from e

    @staticmethod
    def assert_no_empty_where_clause(query_params: Dict[str, Any]) -> None:
        """
        Defense against runaway DB mutations: Ensures UPDATE/DELETE calls
        cannot execute with an empty or omitted filter/WHERE condition.
        """
        filters = query_params.get("filters") or query_params.get("where") or query_params.get("criteria")
        if filters is None or (isinstance(filters, (dict, list, str)) and len(filters) == 0):
            raise SchemaValidationError(
                "Unbounded mutation rejected: Database operation requires an explicit, non-empty "
                "filter/WHERE condition to prevent accidental table-wide modifications."
            )
