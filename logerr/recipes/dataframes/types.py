"""
Type system for dataframes with optional-first design.

Provides Required[T] marker for mandatory fields while treating all other fields
as Optional[T] by default.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime as dt
from typing import Any, Generic, TypeVar, get_args, get_origin

T = TypeVar("T")


class Required(Generic[T]):
    """Marker type for required fields in schema definitions.

    By default, all schema fields are treated as Optional[T]. Use Required[T]
    to mark fields that must be present in the source data.

    Examples:
        >>> schema = {
        ...     "user_id": Required[str],  # Must be present
        ...     "name": str,               # Optional[str] by default
        ...     "age": int,                # Optional[int] by default
        ... }
    """

    def __init__(self, inner_type: type[T]) -> None:
        self.inner_type = inner_type

    def __class_getitem__(cls, item: type[T]) -> Required[T]:
        """Support Required[int] syntax."""
        return cls(item)


@dataclass
class FieldSpec:
    """Specification for a schema field with metadata."""

    name: str
    field_type: type
    is_required: bool
    default_value: Any = None

    @classmethod
    def from_schema_entry(cls, field_name: str, type_spec: Any) -> FieldSpec:
        """Create FieldSpec from schema entry.

        Args:
            field_name: Name of the field
            type_spec: Type specification (Required[T] or T)

        Returns:
            FieldSpec with appropriate metadata
        """
        if isinstance(type_spec, Required):
            return cls(
                name=field_name, field_type=type_spec.inner_type, is_required=True
            )
        elif hasattr(type_spec, "__origin__") and get_origin(type_spec) is Required:
            # Handle Required[T] when used as type annotation
            inner_type = get_args(type_spec)[0]
            return cls(name=field_name, field_type=inner_type, is_required=True)
        else:
            # All other types are optional by default
            return cls(name=field_name, field_type=type_spec, is_required=False)


# Common type mappings for BSON/MongoDB data
BSON_TYPE_MAPPING: dict[type, str] = {
    str: "string",  # Pandas nullable string
    int: "Int64",  # Pandas nullable integer
    float: "Float64",  # Pandas nullable float
    bool: "boolean",  # Pandas nullable boolean
    dt: "datetime64[ns]",
    dict: "object",
    list: "object",
    bytes: "object",
}


# Type validation functions
def is_valid_type_spec(type_spec: Any) -> bool:
    """Check if a type specification is valid for schema definition."""
    if isinstance(type_spec, Required):
        return True
    if hasattr(type_spec, "__origin__") and get_origin(type_spec) is Required:
        return True
    if isinstance(type_spec, type):
        return True
    # Handle generic types like List[str], Dict[str, int], etc.
    if hasattr(type_spec, "__origin__"):
        return True
    return False


def get_pandas_dtype(field_spec: FieldSpec) -> str:
    """Get appropriate pandas dtype for a field specification."""
    base_type = field_spec.field_type

    # Handle Required fields - they can use non-nullable types if desired
    if field_spec.is_required:
        # For required fields, we could use non-nullable types, but let's keep
        # everything nullable for consistency with NoSQL flexibility
        pass

    # Map to pandas nullable types
    return BSON_TYPE_MAPPING.get(base_type, "object")


def get_polars_dtype(field_spec: FieldSpec) -> str:
    """Get appropriate polars dtype for a field specification."""
    base_type = field_spec.field_type

    # Polars type mapping (all types are nullable by default in Polars)
    polars_mapping = {
        str: "Utf8",
        int: "Int64",
        float: "Float64",
        bool: "Boolean",
        dt: "Datetime",
        dict: "Object",
        list: "Object",
        bytes: "Binary",
    }

    return polars_mapping.get(base_type, "Object")
