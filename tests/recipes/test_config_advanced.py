"""
Comprehensive tests for logerr.recipes.config advanced configuration.
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

from logerr.recipes.config import (
    AdvancedLoggingConfig,
    configure_advanced,
    configure_from_confection,
    get_advanced_config,
    get_library_config,
    get_log_level_for_library,
    reset_advanced_config,
    should_log_for_library,
    sync_core_config,
)


class TestAdvancedLoggingConfig:
    """Tests for AdvancedLoggingConfig dataclass."""

    def test_default_config_values(self):
        """Test that default config has expected values."""
        config = AdvancedLoggingConfig()

        assert config.enabled is True
        assert config.level == "ERROR"
        assert config.format is None
        assert config.libraries == {}
        assert config.capture_function_name is True
        assert config.capture_filename is True
        assert config.capture_lineno is True
        assert config.capture_locals is False

    def test_config_with_custom_values(self):
        """Test config creation with custom values."""
        config = AdvancedLoggingConfig(
            enabled=False,
            level="WARNING",
            format="custom format",
            libraries={"mylib": {"level": "DEBUG"}},
            capture_locals=True,
        )

        assert config.enabled is False
        assert config.level == "WARNING"
        assert config.format == "custom format"
        assert config.libraries == {"mylib": {"level": "DEBUG"}}
        assert config.capture_locals is True


class TestAdvancedConfigManagement:
    """Tests for advanced config management functions."""

    def setup_method(self):
        """Reset config before each test."""
        reset_advanced_config()

    def test_get_advanced_config_creates_default(self):
        """Test that get_advanced_config creates default when none exists."""
        # Reset internal state
        import logerr.recipes.config as config_module

        config_module._advanced_config = None

        config = get_advanced_config()
        assert isinstance(config, AdvancedLoggingConfig)
        assert config.enabled is True
        assert config.level == "ERROR"

    def test_reset_advanced_config(self):
        """Test that reset creates fresh default config."""
        # Modify config first
        configure_advanced({"level": "WARNING", "enabled": False})
        config = get_advanced_config()
        assert config.level == "WARNING"
        assert config.enabled is False

        # Reset and verify defaults restored
        reset_advanced_config()
        config = get_advanced_config()
        assert config.level == "ERROR"
        assert config.enabled is True

    def test_configure_advanced_valid_config(self):
        """Test configure_advanced with valid configuration."""
        config_dict = {
            "enabled": False,
            "level": "WARNING",
            "format": "custom format",
            "libraries": {"mylib": {"level": "DEBUG"}, "otherlib": {"enabled": False}},
            "capture_locals": True,
            "capture_filename": False,
        }

        result = configure_advanced(config_dict)
        assert result.is_ok()

        config = get_advanced_config()
        assert config.enabled is False
        assert config.level == "WARNING"
        assert config.format == "custom format"
        assert config.libraries["mylib"]["level"] == "DEBUG"
        assert config.libraries["otherlib"]["enabled"] is False
        assert config.capture_locals is True
        assert config.capture_filename is False

    def test_configure_advanced_invalid_level(self):
        """Test configure_advanced with invalid log level."""
        config_dict = {"level": "INVALID_LEVEL"}

        result = configure_advanced(config_dict)
        assert result.is_err()

        error = result.unwrap_err()
        assert "Invalid log level" in str(error)
        assert "INVALID_LEVEL" in str(error)

    def test_configure_advanced_partial_update(self):
        """Test that configure_advanced performs partial updates."""
        # Set initial config
        configure_advanced({"level": "WARNING", "enabled": False})

        # Update only level
        result = configure_advanced({"level": "DEBUG"})
        assert result.is_ok()

        config = get_advanced_config()
        assert config.level == "DEBUG"
        assert config.enabled is False  # Should preserve previous value

    def test_configure_advanced_merges_libraries(self):
        """Test that library configs are merged, not replaced."""
        # Set initial libraries
        configure_advanced({"libraries": {"lib1": {"level": "DEBUG"}}})

        # Add another library
        configure_advanced({"libraries": {"lib2": {"enabled": False}}})

        config = get_advanced_config()
        assert "lib1" in config.libraries
        assert "lib2" in config.libraries
        assert config.libraries["lib1"]["level"] == "DEBUG"
        assert config.libraries["lib2"]["enabled"] is False

    def test_configure_advanced_exception_handling(self):
        """Test configure_advanced handles exceptions in config creation."""
        with patch("logerr.recipes.config.AdvancedLoggingConfig") as mock_config:
            mock_config.side_effect = RuntimeError("Config creation failed")

            result = configure_advanced({"level": "WARNING"})
            assert result.is_err()
            assert isinstance(result.unwrap_err(), ValueError)


class TestConfectionIntegration:
    """Tests for confection configuration file integration."""

    def setup_method(self):
        """Reset config before each test."""
        reset_advanced_config()

    def test_configure_from_confection_valid_file(self):
        """Test loading configuration from a valid confection file."""
        config_content = """
[logerr]
enabled = false
level = "WARNING"
format = "custom format"

[logerr.libraries]
mylib = {"level": "DEBUG"}
otherlib = {"enabled": false}
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            result = configure_from_confection(config_path)
            assert result.is_ok()

            config = get_advanced_config()
            assert config.enabled is False
            assert config.level == "WARNING"
            assert config.format == "custom format"
            assert config.libraries["mylib"]["level"] == "DEBUG"
            assert config.libraries["otherlib"]["enabled"] is False
        finally:
            os.unlink(config_path)

    def test_configure_from_confection_missing_file(self):
        """Test error handling when config file doesn't exist."""
        result = configure_from_confection("/nonexistent/path/config.cfg")
        assert result.is_err()

        error = result.unwrap_err()
        assert "Config file not found" in str(error)

    def test_configure_from_confection_no_logerr_section(self):
        """Test behavior when config file has no logerr section."""
        config_content = """
[other_section]
key = "value"
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            result = configure_from_confection(config_path)
            # Should succeed but not change anything
            assert result.is_ok()

            config = get_advanced_config()
            assert config.enabled is True  # Should remain default
            assert config.level == "ERROR"  # Should remain default
        finally:
            os.unlink(config_path)

    def test_configure_from_confection_invalid_config_format(self):
        """Test error handling with malformed config file."""
        config_content = """
[logerr]
level = "INVALID_LEVEL"
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            result = configure_from_confection(config_path)
            assert result.is_err()

            error = result.unwrap_err()
            assert "Invalid log level" in str(error) or "INVALID_LEVEL" in str(error)
        finally:
            os.unlink(config_path)

    def test_configure_from_confection_file_read_error(self):
        """Test handling of file read errors."""
        with patch("logerr.recipes.config.Config") as mock_config_class:
            mock_config = MagicMock()
            mock_config.from_disk.side_effect = OSError("Permission denied")
            mock_config_class.return_value = mock_config

            # Create a real file so path exists
            with tempfile.NamedTemporaryFile(suffix=".cfg", delete=False) as f:
                config_path = f.name

            try:
                result = configure_from_confection(config_path)
                assert result.is_err()
                assert isinstance(result.unwrap_err(), Exception)
            finally:
                os.unlink(config_path)


class TestLibrarySpecificConfig:
    """Tests for library-specific configuration functions."""

    def setup_method(self):
        """Reset config before each test."""
        reset_advanced_config()

    def test_get_library_config_existing(self):
        """Test getting config for a library that has specific settings."""
        configure_advanced(
            {"libraries": {"mylib": {"level": "DEBUG", "enabled": False}}}
        )

        config = get_library_config("mylib")
        assert config["level"] == "DEBUG"
        assert config["enabled"] is False

    def test_get_library_config_nonexistent(self):
        """Test getting config for a library with no specific settings."""
        config = get_library_config("nonexistent_lib")
        assert config == {}

    def test_should_log_for_library_global_disabled(self):
        """Test library logging when global logging is disabled."""
        configure_advanced({"enabled": False})

        assert should_log_for_library("anylib") is False

    def test_should_log_for_library_library_disabled(self):
        """Test library logging when specific library is disabled."""
        configure_advanced(
            {"enabled": True, "libraries": {"mylib": {"enabled": False}}}
        )

        assert should_log_for_library("mylib") is False
        assert should_log_for_library("otherlib") is True

    def test_should_log_for_library_library_enabled(self):
        """Test library logging when library is explicitly enabled."""
        configure_advanced({"libraries": {"mylib": {"enabled": True}}})

        assert should_log_for_library("mylib") is True

    def test_should_log_for_library_default_behavior(self):
        """Test library logging with default settings."""
        configure_advanced({"enabled": True})

        assert should_log_for_library("anylib") is True

    def test_get_log_level_for_library_specific_level(self):
        """Test getting log level for library with specific setting."""
        configure_advanced(
            {"level": "ERROR", "libraries": {"mylib": {"level": "DEBUG"}}}
        )

        assert get_log_level_for_library("mylib") == "DEBUG"
        assert get_log_level_for_library("otherlib") == "ERROR"

    def test_get_log_level_for_library_global_level(self):
        """Test getting log level falls back to global setting."""
        configure_advanced({"level": "WARNING"})

        assert get_log_level_for_library("anylib") == "WARNING"

    def test_get_log_level_for_library_type_coercion(self):
        """Test that log level is properly coerced to string."""
        configure_advanced(
            {
                "libraries": {"mylib": {"level": 123}}  # Non-string level
            }
        )

        level = get_log_level_for_library("mylib")
        assert isinstance(level, str)
        assert level == "123"


class TestCoreConfigSync:
    """Tests for synchronizing core config with advanced config."""

    def setup_method(self):
        """Reset config before each test."""
        reset_advanced_config()

    def test_sync_core_config(self):
        """Test that sync_core_config calls core configure with right values."""
        with patch("logerr.config.configure") as mock_core_configure:
            configure_advanced({"enabled": False, "level": "WARNING"})

            sync_core_config()

            mock_core_configure.assert_called_once_with(enabled=False, level="WARNING")

    def test_sync_core_config_default_values(self):
        """Test sync with default advanced config values."""
        with patch("logerr.config.configure") as mock_core_configure:
            sync_core_config()

            mock_core_configure.assert_called_once_with(enabled=True, level="ERROR")
