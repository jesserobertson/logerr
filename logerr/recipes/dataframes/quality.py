"""
Data quality reporting and logging integration.

Provides comprehensive data quality analysis and logging for DataFrame creation
from NoSQL sources, with detailed reports on missing fields, type conversion
issues, and overall data health.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from ...utils import log
from .types import FieldSpec


@dataclass
class FieldQualityMetrics:
    """Quality metrics for a single field."""

    field_name: str
    total_records: int
    present_records: int
    missing_records: int
    type_conversion_errors: int = 0
    invalid_values: list[Any] = field(default_factory=list)

    @property
    def presence_rate(self) -> float:
        """Percentage of records where this field is present."""
        if self.total_records == 0:
            return 0.0
        return (self.present_records / self.total_records) * 100

    @property
    def missing_rate(self) -> float:
        """Percentage of records where this field is missing."""
        return 100.0 - self.presence_rate

    @property
    def conversion_error_rate(self) -> float:
        """Percentage of present records that failed type conversion."""
        if self.present_records == 0:
            return 0.0
        return (self.type_conversion_errors / self.present_records) * 100


@dataclass
class DataQualityReport:
    """Comprehensive data quality report for a DataFrame creation operation."""

    operation_name: str
    total_records_processed: int
    successful_records: int
    failed_records: int
    field_metrics: dict[str, FieldQualityMetrics] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Percentage of records successfully converted to DataFrame."""
        if self.total_records_processed == 0:
            return 0.0
        return (self.successful_records / self.total_records_processed) * 100

    def add_field_metrics(self, field_name: str, metrics: FieldQualityMetrics) -> None:
        """Add metrics for a specific field."""
        self.field_metrics[field_name] = metrics

    def get_required_field_violations(self) -> list[str]:
        """Get list of required fields that had missing data."""
        violations = []
        for field_name, metrics in self.field_metrics.items():
            if metrics.missing_records > 0:
                # We'll need to track which fields are required separately
                violations.append(field_name)
        return violations

    def get_high_missing_fields(self, threshold: float = 20.0) -> list[str]:
        """Get fields with missing rates above threshold percentage."""
        high_missing = []
        for field_name, metrics in self.field_metrics.items():
            if metrics.missing_rate > threshold:
                high_missing.append(field_name)
        return high_missing

    def log_summary(self, log_level: str = "INFO") -> None:
        """Log a comprehensive summary of data quality."""
        log(
            f"Data Quality Summary for '{self.operation_name}': "
            f"{self.successful_records}/{self.total_records_processed} records processed successfully "
            f"({self.success_rate:.1f}% success rate)",
            log_level=log_level,
        )

        # Log field-level issues
        for field_name, metrics in self.field_metrics.items():
            if metrics.missing_rate > 0:
                level = "ERROR" if metrics.missing_rate > 50 else "WARNING"
                log(
                    f"Field '{field_name}': {metrics.missing_records}/{metrics.total_records} "
                    f"missing ({metrics.missing_rate:.1f}% missing rate)",
                    log_level=level,
                    extra_context={
                        "field": field_name,
                        "missing_rate": metrics.missing_rate,
                    },
                )

            if metrics.type_conversion_errors > 0:
                log(
                    f"Field '{field_name}': {metrics.type_conversion_errors} type conversion errors "
                    f"({metrics.conversion_error_rate:.1f}% of present values)",
                    log_level="WARNING",
                    extra_context={
                        "field": field_name,
                        "conversion_errors": metrics.type_conversion_errors,
                        "invalid_values": metrics.invalid_values[
                            :5
                        ],  # First 5 examples
                    },
                )


class DataQualityTracker:
    """Track data quality metrics during DataFrame creation."""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.total_records = 0
        self.successful_records = 0
        self.failed_records = 0
        self.field_presence: dict[str, int] = defaultdict(int)
        self.field_conversion_errors: dict[str, int] = defaultdict(int)
        self.field_invalid_values: dict[str, list[Any]] = defaultdict(list)
        self.required_fields: set[str] = set()

    def set_required_fields(self, fields: set[str]) -> None:
        """Set which fields are required for quality reporting."""
        self.required_fields = fields

    def record_document(self, document: dict[str, Any]) -> None:
        """Record metrics for a single document."""
        self.total_records += 1

        # Track field presence
        for field_name in document:
            if document[field_name] is not None:
                self.field_presence[field_name] += 1

    def record_successful_conversion(self) -> None:
        """Record a successful document conversion."""
        self.successful_records += 1

    def record_failed_conversion(self, reason: str = "unknown") -> None:
        """Record a failed document conversion."""
        self.failed_records += 1
        log(
            f"Failed to convert document: {reason}",
            log_level="DEBUG",
            extra_context={"operation": self.operation_name},
        )

    def record_conversion_error(
        self, field_name: str, invalid_value: Any, error: Exception
    ) -> None:
        """Record a type conversion error for a specific field."""
        self.field_conversion_errors[field_name] += 1
        if len(self.field_invalid_values[field_name]) < 10:  # Keep first 10 examples
            self.field_invalid_values[field_name].append(invalid_value)

        log(
            f"Type conversion error for field '{field_name}': {error}",
            log_level="DEBUG",
            extra_context={
                "field": field_name,
                "invalid_value": str(invalid_value)[:100],  # Truncate long values
                "error_type": type(error).__name__,
            },
        )

    def record_missing_required_field(
        self, field_name: str, document_id: Any = None
    ) -> None:
        """Record a missing required field violation."""
        log(
            f"Missing required field '{field_name}' in document",
            log_level="ERROR",
            extra_context={
                "field": field_name,
                "document_id": document_id,
                "operation": self.operation_name,
            },
        )

    def generate_report(self) -> DataQualityReport:
        """Generate comprehensive data quality report."""
        report = DataQualityReport(
            operation_name=self.operation_name,
            total_records_processed=self.total_records,
            successful_records=self.successful_records,
            failed_records=self.failed_records,
        )

        # Calculate metrics for each field we've seen
        all_fields = set(self.field_presence.keys()) | set(
            self.field_conversion_errors.keys()
        )

        for field_name in all_fields:
            present_count = self.field_presence.get(field_name, 0)
            missing_count = self.total_records - present_count
            conversion_errors = self.field_conversion_errors.get(field_name, 0)
            invalid_values = self.field_invalid_values.get(field_name, [])

            metrics = FieldQualityMetrics(
                field_name=field_name,
                total_records=self.total_records,
                present_records=present_count,
                missing_records=missing_count,
                type_conversion_errors=conversion_errors,
                invalid_values=invalid_values,
            )

            report.add_field_metrics(field_name, metrics)

        return report


def generate_quality_report(
    documents: list[dict[str, Any]],
    schema_fields: list[FieldSpec],
    operation_name: str = "dataframe_conversion",
) -> DataQualityReport:
    """Generate a data quality report for a collection of documents.

    Args:
        documents: List of documents to analyze
        schema_fields: Expected schema specification
        operation_name: Name for this operation (used in logging)

    Returns:
        Comprehensive data quality report
    """
    tracker = DataQualityTracker(operation_name)

    # Set required fields
    required_fields = {spec.name for spec in schema_fields if spec.is_required}
    tracker.set_required_fields(required_fields)

    # Analyze each document
    for doc in documents:
        tracker.record_document(doc)

        # Check for missing required fields
        has_all_required = True
        for field_name in required_fields:
            if field_name not in doc or doc[field_name] is None:
                tracker.record_missing_required_field(field_name, doc.get("_id"))
                has_all_required = False

        if has_all_required:
            tracker.record_successful_conversion()
        else:
            tracker.record_failed_conversion("missing required fields")

    return tracker.generate_report()
