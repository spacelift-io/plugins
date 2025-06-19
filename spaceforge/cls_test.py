import pytest

from spaceforge import Parameter, Variable


def test_ensure_optional_parameters_require_default_values() -> None:
    with pytest.raises(ValueError):
        Parameter(
            name="optional_default",
            description="default value",
            required=False,
        )


def test_ensure_variables_have_either_value_or_value_from_parameter() -> None:
    with pytest.raises(ValueError):
        Variable(key="test_var", sensitive=False)
