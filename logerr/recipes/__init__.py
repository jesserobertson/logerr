"""
logerr.recipes: Optional extended functionality for logerr.

This module provides additional patterns for logerr that may not be needed
by all users, gated behind optional heavy dependencies. Install with:

    pixi run -e retry   # tenacity-based retry patterns
    pixi run -e tables  # pymongo/pandas dataframe conversion

Available modules:
- retry: Comprehensive retry patterns with tenacity integration
- config: Advanced configuration with per-library settings and file loading
- dataframes: NoSQL to DataFrame conversion with data quality logging

For general-purpose functional utilities (validate, resolve, chain,
attribute, error, pipe, try_chain), see logerr.utilities - they have no
dependency on tenacity/pandas/pymongo, so they live in core.

Usage:
    from logerr.recipes import retry, config, dataframes

    @retry.on_err(max_attempts=3)
    def flaky_operation() -> Result[int, str]:
        return Ok(42)

    # Advanced configuration
    from logerr.recipes.config import configure_advanced

    # NoSQL to DataFrame conversion
    from logerr.recipes.dataframes import Required, from_mongo
    schema = {"user_id": Required[str], "name": str, "age": int}
    df_result = from_mongo(db.users, {}, schema=schema)
"""

# Always available modules
from . import config

# Import dataframes module when dependencies are available
try:
    from . import dataframes

    dataframes_available = True
except ImportError:
    dataframes_available = False

# Import retry module when tenacity is available
try:
    from . import retry

    if dataframes_available:
        __all__ = ["retry", "config", "dataframes"]
    else:
        __all__ = ["retry", "config"]
except ImportError:
    # Provide helpful error message when tenacity is missing for retry
    import warnings

    warnings.warn(
        "logerr.recipes.retry requires tenacity. Install with: pixi run -e retry",
        ImportWarning,
        stacklevel=2,
    )
    if dataframes_available:
        __all__ = ["config", "dataframes"]
    else:
        __all__ = ["config"]

# Warn about missing dataframes dependencies
if not dataframes_available:
    import warnings

    warnings.warn(
        "logerr.recipes.dataframes requires pymongo and pandas. "
        "Install with: pixi run -e tables",
        ImportWarning,
        stacklevel=2,
    )
