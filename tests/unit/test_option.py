"""
Tests for Option type with automatic logging.
"""

from unittest.mock import patch

import pytest
from loguru import logger

import logerr
from logerr import Nothing, Option, Some, configure

pytestmark = pytest.mark.unit


class TestSome:
    """Tests for Some class."""

    def test_some_creation(self):
        option = Some(42)
        assert option.is_some()
        assert not option.is_nothing()
        assert option.unwrap() == 42

    def test_some_unwrap_or(self):
        option = Some(42)
        assert option.unwrap_or(0) == 42

    def test_some_unwrap_or_else(self):
        option = Some(42)
        assert option.unwrap_or_else(lambda: 0) == 42

    def test_some_map(self):
        option = Some(42)
        mapped = option.map(lambda x: x * 2)
        assert isinstance(mapped, Some)
        assert mapped.unwrap() == 84

    def test_some_then(self):
        option = Some(42)
        chained = option.then(lambda x: Some(x * 2))
        assert isinstance(chained, Some)
        assert chained.unwrap() == 84

    def test_some_or_else(self):
        option = Some(42)
        result = option.unwrap_or(0)
        assert result == 42

    def test_some_filter_passes(self):
        option = Some(42)
        filtered = option.filter(lambda x: x > 30)
        assert isinstance(filtered, Some)
        assert filtered.unwrap() == 42

    def test_some_filter_fails(self):
        option = Some(42)
        filtered = option.filter(lambda x: x > 50)
        assert isinstance(filtered, Nothing)

    def test_some_map_with_exception(self):
        """Some.map propagates exceptions raised by the transform (Rust parity)."""
        option = Some(42)
        with pytest.raises(ZeroDivisionError):
            option.map(lambda x: 1 / 0)

    def test_some_map_returns_none(self):
        option = Some(42)
        mapped = option.map(lambda x: None)  # Returns None
        assert isinstance(mapped, Nothing)

    def test_some_then_exception_handling(self):
        """Test that Some.then propagates exceptions raised in callback functions."""

        def failing_func(x):
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            Some(42).then(failing_func)

    def test_some_ok_or(self):
        from logerr import Ok

        option = Some(42)
        result = option.ok_or("error message")
        assert isinstance(result, Ok)
        assert result.is_ok()
        assert result.unwrap() == 42

    def test_some_ok_or_else(self):
        from logerr import Ok

        option = Some(42)
        result = option.ok_or_else(lambda: "error message")
        assert isinstance(result, Ok)
        assert result.is_ok()
        assert result.unwrap() == 42

    def test_some_or_else_returns_self(self):
        option = Some(42)
        result = option.or_else(lambda: Some(99))
        assert result is option

    def test_some_or_default_returns_self(self):
        option = Some(42)
        result = option.or_default(99)
        assert result is option

    def test_some_filter_exception_handling(self):
        """Test that Some.filter propagates exceptions raised by the predicate."""
        option = Some(42)
        with pytest.raises(ZeroDivisionError):
            option.filter(lambda x: 1 / 0 > 0)

    def test_some_repr(self):
        assert repr(Some(42)) == "Some(42)"

    def test_some_gt_incomparable_type(self):
        """Some.__gt__ against an unrelated type should defer via NotImplemented."""
        some = Some("hello")
        with pytest.raises(TypeError):
            assert some > 5


class TestNothing:
    """Tests for Nothing class."""

    def test_nothing_creation(self):
        option = Nothing("test reason")
        assert not option.is_some()
        assert option.is_nothing()

    def test_nothing_unwrap_raises(self):
        option = Nothing("test reason")
        with pytest.raises(ValueError, match="Called unwrap on Nothing: test reason"):
            option.unwrap()

    def test_nothing_unwrap_reraises_original_exception(self):
        """Nothing.unwrap should re-raise the original exception when constructed
        from_exception, mirroring Result.Err.unwrap's behaviour."""
        original = ValueError("boom")
        option = Nothing.from_exception(original)
        with pytest.raises(ValueError) as exc_info:
            option.unwrap()
        assert exc_info.value is original

    def test_nothing_ok_or(self):
        from logerr import Err

        option = Nothing("test reason")
        result = option.ok_or("error message")
        assert isinstance(result, Err)
        assert result.is_err()
        assert result.unwrap_err() == "error message"

    def test_nothing_ok_or_else(self):
        from logerr import Err

        option = Nothing("test reason")
        result = option.ok_or_else(lambda: "error message")
        assert isinstance(result, Err)
        assert result.is_err()
        assert result.unwrap_err() == "error message"

    def test_nothing_ok_or_else_exception_handling(self):
        """Test that Nothing.ok_or_else propagates exceptions raised by err_fn."""
        option = Nothing.empty()

        def failing_err_fn():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            option.ok_or_else(failing_err_fn)

    def test_nothing_or_else_exception_handling(self):
        """Test that Nothing.or_else propagates exceptions raised by the callback."""
        option = Nothing.empty()

        def failing_recovery():
            raise RuntimeError("recovery failed")

        with pytest.raises(RuntimeError, match="recovery failed"):
            option.or_else(failing_recovery)

    def test_nothing_repr(self):
        assert repr(Nothing("test reason")) == "Nothing('test reason')"

    def test_nothing_lt_incomparable_type(self):
        """Nothing.__lt__ against an unrelated type defers via NotImplemented."""
        nothing = Nothing.empty()
        with pytest.raises(TypeError):
            assert nothing < 5

    def test_nothing_gt_incomparable_type(self):
        """Nothing.__gt__ against an unrelated type defers via NotImplemented."""
        nothing = Nothing.empty()
        with pytest.raises(TypeError):
            assert nothing > 5

    def test_nothing_ge_some_is_false(self):
        """Nothing is never >= a Some, hitting Nothing.__ge__'s fallback branch."""
        nothing = Nothing.empty()
        some = Some(42)
        assert not (nothing >= some)

    def test_nothing_unwrap_or(self):
        option = Nothing("test reason")
        assert option.unwrap_or(42) == 42

    def test_nothing_unwrap_or_else(self):
        option = Nothing("test reason")
        assert option.unwrap_or_else(lambda: 42) == 42

    def test_nothing_unwrap_or_else_exception(self):
        """Test that Nothing.unwrap_or_else handles exceptions in callback functions."""

        def failing_func():
            raise RuntimeError("callback failed")

        nothing = Nothing("test reason")
        with pytest.raises(ValueError, match="unwrap_or_else function failed"):
            nothing.unwrap_or_else(failing_func)

    def test_nothing_map_returns_nothing(self):
        option = Nothing("test reason")
        mapped = option.map(lambda x: x * 2)
        assert isinstance(mapped, Nothing)

    def test_nothing_then_returns_nothing(self):
        option = Nothing("test reason")
        chained = option.then(lambda x: Some(x * 2))
        assert isinstance(chained, Nothing)

    def test_nothing_or_else(self):
        option = Nothing("test reason")
        result = option.unwrap_or(42)
        assert result == 42

    def test_nothing_filter_returns_nothing(self):
        option = Nothing("test reason")
        filtered = option.filter(lambda x: True)
        assert isinstance(filtered, Nothing)

    def test_nothing_from_exception(self):
        exception = ValueError("test error")
        option = Nothing.from_exception(exception)
        assert isinstance(option, Nothing)
        assert "Exception: test error" in option._reason

    def test_nothing_from_none(self):
        option = Nothing.from_none("custom reason")
        assert isinstance(option, Nothing)
        assert option._reason == "custom reason"

    def test_nothing_empty_no_logging(self):
        with patch.object(logger, "log") as mock_log:
            Nothing.empty()
            mock_log.assert_not_called()


class TestOptionFactories:
    """Tests for Option factory functions."""

    def test_option_from_nullable_some(self):
        option = logerr.option.from_nullable(42)
        assert isinstance(option, Some)
        assert option.unwrap() == 42

    def test_option_from_nullable_nothing(self):
        option = logerr.option.from_nullable(None)
        assert isinstance(option, Nothing)

    def test_option_of_some(self):
        option = logerr.option.of(lambda: 42)
        assert isinstance(option, Some)
        assert option.unwrap() == 42

    def test_option_of_none(self):
        option = logerr.option.of(lambda: None)
        assert isinstance(option, Nothing)

    def test_option_of_exception(self):
        option = logerr.option.of(lambda: 1 / 0)
        assert isinstance(option, Nothing)

    def test_option_from_predicate_success(self):
        option = logerr.option.from_predicate(42, lambda x: x > 30)
        assert isinstance(option, Some)
        assert option.unwrap() == 42

    def test_option_from_predicate_failure(self):
        option = logerr.option.from_predicate(42, lambda x: x > 50)
        assert isinstance(option, Nothing)

    def test_option_from_predicate_exception(self):
        option = logerr.option.from_predicate(42, lambda x: 1 / 0)
        assert isinstance(option, Nothing)

    def test_option_of_classmethod_success(self):
        from logerr import Option

        option = Option.of(lambda: 42)
        assert isinstance(option, Some)
        assert option.unwrap() == 42

    def test_option_of_classmethod_exception(self):
        """Test the Option.of() ABC classmethod's exception-handling branch."""
        from logerr import Option

        option = Option.of(lambda: 1 / 0)
        assert isinstance(option, Nothing)

    def test_option_from_predicate_classmethod(self):
        """Test the Option.from_predicate() ABC classmethod delegates correctly."""
        from logerr import Option

        option = Option.from_predicate(42, lambda x: x > 30)
        assert isinstance(option, Some)
        assert option.unwrap() == 42


class TestLogging:
    """Tests for automatic logging functionality."""

    def setup_method(self):
        """Reset configuration before each test."""
        from logerr import reset_config

        reset_config()

    def test_nothing_logs_by_default(self):
        with patch.object(logger, "bind") as mock_bind:
            mock_bound = mock_bind.return_value
            Nothing("test reason")
            mock_bind.assert_called_once()
            mock_bound.log.assert_called_once()

        # Check that the log call used WARNING level (default for Nothing)
        args, kwargs = mock_bound.log.call_args
        assert args[0] == "WARNING"  # log level
        assert "test reason" in args[1]  # message

    def test_nothing_logging_can_be_disabled(self):
        configure(enabled=False)

        with patch.object(logger, "bind") as mock_bind:
            Nothing("test reason")
            mock_bind.assert_not_called()

        # Reset config
        configure(enabled=True)

    def test_custom_log_level(self):
        configure(level="INFO")

        with patch.object(logger, "bind") as mock_bind:
            mock_bound = mock_bind.return_value
            Nothing("test reason")
            mock_bind.assert_called_once()
            mock_bound.log.assert_called_once()

        # Check that the log call used INFO level
        args, kwargs = mock_bound.log.call_args
        assert args[0] == "INFO"

        # Reset config
        configure(level="ERROR")

    @pytest.mark.skip(reason="Library-specific config moved to recipes module")
    def test_library_specific_config(self):
        # This test is for advanced configuration features
        pass

    @pytest.mark.skip(reason="Per-library logging moved to recipes module")
    def test_should_log_when_disabled(self):
        """Test should_log_for_library when logging is disabled globally."""
        # This test is for advanced configuration features
        pass

    @pytest.mark.skip(reason="configure_from_confection moved to recipes module")
    def test_configure_from_confection_no_logerr_key(self):
        """Test configure_from_confection when config file doesn't contain 'logerr' key."""
        # Create a temporary config file without 'logerr' section
        import tempfile
        from pathlib import Path

        from logerr.config import configure_from_confection, get_config

        with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
            f.write('[other_section]\nsome_setting = "value"\n')
            temp_config_path = f.name

        try:
            # This should not raise an error, just do nothing
            configure_from_confection(temp_config_path)

            # Configuration should remain at default values
            config = get_config()
            assert config.enabled is True

        finally:
            Path(temp_config_path).unlink()


class TestChaining:
    """Tests for Option chaining operations."""

    def test_some_chain(self):
        option = (
            Some(42)
            .map(lambda x: x * 2)
            .then(lambda x: Some(x + 1))
            .filter(lambda x: x > 80)
            .map(lambda x: str(x))
        )

        assert isinstance(option, Some)
        assert option.unwrap() == "85"

    def test_nothing_chain_short_circuits(self):
        option = (
            Nothing.empty()  # Use empty() to avoid logging in test
            .map(lambda x: x * 2)  # Should not execute
            .then(lambda x: Some(x + 1))  # Should not execute
            .filter(lambda x: x > 80)  # Should not execute
            .map(lambda x: str(x))
        )  # Should not execute

        assert isinstance(option, Nothing)

    def test_mixed_chain_with_filter_failure(self):
        with patch.object(logger, "log"):  # Suppress logging for test
            option = (
                Some(42)
                .map(lambda x: x * 2)  # 84
                .filter(lambda x: x > 100)  # Fails here
                .map(lambda x: str(x))
            )  # Should not execute

            assert isinstance(option, Nothing)

    def test_chain_with_or_else_recovery(self):
        option = (
            Nothing.empty()
            .map(lambda x: x * 2)
            .or_default(99)  # Recovery
            .map(lambda x: str(x))
        )

        assert isinstance(option, Some)
        assert option.unwrap() == "99"


class TestIntegrationWithResult:
    """Tests for integration between Option and Result types."""

    def test_option_to_result_pattern(self):
        # Common pattern: convert Option to Result
        def option_to_result(opt):
            if opt.is_some():
                from logerr import Ok

                return Ok(opt.unwrap())
            else:
                from logerr import Err

                return Err(f"Option was Nothing: {opt._reason}")

        some_option = Some(42)
        nothing_option = Nothing.empty()

        result1 = option_to_result(some_option)
        result2 = option_to_result(nothing_option)

        assert result1.is_ok()
        assert result1.unwrap() == 42

        assert result2.is_err()
        assert "Option was Nothing" in str(result2._error)


class TestOptionCombinatorMethods:
    """Test that zip/flatten/and_/or_ methods delegate to logerr.functools."""

    def test_some_zip_some(self):
        result = Some(1).zip(Some("a"))
        assert result.is_some()
        assert result.unwrap() == (1, "a")

    def test_some_zip_nothing(self):
        result = Some(1).zip(Nothing.empty())
        assert result.is_nothing()

    def test_nothing_zip(self):
        result = Nothing.empty().zip(Some(1))
        assert result.is_nothing()

    def test_some_flatten(self):
        result = Some(Some(42)).flatten()
        assert result.is_some()
        assert result.unwrap() == 42

    def test_nothing_flatten(self):
        result = Nothing.empty().flatten()
        assert result.is_nothing()

    def test_some_and(self):
        result = Some(1).and_(Some("a"))
        assert result.is_some()
        assert result.unwrap() == "a"

    def test_nothing_and(self):
        result = Nothing.empty().and_(Some("a"))
        assert result.is_nothing()

    def test_some_or(self):
        result = Some(1).or_(Some(2))
        assert result.is_some()
        assert result.unwrap() == 1

    def test_nothing_or(self):
        result = Nothing.empty().or_(Some(2))
        assert result.is_some()
        assert result.unwrap() == 2

    def test_some_iter(self):
        assert list(Some(42)) == [42]

    def test_nothing_iter(self):
        assert list(Nothing.empty()) == []

    def test_builtin_zip_works_via_iter(self):
        """Once Option is iterable, Python's own zip() works directly -
        no bespoke logerr zip wrapper needed. strict=False is explicit
        because Option/Nothing legitimately yield different counts
        (0 or 1) by design - that's not a bug to catch here."""
        assert list(zip(Some(1), Some("a"), strict=False)) == [(1, "a")]
        assert list(zip(Nothing.empty(), Some("a"), strict=False)) == []


class TestOptionCollectionFactories:
    """Test that Option.sequence/Option.traverse delegate to logerr.itertools."""

    def test_sequence_all_some(self):
        result = Option.sequence([Some(1), Some(2)])
        assert result.is_some()
        assert result.unwrap() == [1, 2]

    def test_sequence_short_circuits(self):
        result = Option.sequence([Some(1), Nothing.empty()])
        assert result.is_nothing()

    def test_traverse_all_succeed(self):
        result = Option.traverse([1, 2, 3], lambda x: Some(x * 2))
        assert result.is_some()
        assert result.unwrap() == [2, 4, 6]

    def test_traverse_short_circuits(self):
        result = Option.traverse(
            [1, 2, 3], lambda x: Nothing.empty() if x == 2 else Some(x)
        )
        assert result.is_nothing()
