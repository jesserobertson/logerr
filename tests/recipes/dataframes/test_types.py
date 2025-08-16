"""
Tests for logerr.recipes.dataframes.types module.
"""

from datetime import datetime
from typing import Union

import pytest

from logerr.recipes.dataframes.types import (
    BSON_TYPE_MAPPING,
    FieldSpec,
    Required,
    get_pandas_dtype,
    get_polars_dtype,
    is_valid_type_spec,
)

pytestmark = [pytest.mark.recipes, pytest.mark.dataframes]


class TestRequired:
    """Tests for Required marker type."""

    def test_required_instance_creation(self):
        """Test creating Required instance directly."""
        req = Required(str)
        assert req.inner_type is str

    def test_required_class_getitem_syntax(self):
        """Test Required[T] syntax works."""
        req_str = Required[str]
        assert isinstance(req_str, Required)
        assert req_str.inner_type is str

        req_int = Required[int]
        assert isinstance(req_int, Required)
        assert req_int.inner_type is int

    def test_required_with_complex_types(self):
        """Test Required works with complex types."""
        req_list = Required[list[str]]
        assert isinstance(req_list, Required)
        assert req_list.inner_type == list[str]

        req_dict = Required[dict[str, int]]
        assert isinstance(req_dict, Required)
        assert req_dict.inner_type == dict[str, int]

    def test_required_different_types(self):
        """Test Required with various Python types."""
        types_to_test = [str, int, float, bool, dict, list, bytes, datetime]

        for type_spec in types_to_test:
            req = Required[type_spec]
            assert isinstance(req, Required)
            assert req.inner_type is type_spec


class TestFieldSpec:
    """Tests for FieldSpec dataclass."""

    def test_fieldspec_creation(self):
        """Test basic FieldSpec creation."""
        spec = FieldSpec(
            name="user_id", field_type=str, is_required=True, default_value="guest"
        )

        assert spec.name == "user_id"
        assert spec.field_type is str
        assert spec.is_required is True
        assert spec.default_value == "guest"

    def test_fieldspec_default_values(self):
        """Test FieldSpec with default values."""
        spec = FieldSpec(name="age", field_type=int, is_required=False)

        assert spec.name == "age"
        assert spec.field_type is int
        assert spec.is_required is False
        assert spec.default_value is None

    def test_from_schema_entry_required_instance(self):
        """Test from_schema_entry with Required instance."""
        req_type = Required(str)
        spec = FieldSpec.from_schema_entry("user_id", req_type)

        assert spec.name == "user_id"
        assert spec.field_type is str
        assert spec.is_required is True
        assert spec.default_value is None

    def test_from_schema_entry_required_annotation(self):
        """Test from_schema_entry with Required[T] type annotation."""
        spec = FieldSpec.from_schema_entry("email", Required[str])

        assert spec.name == "email"
        assert spec.field_type is str
        assert spec.is_required is True

    def test_from_schema_entry_optional_types(self):
        """Test from_schema_entry with regular types (treated as optional)."""
        test_cases = [
            (str, str),
            (int, int),
            (float, float),
            (bool, bool),
            (dict, dict),
            (list, list),
        ]

        for input_type, expected_type in test_cases:
            spec = FieldSpec.from_schema_entry("field", input_type)
            assert spec.name == "field"
            assert spec.field_type is expected_type
            assert spec.is_required is False

    def test_from_schema_entry_complex_types(self):
        """Test from_schema_entry with complex generic types."""
        # Test with List[str]
        spec = FieldSpec.from_schema_entry("tags", list[str])
        assert spec.name == "tags"
        assert spec.field_type == list[str]
        assert spec.is_required is False

        # Test with Dict[str, int]
        spec = FieldSpec.from_schema_entry("counts", dict[str, int])
        assert spec.name == "counts"
        assert spec.field_type == dict[str, int]
        assert spec.is_required is False

    def test_from_schema_entry_various_required_types(self):
        """Test from_schema_entry with various Required types."""
        test_cases = [
            (Required[int], int),
            (Required[float], float),
            (Required[bool], bool),
            (Required[datetime], datetime),
            (Required[list[str]], list[str]),
        ]

        for input_spec, expected_type in test_cases:
            spec = FieldSpec.from_schema_entry("field", input_spec)
            assert spec.field_type == expected_type
            assert spec.is_required is True


class TestTypeMappings:
    """Tests for type mapping constants and functions."""

    def test_bson_type_mapping_completeness(self):
        """Test that BSON_TYPE_MAPPING covers expected types."""
        expected_mappings = {
            str: "string",
            int: "Int64",
            float: "Float64",
            bool: "boolean",
            datetime: "datetime64[ns]",
            dict: "object",
            list: "object",
            bytes: "object",
        }

        for type_spec, expected_dtype in expected_mappings.items():
            assert BSON_TYPE_MAPPING[type_spec] == expected_dtype

    def test_is_valid_type_spec_required_instances(self):
        """Test is_valid_type_spec with Required instances."""
        assert is_valid_type_spec(Required(str)) is True
        assert is_valid_type_spec(Required[int]) is True
        assert is_valid_type_spec(Required[list[str]]) is True

    def test_is_valid_type_spec_basic_types(self):
        """Test is_valid_type_spec with basic Python types."""
        valid_types = [str, int, float, bool, dict, list, bytes, datetime]

        for type_spec in valid_types:
            assert is_valid_type_spec(type_spec) is True

    def test_is_valid_type_spec_generic_types(self):
        """Test is_valid_type_spec with generic types."""
        generic_types = [list[str], dict[str, int], Union[str, int]]  # noqa: UP007

        for type_spec in generic_types:
            assert is_valid_type_spec(type_spec) is True

    def test_is_valid_type_spec_invalid_types(self):
        """Test is_valid_type_spec with invalid specifications."""
        invalid_specs = ["not_a_type", 42, None, {"invalid": "dict"}]

        for invalid_spec in invalid_specs:
            assert is_valid_type_spec(invalid_spec) is False

    def test_get_pandas_dtype_basic_types(self):
        """Test get_pandas_dtype with basic field types."""
        test_cases = [
            (str, "string"),
            (int, "Int64"),
            (float, "Float64"),
            (bool, "boolean"),
            (datetime, "datetime64[ns]"),
            (dict, "object"),
            (list, "object"),
            (bytes, "object"),
        ]

        for field_type, expected_dtype in test_cases:
            spec = FieldSpec("field", field_type, False)
            assert get_pandas_dtype(spec) == expected_dtype

    def test_get_pandas_dtype_required_fields(self):
        """Test get_pandas_dtype with required fields."""
        # Required fields should still use nullable types for NoSQL flexibility
        spec = FieldSpec("required_field", str, True)
        assert get_pandas_dtype(spec) == "string"

        spec = FieldSpec("required_int", int, True)
        assert get_pandas_dtype(spec) == "Int64"

    def test_get_pandas_dtype_unknown_type(self):
        """Test get_pandas_dtype with unknown type defaults to object."""

        class CustomType:
            pass

        spec = FieldSpec("custom", CustomType, False)
        assert get_pandas_dtype(spec) == "object"

    def test_get_polars_dtype_basic_types(self):
        """Test get_polars_dtype with basic field types."""
        test_cases = [
            (str, "Utf8"),
            (int, "Int64"),
            (float, "Float64"),
            (bool, "Boolean"),
            (datetime, "Datetime"),
            (dict, "Object"),
            (list, "Object"),
            (bytes, "Binary"),
        ]

        for field_type, expected_dtype in test_cases:
            spec = FieldSpec("field", field_type, False)
            assert get_polars_dtype(spec) == expected_dtype

    def test_get_polars_dtype_unknown_type(self):
        """Test get_polars_dtype with unknown type defaults to Object."""

        class CustomType:
            pass

        spec = FieldSpec("custom", CustomType, False)
        assert get_polars_dtype(spec) == "Object"

    def test_pandas_polars_dtype_consistency(self):
        """Test that pandas and polars dtypes are consistent for common types."""
        common_types = [str, int, float, bool, datetime]

        for type_spec in common_types:
            spec = FieldSpec("field", type_spec, False)
            pandas_dtype = get_pandas_dtype(spec)
            polars_dtype = get_polars_dtype(spec)

            # Both should return string values
            assert isinstance(pandas_dtype, str)
            assert isinstance(polars_dtype, str)
            # Both should handle the type (not return default)
            assert (
                pandas_dtype != "object"
                or polars_dtype != "Object"
                or type_spec in [dict, list, bytes]
            )


class TestSchemaExamples:
    """Integration tests with realistic schema examples."""

    def test_user_schema_example(self):
        """Test with a realistic user schema."""
        schema = {
            "user_id": Required[str],
            "email": Required[str],
            "name": str,
            "age": int,
            "is_active": bool,
            "metadata": dict,
            "tags": list[str],
        }

        # Test all field specifications
        user_id_spec = FieldSpec.from_schema_entry("user_id", schema["user_id"])
        assert user_id_spec.is_required is True
        assert user_id_spec.field_type is str

        name_spec = FieldSpec.from_schema_entry("name", schema["name"])
        assert name_spec.is_required is False
        assert name_spec.field_type is str

        # Test pandas dtypes
        assert get_pandas_dtype(user_id_spec) == "string"
        assert get_pandas_dtype(name_spec) == "string"

        # Test type validation
        for _field_name, type_spec in schema.items():
            assert is_valid_type_spec(type_spec) is True

    def test_mixed_schema_processing(self):
        """Test processing a schema with mixed required/optional fields."""
        schema = {
            "id": Required[int],
            "timestamp": Required[datetime],
            "optional_text": str,
            "optional_count": int,
            "config": dict,
        }

        field_specs = {}
        for field_name, type_spec in schema.items():
            field_specs[field_name] = FieldSpec.from_schema_entry(field_name, type_spec)

        # Check required fields
        assert field_specs["id"].is_required is True
        assert field_specs["timestamp"].is_required is True

        # Check optional fields
        assert field_specs["optional_text"].is_required is False
        assert field_specs["optional_count"].is_required is False
        assert field_specs["config"].is_required is False

        # Check types preserved correctly
        assert field_specs["id"].field_type is int
        assert field_specs["timestamp"].field_type is datetime
        assert field_specs["optional_text"].field_type is str
