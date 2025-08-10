"""
logerr.recipes.dataframes: NoSQL data to DataFrame conversion with robust error handling.

This module provides utilities for safely converting NoSQL data (especially MongoDB)
to pandas/polars DataFrames with built-in data quality logging and nullable type handling.

Key Features:
- Optional-first schema design (all fields nullable by default)
- Required[T] marker for mandatory fields
- Automatic data quality logging and reporting
- Type-safe conversions with error handling
- Integration with logerr's logging system

Usage:
    from logerr.recipes.dataframes import Required, from_mongo

    schema = {
        "user_id": Required[str],  # Must be present
        "email": Required[str],    # Must be present
        "name": str,              # Optional by default
        "age": int,               # Optional by default
    }

    result = from_mongo(db.users, {}, schema=schema, log_missing_data=True)
    df = result.unwrap_or_default()
"""

from .conversion import convert_bson_value, infer_schema_from_documents
from .mongo import from_mongo, from_mongo_cursor
from .quality import DataQualityReport, generate_quality_report
from .types import Required

__all__ = [
    "Required",
    "from_mongo",
    "from_mongo_cursor",
    "DataQualityReport",
    "generate_quality_report",
    "convert_bson_value",
    "infer_schema_from_documents",
]
