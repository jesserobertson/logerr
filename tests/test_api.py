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
        # Test from_callable
        result = logerr.result.from_callable(lambda: 42)
        assert isinstance(result, Ok)
        assert result.unwrap() == 42

        # Test from_callable with exception
        result = logerr.result.from_callable(lambda: 1 / 0)
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

        # Test from_callable
        option = logerr.option.from_callable(lambda: 42)
        assert isinstance(option, Some)
        assert option.unwrap() == 42

        option = logerr.option.from_callable(lambda: None)
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

        port_result = logerr.result.from_callable(lambda: parse_port(url))
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
            logerr.result.from_callable(lambda: "42")
            .map(int)
            .map(lambda x: x * 2)
            .unwrap_or(0)
        )

        assert result == 84
