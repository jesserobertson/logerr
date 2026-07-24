"""
Tests for logerr.recipes.dataframes.mongo module.

Uses lightweight fake collection/cursor objects instead of a real MongoDB
connection - only the `.find()` / cursor iteration surface actually used by
`logerr.recipes.dataframes.mongo` is implemented.
"""

from __future__ import annotations

import importlib
import sys
import types
from typing import Any

import pytest

from logerr.recipes.dataframes.mongo import (
    _create_dataframe_from_rows,
    _create_empty_dataframe,
    _create_pandas_dataframe,
    _documents_to_dataframe,
    _execute_mongo_query,
    from_mongo,
    from_mongo_cursor,
)
from logerr.recipes.dataframes.types import FieldSpec, Required

pd = pytest.importorskip("pandas")

pytestmark = [pytest.mark.recipes, pytest.mark.dataframes, pytest.mark.mongo]


class FakeCursor:
    """Minimal stand-in for a pymongo.Cursor."""

    def __init__(self, documents: list[dict[str, Any]], fail_on_iterate: bool = False):
        self._documents = documents
        self._limit: int | None = None
        self._batch_size: int | None = None
        self.fail_on_iterate = fail_on_iterate

    def limit(self, n: int) -> FakeCursor:
        self._limit = n
        return self

    def batch_size(self, n: int) -> FakeCursor:
        self._batch_size = n
        return self

    def __iter__(self):
        if self.fail_on_iterate:
            raise ConnectionError("mongo connection lost")
        docs = self._documents
        if self._limit is not None:
            docs = docs[: self._limit]
        return iter(docs)


class FakeCollection:
    """Minimal stand-in for a pymongo.Collection."""

    def __init__(
        self,
        documents: list[dict[str, Any]],
        name: str = "test_collection",
        fail_on_find: bool = False,
        fail_on_iterate: bool = False,
    ):
        self.documents = documents
        self.name = name
        self.fail_on_find = fail_on_find
        self.fail_on_iterate = fail_on_iterate
        self.last_query: dict[str, Any] | None = None

    def find(self, query: dict[str, Any]) -> FakeCursor:
        self.last_query = query
        if self.fail_on_find:
            raise ConnectionError("could not connect to mongo")
        return FakeCursor(self.documents, fail_on_iterate=self.fail_on_iterate)


class FailingIterable:
    """An iterable that raises when iteration is attempted (for cursor tests)."""

    def __iter__(self):
        raise TimeoutError("cursor timed out")


class TestExecuteMongoQuery:
    """Tests for the internal _execute_mongo_query helper."""

    def test_returns_documents(self):
        collection = FakeCollection([{"a": 1}, {"a": 2}])
        result = _execute_mongo_query(collection, {}, None, 1000)
        assert result == [{"a": 1}, {"a": 2}]

    def test_applies_limit(self):
        collection = FakeCollection([{"a": 1}, {"a": 2}, {"a": 3}])
        result = _execute_mongo_query(collection, {}, 2, 1000)
        assert result == [{"a": 1}, {"a": 2}]

    def test_passes_query_through(self):
        collection = FakeCollection([{"a": 1}])
        _execute_mongo_query(collection, {"status": "active"}, None, 1000)
        assert collection.last_query == {"status": "active"}

    def test_no_batch_size_skips_call(self):
        collection = FakeCollection([{"a": 1}])
        result = _execute_mongo_query(collection, {}, None, 0)
        assert result == [{"a": 1}]


class TestFromMongo:
    """Tests for the top-level from_mongo entry point."""

    def test_successful_query_with_schema(self):
        collection = FakeCollection(
            [{"user_id": "u1", "age": 30}, {"user_id": "u2", "age": 25}]
        )
        schema = {"user_id": Required[str], "age": int}

        result = from_mongo(collection, {}, schema=schema, log_missing_data=False)

        assert result.is_ok()
        df = result.unwrap()
        assert len(df) == 2
        assert list(df["user_id"]) == ["u1", "u2"]

    def test_successful_query_infers_schema(self):
        collection = FakeCollection([{"name": "Alice"}, {"name": "Bob"}])

        result = from_mongo(collection, {}, schema=None, log_missing_data=False)

        assert result.is_ok()
        df = result.unwrap()
        assert "name" in df.columns
        assert len(df) == 2

    def test_query_failure_returns_err(self):
        collection = FakeCollection([], fail_on_find=True)

        result = from_mongo(collection, {})

        assert result.is_err()
        assert isinstance(result.unwrap_err(), ConnectionError)

    def test_empty_results_returns_empty_dataframe(self):
        collection = FakeCollection([])

        result = from_mongo(collection, {}, schema={"name": str})

        assert result.is_ok()
        df = result.unwrap()
        assert len(df) == 0
        assert "name" in df.columns

    def test_empty_results_no_schema_returns_bare_empty_dataframe(self):
        collection = FakeCollection([])

        result = from_mongo(collection, {})

        assert result.is_ok()
        df = result.unwrap()
        assert len(df) == 0

    def test_missing_required_field_document_is_dropped(self):
        collection = FakeCollection(
            [{"user_id": "u1"}, {"other": "value"}]  # second doc missing user_id
        )
        schema = {"user_id": Required[str]}

        result = from_mongo(collection, {}, schema=schema, log_missing_data=False)

        assert result.is_ok()
        df = result.unwrap()
        assert len(df) == 1
        assert df["user_id"].iloc[0] == "u1"

    def test_all_documents_missing_required_field_returns_err(self):
        collection = FakeCollection([{"other": "value"}])
        schema = {"user_id": Required[str]}

        result = from_mongo(collection, {}, schema=schema, log_missing_data=False)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), Exception)

    def test_report_name_defaults_to_collection_name(self):
        collection = FakeCollection([{"a": 1}], name="widgets")
        result = from_mongo(collection, {}, log_missing_data=True)
        assert result.is_ok()

    def test_explicit_report_name_used(self):
        collection = FakeCollection([{"a": 1}], name="widgets")
        result = from_mongo(
            collection, {}, report_name="custom_report", log_missing_data=True
        )
        assert result.is_ok()

    def test_limit_and_batch_size_forwarded(self):
        collection = FakeCollection([{"a": 1}, {"a": 2}, {"a": 3}])
        result = from_mongo(collection, {}, limit=1, batch_size=10)
        assert result.is_ok()
        assert len(result.unwrap()) == 1


class TestFromMongoCursor:
    """Tests for from_mongo_cursor."""

    def test_successful_conversion(self):
        cursor = FakeCursor([{"name": "Alice"}, {"name": "Bob"}])

        result = from_mongo_cursor(cursor, schema={"name": str})

        assert result.is_ok()
        df = result.unwrap()
        assert len(df) == 2

    def test_cursor_iteration_failure_returns_err(self):
        cursor = FailingIterable()

        result = from_mongo_cursor(cursor)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), TimeoutError)

    def test_empty_cursor_returns_empty_dataframe(self):
        cursor = FakeCursor([])

        result = from_mongo_cursor(cursor, schema={"name": str})

        assert result.is_ok()
        assert len(result.unwrap()) == 0

    def test_infers_schema_when_none_provided(self):
        cursor = FakeCursor([{"count": 1}, {"count": 2}])

        result = from_mongo_cursor(cursor, schema=None)

        assert result.is_ok()
        df = result.unwrap()
        assert "count" in df.columns

    def test_plain_list_as_cursor(self):
        # A plain list also satisfies "iterable of documents".
        result = from_mongo_cursor([{"a": 1}], schema={"a": int})
        assert result.is_ok()
        assert len(result.unwrap()) == 1


class TestDocumentsToDataframe:
    """Tests for the internal _documents_to_dataframe helper."""

    def test_no_valid_rows_returns_err(self):
        schema_fields = [FieldSpec(name="user_id", field_type=str, is_required=True)]
        documents = [{"other": 1}, {"other": 2}]

        result = _documents_to_dataframe(
            documents, schema_fields, "pandas", "op", log_missing_data=False
        )

        assert result.is_err()
        assert "No valid rows" in str(result.unwrap_err())

    def test_quality_tracking_disabled_still_converts(self):
        schema_fields = [FieldSpec(name="name", field_type=str, is_required=False)]
        documents = [{"name": "Alice"}]

        result = _documents_to_dataframe(
            documents, schema_fields, "pandas", "op", log_missing_data=False
        )

        assert result.is_ok()
        assert len(result.unwrap()) == 1

    def test_quality_tracking_enabled_reports_high_missing_fields(self):
        schema_fields = [
            FieldSpec(name="user_id", field_type=str, is_required=True),
            FieldSpec(name="nickname", field_type=str, is_required=False),
        ]
        # nickname missing in most documents -> high-missing field logging path
        documents = [
            {"user_id": "u1"},
            {"user_id": "u2"},
            {"user_id": "u3"},
            {"user_id": "u4", "nickname": "bob"},
        ]

        result = _documents_to_dataframe(
            documents, schema_fields, "pandas", "op", log_missing_data=True
        )

        assert result.is_ok()
        assert len(result.unwrap()) == 4

    def test_unsupported_backend_returns_err(self):
        schema_fields = [FieldSpec(name="name", field_type=str, is_required=False)]
        documents = [{"name": "Alice"}]

        result = _documents_to_dataframe(
            documents,
            schema_fields,
            "unsupported_backend",
            "op",
            log_missing_data=False,
        )

        assert result.is_err()
        assert isinstance(result.unwrap_err(), ValueError)

    def test_quality_tracker_records_failed_conversion_reason(self):
        # Mix of one document missing the required field (dropped) and one
        # valid document, with quality tracking enabled, exercises the
        # failed-row error-message extraction branch.
        schema_fields = [FieldSpec(name="user_id", field_type=str, is_required=True)]
        documents = [{"other": "value"}, {"user_id": "u1"}]

        result = _documents_to_dataframe(
            documents, schema_fields, "pandas", "op", log_missing_data=True
        )

        assert result.is_ok()
        df = result.unwrap()
        assert len(df) == 1
        assert df["user_id"].iloc[0] == "u1"


class FakePolarsDataFrame:
    """Minimal stand-in for polars.DataFrame."""

    def __init__(self, data=None, schema=None):
        self.data = data
        self.schema = schema


def _install_fake_polars(monkeypatch) -> None:
    """Inject a minimal fake `polars` module into sys.modules."""
    fake_polars = types.ModuleType("polars")
    fake_polars.DataFrame = FakePolarsDataFrame  # type: ignore[attr-defined]
    for dtype_name in (
        "Utf8",
        "Int64",
        "Float64",
        "Boolean",
        "Datetime",
        "Object",
        "Binary",
    ):
        setattr(fake_polars, dtype_name, dtype_name)
    monkeypatch.setitem(sys.modules, "polars", fake_polars)


class TestCreateDataframeFromRows:
    """Tests for _create_dataframe_from_rows and backend dispatch."""

    def test_pandas_backend(self):
        schema_fields = [FieldSpec(name="name", field_type=str, is_required=False)]
        df = _create_dataframe_from_rows([{"name": "Alice"}], schema_fields, "pandas")
        assert isinstance(df, pd.DataFrame)
        assert list(df["name"]) == ["Alice"]

    def test_unsupported_backend_raises(self):
        with pytest.raises(ValueError, match="Unsupported backend"):
            _create_dataframe_from_rows([], [], "not_a_backend")

    def test_pandas_dtype_conversion_failure_is_logged_not_raised(self):
        # "count" declared as int but the row actually holds an unconvertible
        # object -> astype() failure should be caught and logged, not raised.
        schema_fields = [FieldSpec(name="count", field_type=int, is_required=False)]
        rows = [{"count": {"nested": "dict"}}]

        df = _create_dataframe_from_rows(rows, schema_fields, "pandas")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_polars_backend_missing_dependency_raises_import_error(self):
        # polars is not installed in this environment, so the dispatch to
        # _create_polars_dataframe should surface a clear ImportError.
        with pytest.raises(ImportError, match="polars is required"):
            _create_dataframe_from_rows([{"name": "Alice"}], [], "polars")

    def test_polars_backend_with_rows(self, monkeypatch):
        _install_fake_polars(monkeypatch)
        schema_fields = [FieldSpec(name="name", field_type=str, is_required=False)]

        df = _create_dataframe_from_rows([{"name": "Alice"}], schema_fields, "polars")

        assert isinstance(df, FakePolarsDataFrame)
        assert df.data == [{"name": "Alice"}]

    def test_polars_backend_empty_rows_builds_schema(self, monkeypatch):
        _install_fake_polars(monkeypatch)
        schema_fields = [FieldSpec(name="name", field_type=str, is_required=False)]

        df = _create_dataframe_from_rows([], schema_fields, "polars")

        assert isinstance(df, FakePolarsDataFrame)
        assert df.schema == {"name": "Utf8"}

    def test_pandas_import_error_is_wrapped(self, monkeypatch):
        real_import_module = importlib.import_module

        def fake_import_module(name, *args, **kwargs):
            if name == "pandas":
                raise ImportError("simulated missing pandas")
            return real_import_module(name, *args, **kwargs)

        monkeypatch.setattr(importlib, "import_module", fake_import_module)

        with pytest.raises(ImportError, match="pandas is required"):
            _create_pandas_dataframe([{"a": 1}], [])


class TestCreateEmptyDataframe:
    """Tests for _create_empty_dataframe."""

    def test_no_schema_pandas(self):
        result = _create_empty_dataframe(None, "pandas")
        assert result.is_ok()
        assert isinstance(result.unwrap(), pd.DataFrame)
        assert len(result.unwrap()) == 0

    def test_with_schema_pandas(self):
        result = _create_empty_dataframe({"name": str, "age": int}, "pandas")
        assert result.is_ok()
        df = result.unwrap()
        assert len(df) == 0
        assert set(df.columns) == {"name", "age"}

    def test_with_required_schema_field(self):
        result = _create_empty_dataframe({"user_id": Required[str]}, "pandas")
        assert result.is_ok()
        assert "user_id" in result.unwrap().columns

    def test_no_schema_polars_missing_dependency_returns_err(self):
        # polars is not installed here, so the "no schema" polars branch
        # should surface the ImportError wrapped in an Err via execute().
        result = _create_empty_dataframe(None, "polars")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ImportError)

    def test_no_schema_polars_with_fake_module(self, monkeypatch):
        _install_fake_polars(monkeypatch)
        result = _create_empty_dataframe(None, "polars")
        assert result.is_ok()
        assert isinstance(result.unwrap(), FakePolarsDataFrame)
