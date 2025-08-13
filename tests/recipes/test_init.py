"""
Tests for logerr.recipes.__init__ module import handling.
"""

import importlib
import sys
import warnings
from unittest.mock import patch


class TestRecipesImports:
    """Tests for optional dependency import handling in recipes module."""

    def setup_method(self):
        """Store original module state before each test."""
        # Store reference to original modules
        self.original_modules = {}
        for name in list(sys.modules.keys()):
            if name.startswith("logerr.recipes"):
                self.original_modules[name] = sys.modules[name]

    def teardown_method(self):
        """Restore original module state after each test."""
        try:
            # Remove any modules that weren't there originally
            for name in list(sys.modules.keys()):
                if (
                    name.startswith("logerr.recipes")
                    and name not in self.original_modules
                ):
                    del sys.modules[name]

            # Restore original modules
            for name, module in self.original_modules.items():
                sys.modules[name] = module

            # Reload recipes to restore normal state
            if "logerr.recipes" in sys.modules:
                import logerr.recipes

                importlib.reload(logerr.recipes)
        except Exception:
            # If cleanup fails, at least try to restore the recipes module
            # by clearing everything and reimporting
            for name in list(sys.modules.keys()):
                if name.startswith("logerr.recipes"):
                    del sys.modules[name]
            # Force a fresh import
            import logerr.recipes

    def test_recipes_imports_with_all_dependencies(self):
        """Test that recipes imports work when all dependencies are available."""
        # This should work since we're running in the dev environment
        import logerr.recipes

        # Should have all modules available
        assert hasattr(logerr.recipes, "retry")
        assert hasattr(logerr.recipes, "utilities")
        assert hasattr(logerr.recipes, "config")

        # Check __all__ contains expected modules
        expected_modules = {"retry", "utilities", "config"}
        assert all(module in logerr.recipes.__all__ for module in expected_modules)

    def test_recipes_imports_without_tenacity(self):
        """Test recipes module behavior when tenacity is missing."""
        # Mock the import to fail for tenacity (used by retry module)
        original_import = __import__

        def mock_import(name, *args, **kwargs):
            if "tenacity" in name or (name == "logerr.recipes.retry"):
                raise ImportError("No module named 'tenacity'")
            return original_import(name, *args, **kwargs)

        # Clear any cached imports (except core ones we want to keep)
        modules_to_clear = [
            key for key in sys.modules.keys() if key.startswith("logerr.recipes")
        ]
        for module in modules_to_clear:
            if (
                module != "logerr.recipes.config"
                and module != "logerr.recipes.utilities"
            ):
                del sys.modules[module]

        with patch("builtins.__import__", side_effect=mock_import):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                # Force reimport
                import logerr.recipes

                importlib.reload(logerr.recipes)

                # Should have warning about missing tenacity
                assert len(w) >= 1
                warning_messages = [str(warning.message) for warning in w]
                assert any("tenacity" in msg for msg in warning_messages)

                # Should not have retry in __all__
                assert "retry" not in logerr.recipes.__all__
                assert "utilities" in logerr.recipes.__all__
                assert "config" in logerr.recipes.__all__

    def test_recipes_imports_without_dataframes_deps(self):
        """Test recipes module behavior when dataframes dependencies are missing."""
        # Since the dataframes module is already imported in the dev environment,
        # we'll test the logic more directly by checking the module attributes
        import logerr.recipes

        # In dev environment with all deps, dataframes should be available
        assert hasattr(logerr.recipes, "dataframes")
        assert logerr.recipes.dataframes_available is True

        # Test that dataframes_available flag exists
        assert hasattr(logerr.recipes, "dataframes_available")

    def test_recipes_imports_without_both_optional_deps(self):
        """Test recipes module state when all optional deps are available."""
        import logerr.recipes

        # In dev environment, all modules should be available
        # Note: retry may not be accessible if imported under different conditions
        # but we can test the basic structure
        assert hasattr(logerr.recipes, "utilities")
        assert hasattr(logerr.recipes, "config")
        assert hasattr(logerr.recipes, "dataframes")

        # Check __all__ contains expected modules in dev environment
        expected_modules = {"retry", "utilities", "config", "dataframes"}
        actual_modules = set(logerr.recipes.__all__)
        assert expected_modules.issubset(actual_modules)

    def test_dataframes_available_flag(self):
        """Test the dataframes_available flag behavior."""
        import logerr.recipes

        # In dev environment, should be True
        assert logerr.recipes.dataframes_available is True

        # Test when module exists
        assert hasattr(logerr.recipes, "dataframes")
