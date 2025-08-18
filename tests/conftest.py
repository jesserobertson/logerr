"""
Test configuration and fixtures for logerr.
"""

import pytest
from hypothesis import Verbosity, settings


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests",
    )


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line(
        "markers", "recipes: mark test as recipes functionality test"
    )
    config.addinivalue_line(
        "markers", "dataframes: mark test as dataframes functionality test"
    )
    config.addinivalue_line(
        "markers", "mongo: mark test as requiring MongoDB connection"
    )
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "network: mark test as requiring network access")
    config.addinivalue_line(
        "markers", "property: mark test as property-based test using hypothesis"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle markers."""
    if config.getoption("--run-integration"):
        # Run all tests including integration
        return

    # Skip integration tests by default
    skip_integration = pytest.mark.skip(reason="need --run-integration option to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


@pytest.fixture
def sample_data():
    """Provide sample data for testing."""
    return {
        "test_records": [
            {"id": 1, "name": "Test Item 1", "active": True},
            {"id": 2, "name": "Test Item 2", "active": False},
            {"id": 3, "name": "Test Item 3", "active": True},
        ],
        "test_values": [1, 2, 3, None, "test", True, False],
        "test_errors": [
            ValueError("Test value error"),
            RuntimeError("Test runtime error"),
            Exception("Generic test exception"),
        ],
    }


# Configure hypothesis for testing
settings.register_profile("dev", max_examples=10, verbosity=Verbosity.verbose)
settings.register_profile("ci", max_examples=100, deadline=1000)
settings.load_profile("dev")
