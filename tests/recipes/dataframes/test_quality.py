"""
Tests for logerr.recipes.dataframes.quality module.
"""

import pytest

from logerr.recipes.dataframes.quality import (
    DataQualityReport,
    DataQualityTracker,
    FieldQualityMetrics,
    generate_quality_report,
)
from logerr.recipes.dataframes.types import FieldSpec

pytestmark = [pytest.mark.recipes, pytest.mark.dataframes]


class TestFieldQualityMetrics:
    """Tests for the FieldQualityMetrics dataclass properties."""

    def test_presence_rate(self):
        metrics = FieldQualityMetrics(
            field_name="name", total_records=10, present_records=8, missing_records=2
        )
        assert metrics.presence_rate == 80.0

    def test_missing_rate(self):
        metrics = FieldQualityMetrics(
            field_name="name", total_records=10, present_records=8, missing_records=2
        )
        assert metrics.missing_rate == 20.0

    def test_presence_and_missing_rate_zero_total_records(self):
        metrics = FieldQualityMetrics(
            field_name="name", total_records=0, present_records=0, missing_records=0
        )
        assert metrics.presence_rate == 0.0
        assert metrics.missing_rate == 100.0

    def test_conversion_error_rate(self):
        metrics = FieldQualityMetrics(
            field_name="count",
            total_records=10,
            present_records=10,
            missing_records=0,
            type_conversion_errors=2,
        )
        assert metrics.conversion_error_rate == 20.0

    def test_conversion_error_rate_zero_present_records(self):
        metrics = FieldQualityMetrics(
            field_name="count", total_records=0, present_records=0, missing_records=0
        )
        assert metrics.conversion_error_rate == 0.0

    def test_default_invalid_values_empty(self):
        metrics = FieldQualityMetrics(
            field_name="x", total_records=1, present_records=1, missing_records=0
        )
        assert metrics.invalid_values == []

    def test_invalid_values_independent_between_instances(self):
        # Guards against shared mutable default (field(default_factory=list))
        m1 = FieldQualityMetrics(
            field_name="a", total_records=1, present_records=1, missing_records=0
        )
        m2 = FieldQualityMetrics(
            field_name="b", total_records=1, present_records=1, missing_records=0
        )
        m1.invalid_values.append("oops")
        assert m2.invalid_values == []


class TestDataQualityReport:
    """Tests for the DataQualityReport dataclass."""

    def test_success_rate(self):
        report = DataQualityReport(
            operation_name="op",
            total_records_processed=10,
            successful_records=7,
            failed_records=3,
        )
        assert report.success_rate == 70.0

    def test_success_rate_zero_total(self):
        report = DataQualityReport(
            operation_name="op",
            total_records_processed=0,
            successful_records=0,
            failed_records=0,
        )
        assert report.success_rate == 0.0

    def test_add_field_metrics(self):
        report = DataQualityReport(
            operation_name="op",
            total_records_processed=1,
            successful_records=1,
            failed_records=0,
        )
        metrics = FieldQualityMetrics(
            field_name="name", total_records=1, present_records=1, missing_records=0
        )
        report.add_field_metrics("name", metrics)
        assert report.field_metrics["name"] is metrics

    def test_get_required_field_violations(self):
        report = DataQualityReport(
            operation_name="op",
            total_records_processed=2,
            successful_records=1,
            failed_records=1,
        )
        report.add_field_metrics(
            "name",
            FieldQualityMetrics(
                field_name="name", total_records=2, present_records=2, missing_records=0
            ),
        )
        report.add_field_metrics(
            "email",
            FieldQualityMetrics(
                field_name="email",
                total_records=2,
                present_records=1,
                missing_records=1,
            ),
        )
        violations = report.get_required_field_violations()
        assert violations == ["email"]

    def test_get_high_missing_fields_default_threshold(self):
        report = DataQualityReport(
            operation_name="op",
            total_records_processed=10,
            successful_records=10,
            failed_records=0,
        )
        report.add_field_metrics(
            "rarely_present",
            FieldQualityMetrics(
                field_name="rarely_present",
                total_records=10,
                present_records=1,
                missing_records=9,
            ),
        )
        report.add_field_metrics(
            "usually_present",
            FieldQualityMetrics(
                field_name="usually_present",
                total_records=10,
                present_records=9,
                missing_records=1,
            ),
        )
        high_missing = report.get_high_missing_fields()
        assert high_missing == ["rarely_present"]

    def test_get_high_missing_fields_custom_threshold(self):
        report = DataQualityReport(
            operation_name="op",
            total_records_processed=10,
            successful_records=10,
            failed_records=0,
        )
        report.add_field_metrics(
            "field_a",
            FieldQualityMetrics(
                field_name="field_a",
                total_records=10,
                present_records=9,
                missing_records=1,
            ),
        )
        # 10% missing rate exceeds a 5% threshold but not the default 20%
        assert report.get_high_missing_fields(threshold=5.0) == ["field_a"]
        assert report.get_high_missing_fields(threshold=20.0) == []

    def test_log_summary_runs_without_error(self):
        report = DataQualityReport(
            operation_name="op",
            total_records_processed=10,
            successful_records=8,
            failed_records=2,
        )
        report.add_field_metrics(
            "name",
            FieldQualityMetrics(
                field_name="name",
                total_records=10,
                present_records=4,
                missing_records=6,
                type_conversion_errors=2,
                invalid_values=["bad1", "bad2"],
            ),
        )
        # Should not raise regardless of log level branching (>50% -> ERROR).
        report.log_summary()

    def test_log_summary_warning_branch(self):
        report = DataQualityReport(
            operation_name="op",
            total_records_processed=10,
            successful_records=9,
            failed_records=1,
        )
        report.add_field_metrics(
            "name",
            FieldQualityMetrics(
                field_name="name",
                total_records=10,
                present_records=9,
                missing_records=1,
            ),
        )
        report.log_summary(log_level="INFO")


class TestDataQualityTracker:
    """Tests for the DataQualityTracker class."""

    def test_initial_state(self):
        tracker = DataQualityTracker("my_op")
        assert tracker.operation_name == "my_op"
        assert tracker.total_records == 0
        assert tracker.successful_records == 0
        assert tracker.failed_records == 0
        assert tracker.required_fields == set()

    def test_set_required_fields(self):
        tracker = DataQualityTracker("op")
        tracker.set_required_fields({"a", "b"})
        assert tracker.required_fields == {"a", "b"}

    def test_record_document_counts_total(self):
        tracker = DataQualityTracker("op")
        tracker.record_document({"a": 1})
        tracker.record_document({"a": 2})
        assert tracker.total_records == 2

    def test_record_document_tracks_field_presence(self):
        tracker = DataQualityTracker("op")
        tracker.record_document({"a": 1, "b": None})
        assert tracker.field_presence["a"] == 1
        # None values are not counted as present
        assert tracker.field_presence["b"] == 0

    def test_record_document_field_presence_accumulates(self):
        tracker = DataQualityTracker("op")
        tracker.record_document({"a": 1})
        tracker.record_document({"a": 2})
        tracker.record_document({"a": None})
        assert tracker.field_presence["a"] == 2

    def test_record_document_missing_field_not_counted(self):
        tracker = DataQualityTracker("op")
        tracker.record_document({"a": 1})
        tracker.record_document({"b": 1})
        assert tracker.field_presence["a"] == 1
        assert tracker.field_presence["b"] == 1

    def test_record_successful_conversion(self):
        tracker = DataQualityTracker("op")
        tracker.record_successful_conversion()
        tracker.record_successful_conversion()
        assert tracker.successful_records == 2

    def test_record_failed_conversion(self):
        tracker = DataQualityTracker("op")
        tracker.record_failed_conversion("bad data")
        assert tracker.failed_records == 1

    def test_record_failed_conversion_default_reason(self):
        tracker = DataQualityTracker("op")
        tracker.record_failed_conversion()
        assert tracker.failed_records == 1

    def test_record_conversion_error_accumulates_count(self):
        tracker = DataQualityTracker("op")
        tracker.record_conversion_error("age", "bad", ValueError("bad value"))
        tracker.record_conversion_error("age", "worse", ValueError("bad value"))
        assert tracker.field_conversion_errors["age"] == 2

    def test_record_conversion_error_tracks_invalid_values(self):
        tracker = DataQualityTracker("op")
        tracker.record_conversion_error("age", "bad", ValueError("x"))
        assert tracker.field_invalid_values["age"] == ["bad"]

    def test_record_conversion_error_caps_invalid_values_at_ten(self):
        tracker = DataQualityTracker("op")
        for i in range(15):
            tracker.record_conversion_error("age", f"bad{i}", ValueError("x"))
        assert tracker.field_conversion_errors["age"] == 15
        assert len(tracker.field_invalid_values["age"]) == 10
        assert tracker.field_invalid_values["age"][0] == "bad0"
        assert tracker.field_invalid_values["age"][-1] == "bad9"

    def test_record_missing_required_field_does_not_raise(self):
        tracker = DataQualityTracker("op")
        tracker.record_missing_required_field("user_id", document_id="abc123")
        tracker.record_missing_required_field("user_id")

    def test_generate_report_basic_counts(self):
        tracker = DataQualityTracker("op")
        tracker.record_document({"name": "Alice"})
        tracker.record_document({"name": "Bob"})
        tracker.record_successful_conversion()
        tracker.record_successful_conversion()

        report = tracker.generate_report()

        assert report.operation_name == "op"
        assert report.total_records_processed == 2
        assert report.successful_records == 2
        assert report.failed_records == 0
        assert report.success_rate == 100.0

    def test_generate_report_field_metrics_present_and_missing(self):
        tracker = DataQualityTracker("op")
        tracker.record_document({"name": "Alice", "age": 30})
        tracker.record_document({"name": "Bob"})  # missing age
        tracker.record_document({"name": None, "age": 40})  # missing name (None)

        report = tracker.generate_report()

        name_metrics = report.field_metrics["name"]
        assert name_metrics.total_records == 3
        assert name_metrics.present_records == 2
        assert name_metrics.missing_records == 1

        age_metrics = report.field_metrics["age"]
        assert age_metrics.total_records == 3
        assert age_metrics.present_records == 2
        assert age_metrics.missing_records == 1

    def test_generate_report_includes_conversion_error_fields(self):
        tracker = DataQualityTracker("op")
        tracker.record_document({"count": "bad"})
        tracker.record_conversion_error("count", "bad", ValueError("x"))

        report = tracker.generate_report()

        count_metrics = report.field_metrics["count"]
        assert count_metrics.type_conversion_errors == 1
        assert count_metrics.invalid_values == ["bad"]

    def test_generate_report_field_with_only_conversion_errors_no_presence(self):
        # A field can appear in conversion errors without ever being
        # explicitly recorded via record_document (defensive union of keys).
        tracker = DataQualityTracker("op")
        tracker.record_conversion_error("phantom", "bad", ValueError("x"))
        tracker.total_records = 5

        report = tracker.generate_report()

        metrics = report.field_metrics["phantom"]
        assert metrics.present_records == 0
        assert metrics.missing_records == 5
        assert metrics.type_conversion_errors == 1

    def test_generate_report_empty_tracker(self):
        tracker = DataQualityTracker("op")
        report = tracker.generate_report()

        assert report.total_records_processed == 0
        assert report.field_metrics == {}


class TestGenerateQualityReport:
    """Tests for the generate_quality_report convenience function."""

    def test_all_required_fields_present_marks_success(self):
        schema = [FieldSpec(name="user_id", field_type=str, is_required=True)]
        documents = [{"user_id": "u1"}, {"user_id": "u2"}]

        report = generate_quality_report(documents, schema, operation_name="users")

        assert report.operation_name == "users"
        assert report.total_records_processed == 2
        assert report.successful_records == 2
        assert report.failed_records == 0

    def test_missing_required_field_marks_failure(self):
        schema = [FieldSpec(name="user_id", field_type=str, is_required=True)]
        documents = [{"user_id": "u1"}, {"other": "value"}]

        report = generate_quality_report(documents, schema)

        assert report.successful_records == 1
        assert report.failed_records == 1

    def test_none_value_for_required_field_marks_failure(self):
        schema = [FieldSpec(name="user_id", field_type=str, is_required=True)]
        documents = [{"user_id": None}]

        report = generate_quality_report(documents, schema)

        assert report.failed_records == 1
        assert report.successful_records == 0

    def test_no_required_fields_all_successful(self):
        schema = [FieldSpec(name="name", field_type=str, is_required=False)]
        documents = [{}, {"name": "Alice"}]

        report = generate_quality_report(documents, schema)

        assert report.successful_records == 2
        assert report.failed_records == 0

    def test_empty_documents_produces_empty_report(self):
        schema = [FieldSpec(name="user_id", field_type=str, is_required=True)]
        report = generate_quality_report([], schema)

        assert report.total_records_processed == 0
        assert report.successful_records == 0
        assert report.failed_records == 0

    def test_default_operation_name(self):
        report = generate_quality_report([], [])
        assert report.operation_name == "dataframe_conversion"

    def test_field_metrics_generated_for_optional_fields(self):
        schema = [
            FieldSpec(name="user_id", field_type=str, is_required=True),
            FieldSpec(name="nickname", field_type=str, is_required=False),
        ]
        documents = [{"user_id": "u1"}, {"user_id": "u2", "nickname": "bob"}]

        report = generate_quality_report(documents, schema)

        # nickname is present in field_presence tracking via record_document
        assert "nickname" in report.field_metrics
        assert report.field_metrics["nickname"].present_records == 1
        assert report.field_metrics["nickname"].missing_records == 1
