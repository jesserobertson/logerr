"""
Tests for logerr.recipes.dataframes.conversion module.
"""

from datetime import datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st

from logerr.recipes.dataframes.conversion import (
    convert_bson_value,
    convert_document_to_row,
    infer_schema_from_documents,
    normalize_field_name,
    prepare_dataframe_dtypes,
)
from logerr.recipes.dataframes.quality import DataQualityTracker
from logerr.recipes.dataframes.types import FieldSpec, Required

pytestmark = [pytest.mark.recipes, pytest.mark.dataframes]


class TestConvertBsonValueNone:
    """Tests for None handling in convert_bson_value."""

    def test_none_value_returns_nothing(self):
        result = convert_bson_value(None, str, "field")
        assert result.is_nothing()

    def test_none_value_records_no_conversion_error(self):
        tracker = DataQualityTracker("op")
        result = convert_bson_value(None, str, "field", tracker)
        assert result.is_nothing()
        # None short-circuits before the conversion-error path
        assert tracker.field_conversion_errors["field"] == 0


class TestConvertBsonValueStr:
    """Tests for str target type conversion."""

    def test_int_to_str(self):
        result = convert_bson_value(42, str, "field")
        assert result.is_some()
        assert result.unwrap() == "42"

    def test_float_to_str(self):
        result = convert_bson_value(3.14, str, "field")
        assert result.unwrap() == "3.14"

    def test_str_to_str(self):
        result = convert_bson_value("hello", str, "field")
        assert result.unwrap() == "hello"


class TestConvertBsonValueInt:
    """Tests for int target type conversion."""

    def test_int_passthrough(self):
        result = convert_bson_value(42, int, "field")
        assert result.unwrap() == 42

    def test_integer_float_converts(self):
        result = convert_bson_value(42.0, int, "field")
        assert result.unwrap() == 42
        assert isinstance(result.unwrap(), int)

    def test_non_integer_float_truncates(self):
        # Only whole-number floats take the fast "is_integer" path; other
        # floats fall through to the generic `int(value)` branch, which
        # truncates rather than rejecting the value.
        result = convert_bson_value(42.5, int, "field")
        assert result.is_some()
        assert result.unwrap() == 42

    def test_valid_string_converts(self):
        result = convert_bson_value("42", int, "field")
        assert result.unwrap() == 42

    def test_string_with_whitespace_converts(self):
        result = convert_bson_value("  42  ", int, "field")
        assert result.unwrap() == 42

    def test_empty_string_fails(self):
        result = convert_bson_value("   ", int, "field")
        assert result.is_nothing()

    def test_non_numeric_string_fails(self):
        result = convert_bson_value("not-a-number", int, "field")
        assert result.is_nothing()

    def test_bool_as_int(self):
        # bool is a subclass of int in Python
        result = convert_bson_value(True, int, "field")
        assert result.unwrap() == 1

    def test_other_type_uses_int_conversion(self):
        result = convert_bson_value([1, 2], int, "field")
        assert result.is_nothing()


class TestConvertBsonValueFloat:
    """Tests for float target type conversion."""

    def test_int_to_float(self):
        result = convert_bson_value(42, float, "field")
        assert result.unwrap() == 42.0

    def test_float_passthrough(self):
        result = convert_bson_value(3.14, float, "field")
        assert result.unwrap() == 3.14

    def test_valid_string_converts(self):
        result = convert_bson_value("3.14", float, "field")
        assert result.unwrap() == 3.14

    def test_empty_string_fails(self):
        result = convert_bson_value("  ", float, "field")
        assert result.is_nothing()

    def test_non_numeric_string_fails(self):
        result = convert_bson_value("abc", float, "field")
        assert result.is_nothing()

    def test_other_type_conversion_error(self):
        result = convert_bson_value([1, 2], float, "field")
        assert result.is_nothing()


class TestConvertBsonValueBool:
    """Tests for bool target type conversion."""

    def test_bool_passthrough(self):
        assert convert_bson_value(True, bool, "field").unwrap() is True
        assert convert_bson_value(False, bool, "field").unwrap() is False

    def test_int_to_bool(self):
        assert convert_bson_value(1, bool, "field").unwrap() is True
        assert convert_bson_value(0, bool, "field").unwrap() is False

    @pytest.mark.parametrize("text", ["true", "yes", "1", "on", "TRUE", " True "])
    def test_truthy_strings(self, text):
        assert convert_bson_value(text, bool, "field").unwrap() is True

    @pytest.mark.parametrize("text", ["false", "no", "0", "off", "", "FALSE"])
    def test_falsy_strings(self, text):
        assert convert_bson_value(text, bool, "field").unwrap() is False

    def test_invalid_string_fails(self):
        result = convert_bson_value("maybe", bool, "field")
        assert result.is_nothing()

    def test_other_type_uses_bool_builtin(self):
        result = convert_bson_value([1], bool, "field")
        assert result.unwrap() is True


class TestConvertBsonValueDatetime:
    """Tests for datetime target type conversion."""

    def test_datetime_passthrough(self):
        now = datetime(2024, 1, 1, 12, 0, 0)
        result = convert_bson_value(now, datetime, "field")
        assert result.unwrap() == now

    def test_date_only_string(self):
        result = convert_bson_value("2024-01-15", datetime, "field")
        assert result.unwrap() == datetime(2024, 1, 15)

    def test_datetime_with_seconds_string(self):
        result = convert_bson_value("2024-01-15 10:30:00", datetime, "field")
        assert result.unwrap() == datetime(2024, 1, 15, 10, 30, 0)

    def test_iso_format_string(self):
        result = convert_bson_value("2024-01-15T10:30:00", datetime, "field")
        assert result.unwrap() == datetime(2024, 1, 15, 10, 30, 0)

    def test_iso_format_with_z_string(self):
        result = convert_bson_value("2024-01-15T10:30:00Z", datetime, "field")
        assert result.unwrap() == datetime(2024, 1, 15, 10, 30, 0)

    def test_datetime_with_microseconds_string(self):
        result = convert_bson_value("2024-01-15 10:30:00.123456", datetime, "field")
        assert result.unwrap() == datetime(2024, 1, 15, 10, 30, 0, 123456)

    def test_unparseable_string_fails(self):
        result = convert_bson_value("not-a-date", datetime, "field")
        assert result.is_nothing()

    def test_numeric_timestamp_converts(self):
        result = convert_bson_value(0, datetime, "field")
        assert result.is_some()
        assert isinstance(result.unwrap(), datetime)

    def test_unsupported_type_fails(self):
        result = convert_bson_value([1, 2], datetime, "field")
        assert result.is_nothing()


class TestConvertBsonValueContainers:
    """Tests for dict/list target type conversion."""

    def test_dict_passthrough(self):
        value = {"a": 1}
        result = convert_bson_value(value, dict, "field")
        assert result.unwrap() == value

    def test_list_passthrough(self):
        value = [1, 2, 3]
        result = convert_bson_value(value, list, "field")
        assert result.unwrap() == value

    def test_list_from_other_iterable(self):
        result = convert_bson_value((1, 2, 3), list, "field")
        assert result.unwrap() == [1, 2, 3]

    def test_dict_from_pairs(self):
        result = convert_bson_value([("a", 1)], dict, "field")
        assert result.unwrap() == {"a": 1}

    def test_dict_conversion_failure(self):
        result = convert_bson_value(42, dict, "field")
        assert result.is_nothing()


class TestConvertBsonValueOtherTypes:
    """Tests for the fallback conversion branch."""

    def test_generic_type_conversion(self):
        result = convert_bson_value(42, complex, "field")
        assert result.unwrap() == complex(42)

    def test_generic_type_conversion_failure(self):
        class Uninstantiable:
            def __init__(self, value):
                raise ValueError("nope")

        result = convert_bson_value(1, Uninstantiable, "field")
        assert result.is_nothing()


class TestConvertBsonValueQualityTracking:
    """Tests verifying quality_tracker integration on conversion failures."""

    def test_records_conversion_error_with_value_and_error(self):
        tracker = DataQualityTracker("op")
        result = convert_bson_value("abc", int, "count", tracker)

        assert result.is_nothing()
        assert tracker.field_conversion_errors["count"] == 1
        assert tracker.field_invalid_values["count"] == ["abc"]

    def test_multiple_errors_accumulate(self):
        tracker = DataQualityTracker("op")
        convert_bson_value("abc", int, "count", tracker)
        convert_bson_value("xyz", int, "count", tracker)

        assert tracker.field_conversion_errors["count"] == 2
        assert tracker.field_invalid_values["count"] == ["abc", "xyz"]

    def test_no_tracker_does_not_raise(self):
        result = convert_bson_value("abc", int, "count", None)
        assert result.is_nothing()


class TestInferSchemaFromDocuments:
    """Tests for infer_schema_from_documents."""

    def test_empty_documents_returns_empty_schema(self):
        assert infer_schema_from_documents([]) == {}

    def test_single_document_single_field(self):
        docs = [{"name": "Alice"}]
        schema = infer_schema_from_documents(docs)
        assert schema == {"name": str}

    def test_multiple_fields(self):
        docs = [{"name": "Alice", "age": 30, "active": True}]
        schema = infer_schema_from_documents(docs)
        assert schema == {"name": str, "age": int, "active": bool}

    def test_most_common_type_wins(self):
        docs = [
            {"value": "a"},
            {"value": "b"},
            {"value": 1},
        ]
        schema = infer_schema_from_documents(docs)
        assert schema["value"] is str

    def test_int_and_float_mix_prefers_float(self):
        docs = [{"value": 1}, {"value": 2.5}]
        schema = infer_schema_from_documents(docs)
        assert schema["value"] is float

    def test_int_only_stays_int(self):
        docs = [{"value": 1}, {"value": 2}]
        schema = infer_schema_from_documents(docs)
        assert schema["value"] is int

    def test_missing_keys_across_documents(self):
        docs = [{"a": 1}, {"b": "x"}]
        schema = infer_schema_from_documents(docs)
        assert schema == {"a": int, "b": str}

    def test_none_values_produce_nonetype(self):
        docs = [{"a": None}]
        schema = infer_schema_from_documents(docs)
        assert schema["a"] is type(None)

    def test_sample_size_limits_documents_considered(self):
        docs = [{"value": "a"}, {"value": "b"}, {"value": 1}]
        # With sample_size=1 only the first doc ("value": "a") is considered
        schema = infer_schema_from_documents(docs, sample_size=1)
        assert schema["value"] is str

    def test_sample_size_none_uses_all_documents(self):
        docs = [{"value": 1}, {"value": 2.5}]
        schema = infer_schema_from_documents(docs, sample_size=None)
        assert schema["value"] is float

    def test_every_key_present_in_schema(self):
        docs = [{"a": 1}, {"b": 2}, {"c": 3, "a": 4}]
        schema = infer_schema_from_documents(docs)
        assert set(schema.keys()) == {"a", "b", "c"}


class TestConvertDocumentToRow:
    """Tests for convert_document_to_row."""

    def _fields(self, **kwargs):
        """Build FieldSpec list from name=(type, required) kwargs."""
        return [
            FieldSpec(name=name, field_type=t, is_required=req)
            for name, (t, req) in kwargs.items()
        ]

    def test_simple_successful_conversion(self):
        fields = self._fields(name=(str, False), age=(int, False))
        doc = {"name": "Alice", "age": "30"}
        result = convert_document_to_row(doc, fields)

        assert result.is_ok()
        assert result.unwrap() == {"name": "Alice", "age": 30}

    def test_missing_optional_field_becomes_none(self):
        fields = self._fields(name=(str, False), age=(int, False))
        doc = {"name": "Alice"}
        result = convert_document_to_row(doc, fields)

        assert result.is_ok()
        assert result.unwrap() == {"name": "Alice", "age": None}

    def test_missing_required_field_fails(self):
        fields = self._fields(user_id=(str, True))
        doc = {}
        result = convert_document_to_row(doc, fields)

        assert result.is_err()
        assert "user_id" in str(result.unwrap_err())

    def test_multiple_missing_required_fields_all_reported(self):
        fields = self._fields(user_id=(str, True), email=(str, True))
        doc = {}
        result = convert_document_to_row(doc, fields)

        assert result.is_err()
        error = result.unwrap_err()
        assert "user_id" in error
        assert "email" in error

    def test_present_but_unconvertible_optional_field_becomes_none(self):
        fields = self._fields(count=(int, False))
        doc = {"count": "not-a-number"}
        result = convert_document_to_row(doc, fields)

        assert result.is_ok()
        assert result.unwrap() == {"count": None}

    def test_present_but_unconvertible_required_field_fails(self):
        fields = self._fields(count=(int, True))
        doc = {"count": "not-a-number"}
        result = convert_document_to_row(doc, fields)

        assert result.is_err()
        assert "count" in result.unwrap_err()

    def test_none_value_for_required_field_fails(self):
        fields = self._fields(user_id=(str, True))
        doc = {"user_id": None}
        result = convert_document_to_row(doc, fields)

        assert result.is_err()

    def test_quality_tracker_records_missing_required_field(self):
        tracker = DataQualityTracker("op")
        fields = self._fields(user_id=(str, True))
        doc = {"_id": "doc1"}
        result = convert_document_to_row(doc, fields, tracker)

        assert result.is_err()
        # record_missing_required_field just logs; verify no crash and doc
        # processing completed by checking the error path was taken.

    def test_quality_tracker_records_conversion_error(self):
        tracker = DataQualityTracker("op")
        fields = self._fields(count=(int, False))
        doc = {"count": "bad"}
        convert_document_to_row(doc, fields, tracker)

        assert tracker.field_conversion_errors["count"] == 1

    def test_empty_schema_produces_empty_row(self):
        result = convert_document_to_row({"a": 1}, [])
        assert result.is_ok()
        assert result.unwrap() == {}

    def test_required_with_schema_entry_helper(self):
        fields = [FieldSpec.from_schema_entry("user_id", Required[str])]
        result = convert_document_to_row({}, fields)
        assert result.is_err()


class TestNormalizeFieldName:
    """Tests for normalize_field_name."""

    def test_simple_name_unchanged(self):
        assert normalize_field_name("name") == "name"

    def test_dots_replaced(self):
        assert normalize_field_name("user.name") == "user_name"

    def test_special_characters_replaced(self):
        assert normalize_field_name("user-name!") == "user_name_"

    def test_spaces_replaced(self):
        assert normalize_field_name("first name") == "first_name"

    def test_leading_digit_prefixed(self):
        assert normalize_field_name("123field") == "field_123field"

    def test_empty_string_becomes_unnamed(self):
        assert normalize_field_name("") == "unnamed_field"

    def test_only_special_chars_becomes_underscores_not_empty(self):
        result = normalize_field_name("$$$")
        assert result == "___"

    def test_underscore_prefixed_names_kept(self):
        assert normalize_field_name("_id") == "_id"


class TestPrepareDataframeDtypes:
    """Tests for prepare_dataframe_dtypes."""

    def test_basic_dtypes(self):
        fields = [
            FieldSpec(name="name", field_type=str, is_required=False),
            FieldSpec(name="age", field_type=int, is_required=False),
        ]
        dtypes = prepare_dataframe_dtypes(fields)
        assert dtypes == {"name": "string", "age": "Int64"}

    def test_empty_fields_produces_empty_dtypes(self):
        assert prepare_dataframe_dtypes([]) == {}

    def test_unknown_type_defaults_to_object(self):
        class Custom:
            pass

        fields = [FieldSpec(name="x", field_type=Custom, is_required=False)]
        dtypes = prepare_dataframe_dtypes(fields)
        assert dtypes == {"x": "object"}


# --- Property-based tests ---

simple_values = st.one_of(
    st.none(),
    st.integers(min_value=-(10**9), max_value=10**9),
    st.text(max_size=20),
    st.booleans(),
    st.floats(allow_nan=False, allow_infinity=False),
)

document_strategy = st.dictionaries(
    st.text(
        min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=("Ll",))
    ),
    simple_values,
    max_size=5,
)


@pytest.mark.property
class TestConversionProperties:
    """Property-based tests for schema inference and row conversion."""

    @given(st.lists(document_strategy, max_size=10))
    def test_schema_includes_every_key_present_in_any_document(self, documents):
        schema = infer_schema_from_documents(documents)
        all_keys: set[str] = set()
        for doc in documents:
            all_keys.update(doc.keys())
        assert set(schema.keys()) == all_keys

    @given(st.lists(document_strategy, min_size=1, max_size=10))
    def test_converting_n_documents_always_produces_n_rows_or_errors(self, documents):
        schema = infer_schema_from_documents(documents)
        fields = [
            FieldSpec(name=name, field_type=t, is_required=False)
            for name, t in schema.items()
        ]

        results = [convert_document_to_row(doc, fields) for doc in documents]
        assert len(results) == len(documents)
        # All fields optional => never fails since missing/unconvertible
        # values simply become None.
        assert all(r.is_ok() for r in results)

    @given(document_strategy)
    def test_optional_only_conversion_never_errors(self, document):
        schema = infer_schema_from_documents([document]) if document else {}
        fields = [
            FieldSpec(name=name, field_type=t, is_required=False)
            for name, t in schema.items()
        ]
        result = convert_document_to_row(document, fields)
        assert result.is_ok()
        assert set(result.unwrap().keys()) == set(fields_names(fields))


def fields_names(fields):
    return [f.name for f in fields]
