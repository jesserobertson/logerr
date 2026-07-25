# logerr

**Rust-like Option and Result types for Python with automatic logging**

[![Tests](https://img.shields.io/badge/tests-807%20passed-green)](https://github.com/jesserobertson/logerr)
[![Coverage](https://img.shields.io/badge/coverage-96%25-brightgreen)](https://github.com/jesserobertson/logerr)
[![Type Checked](https://img.shields.io/badge/mypy-passing-blue)](https://github.com/jesserobertson/logerr)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue)](https://github.com/jesserobertson/logerr)

`logerr` brings the power of Rust's `Option<T>` and `Result<T, E>` types to Python, with automatic logging of error cases using [loguru](https://github.com/Delgan/loguru). Write clean, functional error-handling code while maintaining excellent observability.

## 🌟 Features

- **🦀 Rust-like Types**: Familiar `Option<T>` and `Result<T, E>` with method chaining
- **🔗 Full Combinator Set**: `zip()`, `flatten()`, `and_()`, `or_()`, `ok()`, `err()` alongside the core `map`/`then`/`filter`
- **🪵 Automatic Logging**: Error cases logged automatically with configurable levels  
- **⚙️ Highly Configurable**: Per-library settings via [confection](https://github.com/explosion/confection)
- **🔒 Type Safe**: Full mypy support with proper generic types
- **🧪 Well Tested**: 500+ tests including property-based tests and comprehensive doctests
- **🚀 Clean API**: Discoverable, IDE-friendly interface

## 🚀 Quick Start

```python
>>> from logerr import Result, Ok, Err, Some, Nothing

>>> # Simple successful case
>>> success = Ok(42)
>>> success.map(lambda x: x * 2).unwrap()
84

>>> # Error case with fallback
>>> error = Err("something failed")
>>> error.unwrap_or("default value")
'default value'

>>> # Chain operations elegantly
>>> Ok("hello").map(str.upper).map(len).unwrap()
5

```

**✨ The key difference:** Errors are **automatically logged** with full context - no manual logging required!

See it in action - no manual logging call, just automatic capture of the error context:

```python
>>> import sys
>>> from loguru import logger
>>> import logerr
>>> _ = logerr.configure(enabled=True, level="ERROR")  # deterministic for this demo
>>> handler_id = logger.add(sys.stdout, format="{level} | {message}")

>>> from logerr import Err
>>> _ = Err("Database connection failed")  # doctest: +ELLIPSIS
ERROR | Result error in ...Database connection failed

>>> _ = logger.remove(handler_id)
>>> logerr.reset_config()

```

```python
>>> from logerr import Option

>>> # Work with optional values using functional pipeline
>>> user_data = {"name": "Alice"}

>>> # Functional pipeline for nullable values
>>> contact = (
...     Option.from_nullable(user_data.get("email"))
...     .filter(lambda email: "@" in email)  # Validate email format
...     .unwrap_or("no-email@example.com")
... )
>>> print(contact)
no-email@example.com

>>> # Chain operations elegantly with automatic error handling
>>> processed = (
...     Ok("hello world")
...     .map(str.upper)           # Ok("HELLO WORLD")  
...     .map(lambda s: s.split()) # Ok(["HELLO", "WORLD"])
...     .map(len)                 # Ok(2)
...     .unwrap_or(0)            # 2
... )
>>> print(processed)
2

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
# Install retry patterns (tenacity)
pixi run -e retry  # or: pip install "logerr[retry]"

# Install dataframe/table conversion utilities (pymongo, pandas)
pixi run -e tables  # or: pip install "logerr[tables]"

# Use in your code
from logerr.recipes import retry, config

@retry.on_err()  # retries on Err, default: 3 attempts with exponential backoff
def flaky_operation() -> Result[int, str]:
    return Ok(42)

# Functional utilities (no extra install needed - these are core)
from logerr.utilities import validate, pipe, try_chain

config.configure_advanced({"libraries": {"my_module": {"level": "DEBUG"}}})

# NoSQL to DataFrame conversion with data quality logging
import pandas as pd
from logerr.recipes.dataframes import Required, from_mongo

schema = {"user_id": Required[str], "email": Required[str], "name": str}
df = from_mongo(db.users, {"status": "active"}, schema=schema).unwrap_or(pd.DataFrame())
```

## 🔍 Why logerr?

### See the Difference

**Traditional approach** (manual logging required):
```python
>>> import json
>>> def load_config():
...     try:
...         with open("config.json") as f:
...             return json.load(f)
...     except Exception as e:
...         print(f"Failed to load config: {e}")  # Manual logging
...         return None

>>> config = load_config()  # doctest: +SKIP
>>> if config is None:  # doctest: +SKIP
...     print("Using defaults")  # doctest: +SKIP
```

**With logerr** (automatic logging + functional style):
```python
>>> from logerr import Result
>>> from logerr.utilities import execute
>>> import json

>>> def load_config():
...     return execute(lambda: json.load(open("config.json")))

>>> # Functional pipeline with error recovery
>>> config = (
...     load_config()
...     .unwrap_or({})  # Fallback to empty config
... )
>>> print(type(config))
<class 'dict'>

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

Here's a "full-stack" pipeline that combines retry logic, NoSQL loading, and
schema validation - and gets observability into all three for free:

```python
import pandas as pd
from logerr import Result, configure
from logerr.recipes import retry
from logerr.recipes.dataframes import Required, from_mongo

configure(level="INFO")  # surface retry attempts and data quality issues as they happen

# Required fields error if missing; other fields are optional by default
schema = {"user_id": Required[str], "email": Required[str], "age": int}

@retry.on_err()  # retries on connection failure: 3 attempts, exponential backoff
def load_active_users() -> Result:
    return from_mongo(
        db.users, {"status": "active"}, schema=schema, report_name="active_users"
    )

df = load_active_users().unwrap_or_else(lambda error: pd.DataFrame())
```

```
# What you'd see in the logs (abbreviated - one ERROR line is logged per
# missing occurrence, not aggregated):
#
# INFO    | load_active_users succeeded after 2 attempts
# ERROR   | Missing required field 'email' in document
# INFO    | Data Quality Summary for 'active_users': 1847/2000 records processed successfully (92.4% success rate)
# WARNING | Field 'age': 43/2000 missing (2.2% missing rate)
```

No manual logging calls anywhere in that pipeline - the retry attempts,
the missing-field errors, and the data quality summary are all captured
automatically.

See the [Examples guide](https://jesserobertson.github.io/logerr/guide/examples/)
for more: web applications, file processing pipelines, configuration
management, and circuit-breaker patterns.

## ⚙️ Configuration

**Core Configuration** (simple and lightweight):

```python
>>> import logerr

>>> # Basic configuration - just the essentials
>>> result = logerr.configure(enabled=True, level="WARNING")
>>> result.is_ok()
True

>>> # Just change log level
>>> result = logerr.configure(level="INFO")
>>> result.is_ok()
True

```

**Advanced Configuration** (per-library settings, custom formats, file-based
config — no extra install needed, `confection` is already a core dependency;
this just lives under `logerr.recipes.config` to keep the top-level API
small):

```python
from logerr.recipes.config import configure_advanced, configure_from_confection

configure_advanced({
    "level": "WARNING",
    "libraries": {
        "myapp.database": {"level": "ERROR"},
        "myapp.api": {"level": "DEBUG"},
        "third_party_lib": {"enabled": False},
    },
    "capture_locals": True,
})

# Or load the same settings from a confection config file (see the
# Configuration guide for the expected [logerr] file format)
configure_from_confection("config.cfg")
```

## 🧪 Development

This project uses [pixi](https://pixi.sh) for development:

```bash
# Install dependencies
pixi install

# Install with retry/tables extras for advanced patterns and utilities
pixi install -e retry
pixi install -e tables

# Run fast tests
pixi run -e dev test fast

# Run all tests, including doctests
pixi run -e dev test all

# Type checking
pixi run -e dev quality typecheck

# Build documentation (default environment - combines dev + docs features)
pixi run docs build

# Serve documentation locally
pixi run docs serve
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