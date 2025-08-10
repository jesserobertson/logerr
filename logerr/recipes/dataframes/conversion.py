"""
Type conversion utilities for BSON/NoSQL data to DataFrame types.

Handles safe conversion of MongoDB BSON values to appropriate DataFrame types
with comprehensive error handling and Option integration.
"""

from __future__ import annotations

import re
from datetime import datetime as dt
from typing import Any

from ...option import Nothing, Option, Some
from ...result import Err, Ok, Result
from .quality import DataQualityTracker
from .types import FieldSpec


def convert_bson_value(
    value: Any,
    target_type: type,
    field_name: str,
    quality_tracker: DataQualityTracker | None = None,
) -> Option[Any]:
    """Convert a BSON value to the target type with error handling.

    Args:
        value: Raw value from MongoDB/BSON
        target_type: Target Python type
        field_name: Name of the field (for error reporting)
        quality_tracker: Optional tracker for recording conversion issues

    Returns:
        Some(converted_value) if successful, Nothing if conversion failed
    """
    if value is None:
        return Nothing.from_none(f"Field '{field_name}' is None")

    try:
        # Handle different target types
        if target_type is str:
            return Some(str(value))

        elif target_type is int:
            if isinstance(value, int):
                return Some(value)
            elif isinstance(value, float) and value.is_integer():
                return Some(int(value))
            elif isinstance(value, str):
                # Try to parse string as integer
                cleaned = value.strip()
                if cleaned:
                    return Some(int(cleaned))
                else:
                    raise ValueError("Empty string")
            else:
                return Some(int(value))  # Let int() handle conversion

        elif target_type is float:
            if isinstance(value, int | float):
                return Some(float(value))
            elif isinstance(value, str):
                cleaned = value.strip()
                if cleaned:
                    return Some(float(cleaned))
                else:
                    raise ValueError("Empty string")
            else:
                return Some(float(value))

        elif target_type is bool:
            if isinstance(value, bool):
                return Some(value)
            elif isinstance(value, int):
                return Some(bool(value))
            elif isinstance(value, str):
                lower_val = value.lower().strip()
                if lower_val in ("true", "yes", "1", "on"):
                    return Some(True)
                elif lower_val in ("false", "no", "0", "off", ""):
                    return Some(False)
                else:
                    raise ValueError(f"Cannot convert '{value}' to boolean")
            else:
                return Some(bool(value))

        elif target_type is dt:
            if isinstance(value, dt):
                return Some(value)
            elif isinstance(value, str):
                # Try common datetime formats
                for fmt in [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M:%SZ",
                    "%Y-%m-%d %H:%M:%S.%f",
                ]:
                    try:
                        return Some(dt.strptime(value, fmt))
                    except ValueError:
                        continue
                raise ValueError(f"Cannot parse datetime: {value}")
            else:
                # For other types, try conversion if it's a timestamp
                if isinstance(value, int | float):
                    return Some(dt.fromtimestamp(value))
                else:
                    raise ValueError(
                        f"Cannot convert {type(value).__name__} to datetime"
                    )

        elif target_type in (dict, list):
            # For complex types, return as-is if they match, otherwise convert
            if isinstance(value, target_type):
                return Some(value)
            else:
                return Some(target_type(value))

        else:
            # For other types, try direct conversion
            return Some(target_type(value))

    except (ValueError, TypeError, OverflowError) as e:
        # Record conversion error if tracker is provided
        if quality_tracker:
            quality_tracker.record_conversion_error(field_name, value, e)

        return Nothing.from_exception(e)


def infer_schema_from_documents(
    documents: list[dict[str, Any]], sample_size: int | None = None
) -> dict[str, type]:
    """Infer schema from a collection of MongoDB documents.

    Args:
        documents: List of documents to analyze
        sample_size: Maximum number of documents to sample (None for all)

    Returns:
        Dictionary mapping field names to inferred types
    """
    if not documents:
        return {}

    # Sample documents if requested
    sample = documents[:sample_size] if sample_size else documents

    # Track field types across all documents
    field_types: dict[str, dict[type, int]] = {}

    for doc in sample:
        for field_name, value in doc.items():
            if field_name not in field_types:
                field_types[field_name] = {}

            value_type = type(value)
            field_types[field_name][value_type] = (
                field_types[field_name].get(value_type, 0) + 1
            )

    # Determine most common type for each field
    inferred_schema: dict[str, type] = {}
    for field_name, type_counts in field_types.items():
        # Get the most common type
        most_common_type = max(type_counts.items(), key=lambda x: x[1])[0]

        # Handle type normalization
        if most_common_type in (int, float):
            # If we see both int and float, prefer float
            if int in type_counts and float in type_counts:
                inferred_schema[field_name] = float
            else:
                inferred_schema[field_name] = most_common_type
        else:
            inferred_schema[field_name] = most_common_type

    return inferred_schema


def convert_document_to_row(
    document: dict[str, Any],
    schema_fields: list[FieldSpec],
    quality_tracker: DataQualityTracker | None = None,
) -> Result[dict[str, Any], str]:
    """Convert a MongoDB document to a DataFrame row with type conversion.

    Args:
        document: MongoDB document
        schema_fields: List of field specifications
        quality_tracker: Optional quality tracker

    Returns:
        Ok(row_dict) if successful, Err(error_message) if failed
    """
    row = {}
    missing_required_fields = []

    for field_spec in schema_fields:
        field_name = field_spec.name

        if field_name in document:
            # Convert the value
            converted = convert_bson_value(
                document[field_name], field_spec.field_type, field_name, quality_tracker
            )

            if converted.is_some():
                row[field_name] = converted.unwrap()
            else:
                # Conversion failed - use None for optional fields
                if field_spec.is_required:
                    missing_required_fields.append(field_name)
                else:
                    row[field_name] = None
        else:
            # Field is missing
            if field_spec.is_required:
                missing_required_fields.append(field_name)
                if quality_tracker:
                    quality_tracker.record_missing_required_field(
                        field_name, document.get("_id")
                    )
            else:
                row[field_name] = None

    if missing_required_fields:
        error_msg = f"Missing required fields: {missing_required_fields}"
        return Err.from_value(error_msg)

    return Ok(row)


def normalize_field_name(name: str) -> str:
    """Normalize MongoDB field names for DataFrame compatibility.

    Args:
        name: Original field name

    Returns:
        Normalized field name safe for DataFrame columns
    """
    # Replace problematic characters
    normalized = re.sub(r"[^\w]", "_", name)

    # Ensure it doesn't start with a number
    if normalized and normalized[0].isdigit():
        normalized = f"field_{normalized}"

    # Handle empty names
    if not normalized:
        normalized = "unnamed_field"

    return normalized


def prepare_dataframe_dtypes(schema_fields: list[FieldSpec]) -> dict[str, str]:
    """Prepare dtype dictionary for DataFrame creation.

    Args:
        schema_fields: List of field specifications

    Returns:
        Dictionary mapping field names to pandas dtypes
    """
    from .types import get_pandas_dtype

    dtypes = {}
    for field_spec in schema_fields:
        pandas_dtype = get_pandas_dtype(field_spec)
        dtypes[field_spec.name] = pandas_dtype

    return dtypes
