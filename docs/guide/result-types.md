# Result Types

Result types represent operations that can either succeed with a value or fail with an error. This is similar to Rust's `Result<T, E>` type and provides a clean alternative to exception-based error handling.

## The Result Type

A `Result<T, E>` can be one of two variants:

- **`Ok<T>`**: Contains a success value of type `T`
- **`Err<E>`**: Contains an error value of type `E`

## Creating Results

### Direct Construction

```python
from logerr import Ok, Err

# Success case
success_result = Ok(42)
print(success_result.is_ok())    # True
print(success_result.unwrap())   # 42

# Error case - automatically logged
error_result = Err("Database connection failed")
print(error_result.is_err())     # True
print(error_result.unwrap_or(0)) # 0
```

### Factory Functions

The most common way to create Results is through factory functions:

#### `from_callable()`

Wraps a callable that might raise an exception:

```python
import logerr

# Success case
result = logerr.result.from_callable(lambda: int("42"))
print(result.unwrap())  # 42

# Error case - exception caught automatically
result = logerr.result.from_callable(lambda: int("not a number"))
print(result.is_err())  # True
print(result.unwrap_or(0))  # 0
```

#### `from_optional()`

Converts an optional value (might be None) into a Result:

```python
import logerr

data = {"name": "Alice", "age": 30}

# Success case
result = logerr.result.from_optional(data.get("name"), "Name not found")
print(result.unwrap())  # "Alice"

# Error case
result = logerr.result.from_optional(data.get("email"), "Email not found")
print(result.unwrap_or("no-email@example.com"))  # "no-email@example.com"
```

## Checking Result State

```python
from logerr import Ok, Err

success = Ok("hello")
failure = Err("error")

# Check if Ok
print(success.is_ok())     # True
print(failure.is_ok())     # False

# Check if Err
print(success.is_err())    # False
print(failure.is_err())    # True
```

## Extracting Values

### Safe Extraction

```python
from logerr import Ok, Err

success = Ok(42)
failure = Err("oops")

# unwrap() - panics on Err
value = success.unwrap()        # 42
# failure.unwrap()              # Would raise an exception!

# unwrap_or() - provides default for Err
value = success.unwrap_or(0)    # 42
value = failure.unwrap_or(0)    # 0

# unwrap_or_else() - computes default for Err
value = failure.unwrap_or_else(lambda err: len(str(err)))  # 4
```

### Conditional Extraction

```python
from logerr import Ok, Err

def handle_result(result):
    if result.is_ok():
        print(f"Success: {result.unwrap()}")
    else:
        print(f"Error: {result.unwrap_err()}")

handle_result(Ok("working"))     # Success: working
handle_result(Err("broken"))     # Error: broken
```

## Transforming Results

### `map()` - Transform Success Values

```python
from logerr import Ok, Err

# Transform success value
result = Ok("hello").map(str.upper)
print(result.unwrap())  # "HELLO"

# Err passes through unchanged
result = Err("fail").map(str.upper)
print(result.is_err())  # True
```

### `map_err()` - Transform Error Values

```python
from logerr import Ok, Err

# Ok passes through unchanged
result = Ok(42).map_err(str.upper)
print(result.unwrap())  # 42

# Transform error value
result = Err("fail").map_err(str.upper)
print(result.unwrap_err())  # "FAIL"
```

### `and_then()` - Chain Operations

Chain operations that return Results:

```python
import logerr
import json

def parse_json(text: str) -> logerr.Result[dict, str]:
    return logerr.result.from_callable(lambda: json.loads(text))

def get_field(data: dict, field: str) -> logerr.Result[str, str]:
    return logerr.result.from_optional(data.get(field), f"Missing field: {field}")

# Chain multiple operations
result = (Ok('{"name": "Alice", "age": 30}')
    .and_then(parse_json)
    .and_then(lambda data: get_field(data, "name")))

print(result.unwrap())  # "Alice"
```

### `or_else()` - Error Recovery

```python
import logerr

def retry_operation(error):
    """Try an alternative on failure."""
    if "timeout" in str(error):
        return Ok("recovered from timeout")
    return Err(f"permanent failure: {error}")

result = (Err("timeout occurred")
    .or_else(retry_operation))

print(result.unwrap())  # "recovered from timeout"
```

## Method Chaining

Results support fluent method chaining for complex operations:

```python
import logerr
import json
from pathlib import Path

def load_config(path: str) -> logerr.Result[dict, str]:
    """Load and parse configuration file."""
    return (logerr.result.from_callable(lambda: Path(path).read_text())
        .map_err(lambda e: f"Failed to read {path}: {e}")
        .and_then(lambda text: logerr.result.from_callable(lambda: json.loads(text)))
        .map_err(lambda e: f"Failed to parse JSON: {e}"))

def get_database_config(config: dict) -> logerr.Result[str, str]:
    """Extract database URL from config."""
    return (logerr.result.from_optional(config.get("database"), "No database config")
        .and_then(lambda db: logerr.result.from_optional(db.get("url"), "No database URL")))

# Usage
config_result = load_config("app.json")
if config_result.is_ok():
    config = config_result.unwrap()
    db_url = get_database_config(config).unwrap_or("sqlite:///default.db")
    print(f"Database URL: {db_url}")
else:
    print("Failed to load configuration - using defaults")
```

## Pattern Matching with `match()`

Handle both success and error cases in a single expression:

```python
import logerr

def divide(a: float, b: float) -> logerr.Result[float, str]:
    if b == 0:
        return Err("Division by zero")
    return Ok(a / b)

result = divide(10, 2).match(
    ok=lambda value: f"Result: {value}",
    err=lambda error: f"Error: {error}"
)
print(result)  # "Result: 5.0"

result = divide(10, 0).match(
    ok=lambda value: f"Result: {value}",
    err=lambda error: f"Error: {error}"
)
print(result)  # "Error: Division by zero"
```

## Comparison Support

Results can be compared if their contained types support comparison:

```python
from logerr import Ok, Err

# Compare Ok values
assert Ok(1) < Ok(2)
assert Ok("a") < Ok("b")

# Compare Err values
assert Err("a") < Err("b")

# Ok is always greater than Err
assert Ok(1) > Err("anything")
```

## Real-World Example

Here's a complete example showing how Results can be used for file processing:

```python
import logerr
import json
from pathlib import Path
from typing import Dict, List

def read_file(path: str) -> logerr.Result[str, str]:
    """Read file contents."""
    return logerr.result.from_callable(lambda: Path(path).read_text())

def parse_json(content: str) -> logerr.Result[dict, str]:
    """Parse JSON content."""
    return logerr.result.from_callable(lambda: json.loads(content))

def validate_config(config: dict) -> logerr.Result[dict, str]:
    """Validate configuration has required fields."""
    required_fields = ["name", "version", "database"]
    for field in required_fields:
        if field not in config:
            return Err(f"Missing required field: {field}")
    return Ok(config)

def process_config_file(path: str) -> logerr.Result[dict, str]:
    """Complete config file processing pipeline."""
    return (read_file(path)
        .and_then(parse_json)
        .and_then(validate_config))

# Usage
result = process_config_file("config.json")
match result:
    case Ok(config):
        print(f"Loaded config for {config['name']} v{config['version']}")
    case Err(error):
        print(f"Failed to load config: {error}")
        # Error details are automatically logged!
```

This approach provides clear error handling with excellent observability through automatic logging.