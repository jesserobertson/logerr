"""
MongoDB integration for safe DataFrame creation.

Provides utilities for querying MongoDB collections and converting results
to pandas/polars DataFrames with comprehensive error handling and data quality reporting.
"""

from __future__ import annotations

import importlib
from typing import Any, Literal

from ...result import Err, Result
from ...utils import execute, log
from .conversion import (
    convert_document_to_row,
    infer_schema_from_documents,
    prepare_dataframe_dtypes,
)
from .quality import DataQualityTracker
from .types import FieldSpec


def from_mongo(
    collection: Any,  # pymongo.Collection
    query: dict[str, Any],
    schema: dict[str, Any] | None = None,
    backend: Literal["pandas"] = "pandas",  # TODO: Add polars support
    log_missing_data: bool = True,
    report_name: str | None = None,
    limit: int | None = None,
    batch_size: int = 1000,
) -> Result[Any, Exception]:  # Returns DataFrame
    """Query MongoDB collection and create DataFrame with data quality logging.

    Args:
        collection: PyMongo collection object
        query: MongoDB query dictionary
        schema: Schema specification with Required[T] for mandatory fields
        backend: DataFrame backend ("pandas" or "polars")
        log_missing_data: Whether to log data quality issues
        report_name: Name for data quality report (defaults to collection name)
        limit: Maximum number of documents to retrieve
        batch_size: Batch size for cursor iteration

    Returns:
        Ok(dataframe) if successful, Err(exception) if failed

    Examples:
        >>> from logerr.recipes.dataframes import Required, from_mongo
        >>> # Schema with required and optional fields
        >>> schema = {
        ...     "user_id": Required[str],  # Must be present
        ...     "name": str,              # Optional by default
        ...     "age": int,               # Optional by default
        ... }
        >>> # Example usage (requires actual MongoDB collection):
        >>> # result = from_mongo(db.users, {"status": "active"}, schema=schema)
        >>> # df = result.unwrap_or_default()
    """
    # Set up operation name for logging
    operation_name = report_name or getattr(collection, "name", "mongo_query")

    # Execute the query safely
    query_result = execute(
        lambda: _execute_mongo_query(collection, query, limit, batch_size)
    )

    if query_result.is_err():
        log(
            f"MongoDB query failed for collection '{operation_name}': {query_result.unwrap_err()}",
            log_level="ERROR",
            extra_context={"collection": operation_name, "query": str(query)[:200]},
        )
        return query_result  # type: ignore[no-any-return]

    documents = query_result.unwrap()

    if not documents:
        log(
            f"No documents found in collection '{operation_name}' for query",
            log_level="WARNING",
            extra_context={"collection": operation_name, "query": str(query)[:200]},
        )
        # Return empty DataFrame
        return _create_empty_dataframe(schema, backend)

    # Process schema or infer it
    if schema:
        schema_fields = [
            FieldSpec.from_schema_entry(name, type_spec)
            for name, type_spec in schema.items()
        ]
    else:
        # Infer schema from documents
        inferred_schema = infer_schema_from_documents(documents)
        schema_fields = [
            FieldSpec.from_schema_entry(name, type_spec)
            for name, type_spec in inferred_schema.items()
        ]

        if log_missing_data:
            log(
                f"No schema provided for '{operation_name}', inferred {len(schema_fields)} fields",
                log_level="INFO",
                extra_context={"inferred_fields": list(inferred_schema.keys())},
            )

    # Convert documents to DataFrame
    return _documents_to_dataframe(
        documents, schema_fields, backend, str(operation_name), log_missing_data
    )


def from_mongo_cursor(
    cursor: Any,  # pymongo.Cursor
    schema: dict[str, Any] | None = None,
    backend: Literal["pandas"] = "pandas",
    log_missing_data: bool = True,
    report_name: str = "cursor_conversion",
    batch_size: int = 1000,
) -> Result[Any, Exception]:  # Returns DataFrame
    """Convert MongoDB cursor to DataFrame with data quality logging.

    Args:
        cursor: PyMongo cursor object
        schema: Schema specification with Required[T] for mandatory fields
        backend: DataFrame backend ("pandas" or "polars")
        log_missing_data: Whether to log data quality issues
        report_name: Name for data quality report
        batch_size: Batch size for cursor iteration

    Returns:
        Ok(dataframe) if successful, Err(exception) if failed
    """
    # Execute cursor iteration safely
    documents_result = execute(lambda: list(cursor))

    if documents_result.is_err():
        log(
            f"Failed to iterate MongoDB cursor: {documents_result.unwrap_err()}",
            log_level="ERROR",
            extra_context={"operation": report_name},
        )
        return documents_result  # type: ignore[no-any-return]

    documents = documents_result.unwrap()

    if not documents:
        log(f"No documents found in cursor for '{report_name}'", log_level="WARNING")
        return _create_empty_dataframe(schema, backend)

    # Process schema
    if schema:
        schema_fields = [
            FieldSpec.from_schema_entry(name, type_spec)
            for name, type_spec in schema.items()
        ]
    else:
        inferred_schema = infer_schema_from_documents(documents)
        schema_fields = [
            FieldSpec.from_schema_entry(name, type_spec)
            for name, type_spec in inferred_schema.items()
        ]

    # Convert to DataFrame
    return _documents_to_dataframe(
        documents, schema_fields, backend, report_name, log_missing_data
    )


def _execute_mongo_query(
    collection: Any, query: dict[str, Any], limit: int | None, batch_size: int
) -> list[dict[str, Any]]:
    """Execute MongoDB query and return documents."""
    cursor = collection.find(query)

    if limit:
        cursor = cursor.limit(limit)

    if batch_size:
        cursor = cursor.batch_size(batch_size)

    return list(cursor)


def _documents_to_dataframe(
    documents: list[dict[str, Any]],
    schema_fields: list[FieldSpec],
    backend: str,
    operation_name: str,
    log_missing_data: bool,
) -> Result[Any, Exception]:
    """Convert documents to DataFrame with quality tracking."""
    quality_tracker = DataQualityTracker(operation_name) if log_missing_data else None

    # Set required fields for quality tracking
    if quality_tracker:
        required_fields = {spec.name for spec in schema_fields if spec.is_required}
        quality_tracker.set_required_fields(required_fields)

    # Convert each document to a row
    successful_rows = []

    for doc in documents:
        if quality_tracker:
            quality_tracker.record_document(doc)

        row_result = convert_document_to_row(doc, schema_fields, quality_tracker)

        if row_result.is_ok():
            successful_rows.append(row_result.unwrap())
            if quality_tracker:
                quality_tracker.record_successful_conversion()
        else:
            if quality_tracker:
                # Work around mypy issue with unwrap_err on Result[T, str]
                error_msg = (
                    str(row_result).replace("Err(", "").replace(")", "")
                    if "Err(" in str(row_result)
                    else "unknown error"
                )
                quality_tracker.record_failed_conversion(error_msg)
            # Skip failed rows rather than failing entire operation

    if not successful_rows:
        error_msg = f"No valid rows could be created from {len(documents)} documents"
        log(error_msg, log_level="ERROR", extra_context={"operation": operation_name})
        return Err.from_value(Exception(error_msg))

    # Create DataFrame
    dataframe_result = execute(
        lambda: _create_dataframe_from_rows(successful_rows, schema_fields, backend)
    )

    # Generate quality report if tracking enabled
    if quality_tracker and log_missing_data:
        quality_report = quality_tracker.generate_report()
        quality_report.log_summary()

        # Log specific issues
        high_missing_fields = quality_report.get_high_missing_fields(20.0)
        if high_missing_fields:
            log(
                f"Fields with high missing rates (>20%): {high_missing_fields}",
                log_level="WARNING",
                extra_context={
                    "operation": operation_name,
                    "high_missing_fields": high_missing_fields,
                },
            )

    return dataframe_result  # type: ignore[no-any-return]


def _create_dataframe_from_rows(
    rows: list[dict[str, Any]], schema_fields: list[FieldSpec], backend: str
) -> Any:  # DataFrame
    """Create DataFrame from processed rows."""
    if backend == "pandas":
        return _create_pandas_dataframe(rows, schema_fields)
    elif backend == "polars":
        return _create_polars_dataframe(rows, schema_fields)
    else:
        raise ValueError(f"Unsupported backend: {backend}")


def _create_pandas_dataframe(
    rows: list[dict[str, Any]], schema_fields: list[FieldSpec]
) -> Any:
    """Create pandas DataFrame with appropriate nullable types."""
    try:
        pd = importlib.import_module("pandas")
    except ImportError as e:
        raise ImportError(
            "pandas is required for pandas backend. Install with: pip install pandas"
        ) from e

    if not rows:
        # Create empty DataFrame with correct schema
        dtypes = prepare_dataframe_dtypes(schema_fields)
        return pd.DataFrame(columns=list(dtypes.keys())).astype(dtypes)

    # Create DataFrame from rows
    df = pd.DataFrame(rows)

    # Apply type conversions for better nullable type support
    dtypes = prepare_dataframe_dtypes(schema_fields)

    for field_name, dtype in dtypes.items():
        if field_name in df.columns:
            try:
                df[field_name] = df[field_name].astype(dtype)
            except (ValueError, TypeError) as e:
                # Log conversion warning but continue
                log(
                    f"Could not convert column '{field_name}' to {dtype}: {e}",
                    log_level="WARNING",
                    extra_context={"column": field_name, "target_dtype": dtype},
                )

    return df


def _create_polars_dataframe(
    rows: list[dict[str, Any]], schema_fields: list[FieldSpec]
) -> Any:
    """Create polars DataFrame with appropriate nullable types."""
    try:
        pl = importlib.import_module("polars")
    except ImportError as e:
        raise ImportError(
            "polars is required for polars backend. Install with: pip install polars"
        ) from e

    if not rows:
        # Create empty DataFrame with correct schema
        from .types import get_polars_dtype

        schema = {
            spec.name: getattr(pl, get_polars_dtype(spec)) for spec in schema_fields
        }
        return pl.DataFrame([], schema=schema)

    # Create DataFrame from rows - polars handles nullable types automatically
    return pl.DataFrame(rows)


def _create_empty_dataframe(
    schema: dict[str, Any] | None, backend: str
) -> Result[Any, Exception]:
    """Create empty DataFrame with correct schema."""
    if not schema:
        # Create completely empty DataFrame
        if backend == "pandas":
            return execute(lambda: importlib.import_module("pandas").DataFrame())  # type: ignore[no-any-return]
        else:
            return execute(lambda: importlib.import_module("polars").DataFrame())  # type: ignore[no-any-return]

    schema_fields = [
        FieldSpec.from_schema_entry(name, type_spec)
        for name, type_spec in schema.items()
    ]

    return execute(lambda: _create_dataframe_from_rows([], schema_fields, backend))  # type: ignore[no-any-return]
