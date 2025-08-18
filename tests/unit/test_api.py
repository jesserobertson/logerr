"""
Tests for the new clean API design.
"""

import logerr
from logerr import Err, Nothing, Ok, Some


class TestCleanAPI:
    """Tests for the new clean API structure."""

    def test_direct_imports(self):
        """Test that direct imports still work."""
        ok_result = Ok(42)
        err_result = Err("error")
        some_option = Some(42)
        nothing_option = Nothing.empty()

        assert ok_result.is_ok()
        assert err_result.is_err()
        assert some_option.is_some()
        assert nothing_option.is_nothing()

    def test_result_factories(self):
        """Test result factory functions through module namespace."""
        # Test of
        result = logerr.result.of(lambda: 42)
        assert isinstance(result, Ok)
        assert result.unwrap() == 42

        # Test of with exception
        result = logerr.result.of(lambda: 1 / 0)
        assert isinstance(result, Err)

        # Test from_optional
        result = logerr.result.from_optional(42, "was None")
        assert isinstance(result, Ok)
        assert result.unwrap() == 42

        result = logerr.result.from_optional(None, "was None")
        assert isinstance(result, Err)
        assert result._error == "was None"

    def test_option_factories(self):
        """Test option factory functions through module namespace."""
        # Test from_nullable
        option = logerr.option.from_nullable(42)
        assert isinstance(option, Some)
        assert option.unwrap() == 42

        option = logerr.option.from_nullable(None)
        assert isinstance(option, Nothing)

        # Test of
        option = logerr.option.of(lambda: 42)
        assert isinstance(option, Some)
        assert option.unwrap() == 42

        option = logerr.option.of(lambda: None)
        assert isinstance(option, Nothing)

        # Test from_predicate
        option = logerr.option.from_predicate(42, lambda x: x > 30)
        assert isinstance(option, Some)
        assert option.unwrap() == 42

        option = logerr.option.from_predicate(42, lambda x: x > 50)
        assert isinstance(option, Nothing)

    def test_configuration_api(self):
        """Test that configuration functions are available at top level."""
        # Test that these functions exist and are callable
        assert callable(logerr.configure)
        assert callable(logerr.get_config)
        assert callable(logerr.reset_config)

        # Test basic configuration
        logerr.configure(level="DEBUG")
        new_config = logerr.get_config()
        assert new_config.level == "DEBUG"

        # Reset
        logerr.reset_config()
        reset_config = logerr.get_config()
        assert reset_config.level == "ERROR"  # default


class TestAPIDocumentation:
    """Test that demonstrates the clean API in action."""

    def test_real_world_example(self):
        """Example showing the clean API in a realistic scenario."""
        # Simulate a config dict that might be None
        config_dict = {"database_url": "postgres://localhost/db"}

        # Clean way to get optional config values
        db_url = logerr.option.from_nullable(config_dict.get("database_url"))

        if db_url.is_some():
            url = db_url.unwrap()
            assert url == "postgres://localhost/db"

        # Missing config value
        missing = logerr.option.from_nullable(config_dict.get("missing_key"))
        assert missing.is_nothing()

        # Safe operation with Result
        def parse_port(url: str) -> int:
            # Simulate parsing that might fail
            if "localhost" in url:
                return 5432
            else:
                raise ValueError("Invalid URL")

        port_result = logerr.result.of(lambda: parse_port(url))
        assert port_result.is_ok()
        assert port_result.unwrap() == 5432

    def test_chaining_with_factories(self):
        """Test that factory functions work well with method chaining."""
        # Start with a nullable value, convert to option, and chain operations
        result = (
            logerr.option.from_nullable("42")
            .map(int)
            .filter(lambda x: x > 0)
            .map(lambda x: x * 2)
            .unwrap_or(0)
        )

        assert result == 84

        # Same with Result
        result = (
            logerr.result.of(lambda: "42").map(int).map(lambda x: x * 2).unwrap_or(0)
        )

        assert result == 84

    def test_match_statements_with_results(self):
        """Test demonstrating match statement usage with Results (Python 3.12+)."""
        ok_result = Ok(42)
        err_result = Err("failed")

        # Match statements provide clean pattern matching
        match ok_result:
            case Ok(value):
                assert value == 42
            case Err(_):
                raise AssertionError("Should not match Err")

        match err_result:
            case Ok(_):
                raise AssertionError("Should not match Ok")
            case Err(error):
                assert error == "failed"

        # More complex example with processing
        def process_result_match(result):
            match result:
                case Ok(value) if value > 0:
                    return f"Positive: {value}"
                case Ok(value):
                    return f"Zero or negative: {value}"
                case Err(error):
                    return f"Error: {error}"

        assert process_result_match(Ok(42)) == "Positive: 42"
        assert process_result_match(Ok(-5)) == "Zero or negative: -5"
        assert process_result_match(Err("bad")) == "Error: bad"

    def test_match_statements_with_options(self):
        """Test demonstrating match statement usage with Options (Python 3.12+)."""
        some_option = Some("hello")
        nothing_option = Nothing.empty()

        # Match statements with Options
        match some_option:
            case Some(value):
                assert value == "hello"
            case Nothing():
                raise AssertionError("Should not match Nothing")

        match nothing_option:
            case Some(_):
                raise AssertionError("Should not match Some")
            case Nothing():
                pass  # Expected

        # Processing example with guards
        def process_option_match(option):
            match option:
                case Some(value) if len(value) > 5:
                    return f"Long: {value}"
                case Some(value):
                    return f"Short: {value}"
                case Nothing():
                    return "Empty"

        assert process_option_match(Some("hello world")) == "Long: hello world"
        assert process_option_match(Some("hi")) == "Short: hi"
        assert process_option_match(Nothing.empty()) == "Empty"
