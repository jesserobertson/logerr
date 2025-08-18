"""
Basic integration tests for logerr.
"""

import pytest

from logerr import Nothing, Option, Result, Some


@pytest.mark.integration
def test_option_result_integration():
    """Test integration between Option and Result types."""
    # Test converting Option to Result
    some_value = Some(42)
    result_from_some = some_value.ok_or("No value")
    assert result_from_some.is_ok()
    assert result_from_some.unwrap() == 42

    nothing_value = Nothing()
    result_from_nothing = nothing_value.ok_or("No value")
    assert result_from_nothing.is_err()
    assert result_from_nothing.unwrap_err() == "No value"


@pytest.mark.integration
def test_full_workflow_integration():
    """Test a complete workflow using multiple logerr types."""

    def process_data(data: dict) -> Result[int, str]:
        """Process data and return a result."""
        value = Option.from_nullable(data.get("value"))

        return (
            value.filter(lambda x: isinstance(x, int))
            .filter(lambda x: x > 0)
            .ok_or("Invalid or missing value")
            .map(lambda x: x * 2)
        )

    # Test successful case
    good_data = {"value": 21}
    result = process_data(good_data)
    assert result.is_ok()
    assert result.unwrap() == 42

    # Test failure cases
    bad_data_cases = [
        {"value": None},  # None value
        {"value": -5},  # Negative value
        {"value": "not_int"},  # Wrong type
        {},  # Missing key
    ]

    for bad_data in bad_data_cases:
        result = process_data(bad_data)
        assert result.is_err()
        assert result.unwrap_err() == "Invalid or missing value"
