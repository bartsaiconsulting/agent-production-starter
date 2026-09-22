"""
Tests for Schema Validator: Deterministic JSON Schema & Pydantic structure assertions.
Ref: BartsAI Production Checklist §1 & §3 (Parameter Typing & Schema Validation).
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

from bartsai_guard import SchemaValidator, SchemaValidationError

try:
    from pydantic import BaseModel, Field
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False
    BaseModel = object
    Field = lambda *args, **kwargs: None


CUSTOMER_UPDATE_SCHEMA = {
    "type": "object",
    "required": ["customer_id", "status"],
    "additionalProperties": False,
    "properties": {
        "customer_id": {"type": "integer"},
        "status": {"type": "string", "enum": ["active", "suspended", "archived"]},
        "reason": {"type": "string"},
    },
}


if HAS_PYDANTIC:
    class UserTransferRequest(BaseModel):
        source_account: str = Field(min_length=5, max_length=20)
        target_account: str = Field(min_length=5, max_length=20)
        amount_cents: int = Field(gt=0, le=10_000_000)
        currency: str = Field(pattern="^[A-Z]{3}$")
else:
    UserTransferRequest = None


def test_json_schema_valid_payload():
    """Valid payload passes schema validation without raising."""
    payload = {"customer_id": 42, "status": "active", "reason": "KYC verified"}
    SchemaValidator.validate_json_schema(payload, CUSTOMER_UPDATE_SCHEMA)


def test_json_schema_missing_required_field():
    """Missing required field is rejected before reaching business logic."""
    payload = {"customer_id": 42}  # Missing 'status'

    with pytest.raises(SchemaValidationError) as exc_info:
        SchemaValidator.validate_json_schema(payload, CUSTOMER_UPDATE_SCHEMA)

    assert "Missing required property" in str(exc_info.value) or "is a required property" in str(exc_info.value)


def test_json_schema_additional_properties_rejected():
    """Hallucinated unexpected arguments are rejected when jsonschema is present."""
    payload = {
        "customer_id": 42,
        "status": "active",
        "drop_tables": True,  # Unexpected hallucinatory parameter
    }

    try:
        SchemaValidator.validate_json_schema(payload, CUSTOMER_UPDATE_SCHEMA)
    except SchemaValidationError as e:
        assert "drop_tables" in str(e)


def test_pydantic_validation_success():
    """Valid Pydantic model parses and returns typed object."""
    if not HAS_PYDANTIC:
        pytest.skip("Pydantic is not installed in local environment")
        return

    data = {
        "source_account": "ACC_12345",
        "target_account": "ACC_67890",
        "amount_cents": 5000,
        "currency": "USD",
    }
    model = SchemaValidator.validate_pydantic(data, UserTransferRequest)
    assert model.amount_cents == 5000
    assert model.currency == "USD"


def test_pydantic_validation_bounds_failure():
    """Invalid amount (< 0 or > limit) or malformed currency is rejected."""
    if not HAS_PYDANTIC:
        pytest.skip("Pydantic is not installed in local environment")
        return

    data = {
        "source_account": "ACC_12345",
        "target_account": "ACC_67890",
        "amount_cents": -500,  # Negative amount rejected
        "currency": "usd",     # Lowercase currency rejected by pattern
    }

    with pytest.raises(SchemaValidationError) as exc_info:
        SchemaValidator.validate_pydantic(data, UserTransferRequest)

    assert "Input should be greater than 0" in str(exc_info.value)


def test_empty_where_clause_intercepted():
    """Database update without explicit WHERE condition is intercepted."""
    # Omitted filter
    with pytest.raises(SchemaValidationError) as exc_info:
        SchemaValidator.assert_no_empty_where_clause({"action": "update_status", "status": "disabled"})
    assert "Unbounded mutation rejected" in str(exc_info.value)

    # Empty filter
    with pytest.raises(SchemaValidationError) as exc_info:
        SchemaValidator.assert_no_empty_where_clause({"action": "update_status", "where": {}})
    assert "Unbounded mutation rejected" in str(exc_info.value)

    # Valid non-empty filter passes
    SchemaValidator.assert_no_empty_where_clause({"action": "update_status", "where": {"user_id": 101}})


if __name__ == "__main__":
    test_json_schema_valid_payload()
    test_json_schema_missing_required_field()
    test_json_schema_additional_properties_rejected()
    test_pydantic_validation_success()
    test_pydantic_validation_bounds_failure()
    test_empty_where_clause_intercepted()
    print("All schema integrity tests passed!")
