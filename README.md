# logerr

**Rust-like Option and Result types for Python with automatic logging**

[![Tests](https://img.shields.io/badge/tests-162%20passed-green)](https://github.com/jesserobertson/logerr)
[![Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen)](https://github.com/jesserobertson/logerr)
[![Type Checked](https://img.shields.io/badge/mypy-passing-blue)](https://github.com/jesserobertson/logerr)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue)](https://github.com/jesserobertson/logerr)

`logerr` brings the power of Rust's `Option<T>` and `Result<T, E>` types to Python, with automatic logging of error cases using [loguru](https://github.com/Delgan/loguru). Write clean, functional error-handling code while maintaining excellent observability.

## 🌟 Features

- **🦀 Rust-like Types**: Familiar `Option<T>` and `Result<T, E>` with method chaining
- **🪵 Automatic Logging**: Error cases logged automatically with configurable levels  
- **⚙️ Highly Configurable**: Per-library settings via [confection](https://github.com/explosion/confection)
- **🔒 Type Safe**: Full mypy support with proper generic types
- **🧪 Well Tested**: 79 tests including comprehensive doctests
- **🚀 Clean API**: Discoverable, IDE-friendly interface

## 🚀 Quick Start

```python
from logerr import Result, Ok, Err, Some, Nothing

# Handle operations that might fail - functional pipeline style
def risky_operation():
    raise ConnectionError("Database connection failed")

# Use functional pipeline with automatic error logging
message = (
    Result.of(risky_operation)
    .map(lambda value: f"Success: {value}")
    .unwrap_or("Failed: check logs for details")
)
print(message)
# 🪵 Automatic logging output:
# 2024-01-15 14:23:12.345 | ERROR | logerr.result:425 - Result error in risky_operation:2 - Database connection failed
```

**✨ The key difference:** Errors are **automatically logged** with full context - no manual logging required!

```python
from logerr import Option

# Work with optional values using functional pipeline
user_data = {"name": "Alice"}

# Functional pipeline for nullable values
contact = (
    Option.from_nullable(user_data.get("email"))
    .filter(lambda email: "@" in email)  # Validate email format
    .unwrap_or("no-email@example.com")
)
# 🪵 Automatic logging output:
# 2024-01-15 14:23:12.456 | WARNING | logerr.option:421 - Option Nothing in from_nullable:1 - Value was None

# Chain operations elegantly with automatic error handling
processed = (
    Ok("hello world")
    .map(str.upper)           # Ok("HELLO WORLD")  
    .map(lambda s: s.split()) # Ok(["HELLO", "WORLD"])
    .map(len)                 # Ok(2)
    .unwrap_or(0)            # 2
)
```

## 📦 Installation

Currently available from source:

```bash
git clone https://github.com/jesserobertson/logerr
cd logerr
pip install -e .
```

### Optional Features

**Recipes Module**: Advanced patterns and utilities for specialized use cases:

```bash
# Install with recipes (includes retry patterns, advanced utilities, config, and dataframes)
pixi run -e recipes

# Use in your code
from logerr.recipes import retry, utilities, config, dataframes

@retry.on_err(max_attempts=3)
def flaky_operation() -> Result[int, str]:
    return Ok(42)

# Advanced utilities
from logerr.recipes.utilities import validate, pipe, try_chain

# Advanced configuration
config.configure_advanced({
    "libraries": {"my_module": {"level": "DEBUG"}},
    "capture_locals": True
})

# NoSQL to DataFrame conversion with data quality logging
from logerr.recipes.dataframes import Required, from_mongo

schema = {
    "user_id": Required[str],  # Must be present
    "email": Required[str],    # Must be present
    "name": str,              # Optional by default
    "age": int,               # Optional by default
}

df_result = from_mongo(db.users, {"status": "active"}, schema=schema)
df = df_result.unwrap_or_default()
```

## 🔍 Why logerr?

### See the Difference

**Traditional approach** (manual logging required):
```python
def load_config():
    try:
        with open("config.json") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")  # Manual logging
        return None

config = load_config()
if config is None:
    print("Using defaults")
```

**With logerr** (automatic logging + functional style):
```python
from logerr import Result
from logerr.utils import execute
import json

def load_config():
    return execute(lambda: json.load(open("config.json")))

# Functional pipeline with error recovery
config = (
    load_config()
    .or_default({})  # Fallback to empty config
    .unwrap()
)
# 🪵 Automatically logs:
# 2024-01-15 14:23:12.789 | ERROR | logerr.result:425 - Result error in <lambda>:1 - [Errno 2] No such file or directory: 'config.json'
```

### Traditional Tradeoffs vs logerr

| Approach | Pros | Cons |
|----------|------|------|
| **Exceptions** | Clear error info | Hard to follow, requires try/catch |
| **None returns** | Simple | Loses error context, silent failures |
| **Tuple returns** | Explicit | Verbose, easy to misuse |
| **🦀 logerr** | **Explicit + Automatic logging + Composable + Type safe** | **Learning curve** |

**logerr gives you the best of all worlds:**

✅ **Explicit error handling** like Go or Rust  
✅ **Composable operations** through method chaining  
✅ **Automatic observability** without manual logging  
✅ **Type safety** that catches errors at development time  

## 📖 Documentation

- **[Getting Started](https://jesserobertson.github.io/logerr/guide/getting-started/)** - Learn the basics
- **[Result Types](https://jesserobertson.github.io/logerr/guide/result-types/)** - Handle operations that might fail
- **[Option Types](https://jesserobertson.github.io/logerr/guide/option-types/)** - Work with nullable values  
- **[Configuration](https://jesserobertson.github.io/logerr/guide/configuration/)** - Customize logging behavior
- **[API Reference](https://jesserobertson.github.io/logerr/api/result/)** - Complete API documentation

## 💡 Examples

### Database Connection with Retry Logic

```python
from logerr import Result, Ok, Err
from logerr.recipes import retry  # Requires: pixi install --feature recipes
from typing import Any

@retry.on_err(max_attempts=3, log_attempts=True)
def connect_to_database(url: str) -> Result[Any, Exception]:
    """Connect with automatic retry on failure"""
    try:
        connection = database.connect(url)
        return Ok(connection)
    except ConnectionError as e:
        return Err.from_exception(e)

# Alternative functional approach with retry utility
def connect_with_fallback() -> Result[Any, Exception]:
    """Try primary, then backup with retry logic"""
    return (
        retry.with_retry(lambda: database.connect("primary-server.db"))
        .or_else(lambda _: retry.with_retry(lambda: database.connect("backup-server.db")))
    )

# Usage - automatic retry and logging  
result = (
    connect_to_database("primary-server.db")
    .map(lambda conn: "Connected successfully!")
    .unwrap_or("All connection attempts failed - check logs")
)

print(result)
```

### Configuration Loading Pipeline

```python
from logerr import Result, Ok, Err  
from logerr.utils import execute, validate, resolve
import json
from pathlib import Path

def load_config(path: str) -> Result[dict, str]:
    """Load and validate configuration using functional utilities."""
    return (
        execute(lambda: Path(path).read_text())
        .then(lambda text: execute(lambda: json.loads(text)))
        .then(validate_config)
        .map_err(lambda e: f"Config error in {path}: {e}")
    )

def validate_config(config: dict) -> Result[dict, str]:
    """Validate required configuration keys using validation utility."""
    required_keys = ["database_url", "api_key"]
    
    return (
        validate(config, lambda cfg: all(key in cfg for key in required_keys), None)
        .map_err(lambda _: f"Missing required keys: {[k for k in required_keys if k not in config]}")
        .map(lambda _: config)
    )

# Functional pipeline with fallback configuration
default_config = {
    "database_url": "sqlite:///default.db", 
    "api_key": "demo-key"
}

config = (
    load_config("app.json")
    .or_default(default_config)
    .map(lambda cfg: resolve(cfg.get("database_url"), default=default_config["database_url"]))
    .unwrap()
)
```

### Safe Data Processing

```python
from logerr import Option
from logerr.utils import nullable, validate, attribute

def process_user_data(data: dict) -> Option[str]:
    """Extract and format user display name using functional utilities."""
    return (
        nullable(data.get("user"))
        .then(lambda user: nullable(user.get("profile")))  
        .then(lambda profile: nullable(profile.get("name")))
        .then(lambda name: validate(name, lambda n: len(n.strip()) > 0, None))
        .map(str.title)
        .map(lambda name: f"👋 {name}")  # Add greeting emoji
    )

def get_user_role(data: dict) -> Option[str]:
    """Get user role with fallback using attribute utility."""
    return (
        nullable(data.get("user"))  
        .map(lambda user: attribute(user, "role", "member"))  # Default to "member"
        .filter(lambda role: role in ["admin", "member", "guest"])
    )

# Usage with functional pipeline
user_data = {"user": {"profile": {"name": "alice smith"}, "role": "admin"}}

greeting = (
    process_user_data(user_data)
    .zip(get_user_role(user_data))  # Combine name and role
    .map(lambda pair: f"{pair[0]} (Role: {pair[1]})")
    .unwrap_or("👋 Anonymous User")
)

print(greeting)  # 👋 Alice Smith (Role: admin)
```

### NoSQL to DataFrame with Data Quality Logging

```python
from logerr.recipes.dataframes import Required, from_mongo
from logerr import configure

# Configure logging for data quality reports
configure(level="INFO")

# Define schema: Required fields must be present, others are optional by default
schema = {
    "user_id": Required[str],      # Must be present - error if missing
    "email": Required[str],        # Must be present - error if missing
    "name": str,                  # Optional[str] by default
    "age": int,                   # Optional[int] by default  
    "bio": str,                   # Optional[str] by default
    "preferences": dict,          # Optional[dict] by default
    "created_at": datetime,       # Optional[datetime] by default
    "tags": List[str],           # Optional[List[str]] by default
}

# Safe MongoDB querying with automatic data quality logging
result = from_mongo(
    collection=db.users,
    query={"status": "active", "last_login": {"$gte": last_month}}, 
    schema=schema,
    log_missing_data=True,        # Enable data quality reporting
    report_name="active_users"
)

# Handle the result functionally
df = (
    result
    .map(lambda df: df[df['age'].notna()])  # Filter out users without age
    .map(lambda df: df.fillna({"bio": "No bio provided"}))  # Fill missing bios
    .unwrap_or_else(lambda error: handle_data_error(error))
)

# Automatic logging output:
# 2024-01-15 14:23:12 | INFO    | Data Quality Summary for 'active_users': 1847/2000 records processed successfully (92.4% success rate)
# 2024-01-15 14:23:12 | WARNING | Field 'bio': 612/2000 missing (30.6% missing rate)  
# 2024-01-15 14:23:12 | ERROR   | Missing required field 'email' in 153/2000 records - excluding from DataFrame
# 2024-01-15 14:23:12 | WARNING | Field 'age': 23 type conversion errors (1.2% of present values)
```

## ⚙️ Configuration

**Core Configuration** (simple and lightweight):

```python
import logerr

# Basic configuration - just the essentials
logerr.configure(enabled=True, level="WARNING")
logerr.configure(level="INFO")  # Just change log level
```

**Advanced Configuration** (requires recipes module):

```python
from logerr.recipes import config

# Advanced configuration with per-library settings
config.configure_advanced({
    "enabled": True,
    "level": "WARNING", 
    "libraries": {
        "myapp.database": {"level": "ERROR"},
        "myapp.api": {"level": "DEBUG"},
        "third_party_lib": {"enabled": False}
    },
    "capture_locals": True,
    "capture_filename": True
})

# Load from configuration file
config.configure_from_confection("config.cfg")
```

## 🧪 Development

This project uses [pixi](https://pixi.sh) for development:

```bash
# Install dependencies
pixi install

# Install with recipes module for advanced patterns and utilities
pixi run -e recipes

# Run tests
pixi run -e dev test

# Run tests with doctests
pixi run -e dev test-all

# Type checking
pixi run -e dev typecheck

# Build documentation
pixi run -e docs docs-build

# Serve documentation locally
pixi run -e docs docs-serve
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

This project builds upon excellent prior work:

- **[MaT1g3R/option](https://github.com/MaT1g3R/option)** - The original Python implementation of Rust-like Option and Result types that inspired this project. `logerr` extends their elegant API design with automatic logging capabilities.
- **[Rust's std::option and std::result](https://doc.rust-lang.org/)** - The foundational design patterns and method names
- **[loguru](https://github.com/Delgan/loguru)** - The excellent logging library that powers our automatic error logging
- **[confection](https://github.com/explosion/confection)** - Flexible configuration management system
- **[tenacity](https://github.com/jd/tenacity)** - Robust retry library that powers our retry decorators and resilient operations