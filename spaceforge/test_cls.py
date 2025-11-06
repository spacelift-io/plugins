import pytest

from spaceforge import Parameter, Variable


def test_ensure_optional_parameters_require_default_values() -> None:
    with pytest.raises(ValueError):
        Parameter(
            name="optional_default",
            description="default value",
            type="string",
            required=False,
        )


def test_ensure_variables_have_either_value_or_value_from_parameter() -> None:
    with pytest.raises(ValueError):
        Variable(key="test_var", sensitive=False)


def test_parameter_type_validation_string() -> None:
    """Test that string type accepts any default value."""
    # Should not raise
    Parameter(
        name="string_param",
        description="A string parameter",
        type="string",
        required=False,
        default="any value works",
    )


def test_parameter_type_validation_number_valid() -> None:
    """Test that number type accepts valid numeric strings."""
    # Integer
    Parameter(
        name="int_param",
        description="An integer parameter",
        type="number",
        required=False,
        default=42,
    )

    # Float
    Parameter(
        name="float_param",
        description="A float parameter",
        type="number",
        required=False,
        default=3.14,
    )

    # Negative number
    Parameter(
        name="negative_param",
        description="A negative parameter",
        type="number",
        required=False,
        default=-100,
    )


def test_parameter_type_validation_number_invalid() -> None:
    """Test that number type rejects non-numeric strings."""
    with pytest.raises(
        ValueError,
        match="Parameter invalid_number has type 'number' but default value has Python type str.",
    ):
        Parameter(
            name="invalid_number",
            description="Invalid number parameter",
            type="number",
            required=False,
            default="not a number",
        )


def test_parameter_type_validation_boolean_invalid() -> None:
    """Test that boolean type rejects values other than 'true'/'false'."""
    with pytest.raises(
        ValueError,
        match="Parameter invalid_bool has type 'boolean' but default value has Python type str.",
    ):
        Parameter(
            name="invalid_bool",
            description="Invalid boolean parameter",
            type="boolean",
            required=False,
            default="1",
        )

    with pytest.raises(
        ValueError,
        match="Parameter invalid_bool2 has type 'boolean' but default value has Python type str.",
    ):
        Parameter(
            name="invalid_bool2",
            description="Invalid boolean parameter",
            type="boolean",
            required=False,
            default="yes",
        )
