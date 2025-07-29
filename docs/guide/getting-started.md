# Getting Started

This guide will help you understand the core concepts of `logerr` and get you up and running quickly.

## Core Concepts

`logerr` provides two main types that represent different kinds of "maybe" values:

- **`Result<T, E>`**: Represents success (`Ok<T>`) or failure (`Err<E>`) 
- **`Option<T>`**: Represents presence (`Some<T>`) or absence (`Nothing`)

Both types support method chaining and automatically log error/absence cases for better observability.

## Installation

Currently, install from source:

```bash
git clone https://github.com/jesserobertson/logerr
cd logerr
pixi install  # If you have pixi
# or
pip install -e .
```

## Basic Usage

### Import the Types

```python
# Direct imports for the main types
from logerr import Ok, Err, Some, Nothing

# Import the main types
from logerr import Result, Option
```

### Working with Results

Results represent operations that might succeed or fail:

```python
from logerr import Ok, Err

# Create Results directly
success = Ok(42)
failure = Err("something went wrong")

# Check the state
print(success.is_ok())    # True
print(failure.is_err())   # True

# Extract values safely
print(success.unwrap())           # 42
print(failure.unwrap_or(0))       # 0

# Chain operations
result = (Ok(5)
    .map(lambda x: x * 2)         # Ok(10)
    .map(str)                     # Ok("10")
    .unwrap_or("failed"))         # "10"
```

### Working with Options

Options represent values that might be present or absent:

```python
from logerr import Some, Nothing

# Create Options directly
present = Some("hello")
absent = Nothing.empty()  # Use .empty() to avoid logging

# Check the state
print(present.is_some())   # True
print(absent.is_nothing()) # True

# Extract values safely
print(present.unwrap())            # "hello"
print(absent.unwrap_or("default")) # "default"

# Chain operations
result = (Some("hello world")
    .map(str.upper)               # Some("HELLO WORLD")
    .map(lambda s: s.split())     # Some(["HELLO", "WORLD"])
    .map(len)                     # Some(2)
    .unwrap_or(0))                # 2
```

## Factory Functions

The cleanest way to create Results and Options is through factory functions:

### Result Factories

```python
from logerr import Result

# From a callable that might raise
result_value = Result.from_callable(lambda: int("42"))
print(result_value.unwrap())  # 42

result_value = Result.from_callable(lambda: int("not a number"))
print(result_value.is_err())  # True - exception was caught and logged

# From an optional value
data = {"name": "Alice"}
result_value = Result.from_optional(data.get("name"), "name not found")
print(result_value.unwrap())  # "Alice"

result_value = Result.from_optional(data.get("age"), "age not found") 
print(result_value.unwrap_or(0))  # 0
```

### Option Factories

```python
from logerr import Option

# From a nullable value
config = {"database_url": "postgres://localhost/db"}
option_value = Option.from_nullable(config.get("database_url"))
print(option_value.unwrap())  # "postgres://localhost/db"

option_value = Option.from_nullable(config.get("missing_key"))
print(option_value.is_nothing())  # True

# From a callable that might return None
option_value = Option.from_callable(lambda: config.get("database_url"))
print(option_value.is_some())  # True

# From a predicate
option_value = Option.from_predicate(42, lambda x: x > 0)
print(option_value.unwrap())  # 42

option_value = Option.from_predicate(-5, lambda x: x > 0)
print(option_value.is_nothing())  # True
```

## Automatic Logging

One of the key features of `logerr` is automatic logging of error cases:

```python
from logerr import Err, Result, configure

# This automatically logs the error
error_result = Err("database connection failed")

# This also logs when the callable fails
result_value = Result.from_callable(lambda: 1 / 0)

# Configure logging levels
configure({
    "level": "WARNING",
    "libraries": {
        "myapp": {"level": "DEBUG"}
    }
})
```

## Method Chaining

Both Result and Option types support fluent method chaining:

```python
from logerr import Result
import json

# Complex pipeline with error handling
result_value = (Result.from_callable(lambda: open("config.json").read())
    .and_then(lambda text: Result.from_callable(lambda: json.loads(text)))
    .map(lambda config: config.get("database_url"))
    .and_then(lambda url: Result.from_optional(url, "No database URL in config"))
    .unwrap_or("sqlite:///default.db"))

print(f"Database URL: {result_value}")
```

## Error Recovery

Handle errors gracefully with recovery methods:

```python
from logerr import Result, Err

def retry_operation(error):
    """Retry logic for failed operations."""
    if "timeout" in str(error):
        return Result.from_callable(lambda: "retry successful")
    return Err("permanent failure")

result_value = (Result.from_callable(lambda: raise_timeout_error())
    .or_else(retry_operation)
    .unwrap_or("fallback value"))
```

## Next Steps

- Learn more about [Result Types](result-types.md)
- Explore [Option Types](option-types.md) 
- Customize behavior with [Configuration](configuration.md)
- See real-world [Examples](examples.md)