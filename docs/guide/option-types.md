# Option Types

Option types represent values that might be present or absent. This is similar to Rust's `Option<T>` type and provides a clean alternative to using `None` values directly.

## The Option Type

An `Option<T>` can be one of two variants:

- **`Some<T>`**: Contains a value of type `T`
- **`Nothing`**: Represents the absence of a value

## Creating Options

### Direct Construction

```python
from logerr import Some, Nothing

# Present value
present = Some("hello")
print(present.is_some())     # True
print(present.unwrap())      # "hello"

# Absent value - use empty() to avoid logging
absent = Nothing.empty()
print(absent.is_nothing())   # True
print(absent.unwrap_or("default"))  # "default"

# Absent value with automatic logging (when unexpected)
logged_absent = Nothing("Expected value was missing")
print(logged_absent.unwrap_or("fallback"))  # "fallback"
```

### Factory Functions

The most common way to create Options is through factory functions:

#### `from_nullable()`

Converts a potentially None value into an Option:

```python
import logerr

config = {"database_url": "postgres://localhost/db", "debug": True}

# Present value
option = logerr.option.from_nullable(config.get("database_url"))
print(option.unwrap())  # "postgres://localhost/db"

# Absent value
option = logerr.option.from_nullable(config.get("missing_key"))
print(option.is_nothing())  # True
print(option.unwrap_or("default"))  # "default"
```

#### `from_callable()`

Wraps a callable that might return None:

```python
import logerr

# Function that might return None
def find_user(user_id: int):
    users = {1: "Alice", 2: "Bob"}
    return users.get(user_id)

# Present value
option = logerr.option.from_callable(lambda: find_user(1))
print(option.unwrap())  # "Alice"

# Absent value
option = logerr.option.from_callable(lambda: find_user(99))
print(option.is_nothing())  # True
```

#### `from_predicate()`

Creates an Option based on whether a predicate is satisfied:

```python
import logerr

# Predicate satisfied
option = logerr.option.from_predicate(42, lambda x: x > 0)
print(option.unwrap())  # 42

# Predicate not satisfied
option = logerr.option.from_predicate(-5, lambda x: x > 0)
print(option.is_nothing())  # True

# With custom message for logging
option = logerr.option.from_predicate(-5, lambda x: x > 0, "Value must be positive")
print(option.unwrap_or(0))  # 0
```

## Checking Option State

```python
from logerr import Some, Nothing

present = Some("value")
absent = Nothing.empty()

# Check if Some
print(present.is_some())     # True
print(absent.is_some())      # False

# Check if Nothing
print(present.is_nothing())  # False
print(absent.is_nothing())   # True
```

## Extracting Values

### Safe Extraction

```python
from logerr import Some, Nothing

present = Some(42)
absent = Nothing.empty()

# unwrap() - panics on Nothing
value = present.unwrap()        # 42
# absent.unwrap()               # Would raise an exception!

# unwrap_or() - provides default for Nothing
value = present.unwrap_or(0)    # 42
value = absent.unwrap_or(0)     # 0

# unwrap_or_else() - computes default for Nothing
value = absent.unwrap_or_else(lambda: 100)  # 100
```

### Conditional Extraction

```python
from logerr import Some, Nothing

def handle_option(option):
    if option.is_some():
        print(f"Found: {option.unwrap()}")
    else:
        print("Nothing found")

handle_option(Some("treasure"))      # Found: treasure
handle_option(Nothing.empty())       # Nothing found
```

## Transforming Options

### `map()` - Transform Present Values

```python
from logerr import Some, Nothing

# Transform present value
option = Some("hello").map(str.upper)
print(option.unwrap())  # "HELLO"

# Nothing passes through unchanged
option = Nothing.empty().map(str.upper)
print(option.is_nothing())  # True
```

### `filter()` - Conditional Filtering

```python
from logerr import Some, Nothing

# Value passes filter
option = Some(42).filter(lambda x: x > 0)
print(option.unwrap())  # 42

# Value fails filter
option = Some(-5).filter(lambda x: x > 0)
print(option.is_nothing())  # True

# Nothing passes through unchanged
option = Nothing.empty().filter(lambda x: x > 0)
print(option.is_nothing())  # True
```

### `and_then()` - Chain Operations

Chain operations that return Options:

```python
import logerr

def find_user(user_id: int) -> logerr.Option[dict]:
    users = {1: {"name": "Alice", "age": 30}, 2: {"name": "Bob", "age": 25}}
    return logerr.option.from_nullable(users.get(user_id))

def get_user_name(user: dict) -> logerr.Option[str]:
    return logerr.option.from_nullable(user.get("name"))

# Chain multiple operations
result = (Some(1)
    .and_then(find_user)
    .and_then(get_user_name))

print(result.unwrap())  # "Alice"
```

### `or_else()` - Alternative Values

```python
import logerr

def get_default_config():
    """Provide default configuration."""
    return Some({"theme": "default", "language": "en"})

# Use alternative when nothing
config = (Nothing.empty()
    .or_else(get_default_config))

print(config.unwrap())  # {"theme": "default", "language": "en"}
```

## Method Chaining

Options support fluent method chaining for complex operations:

```python
import logerr

def parse_int(s: str) -> logerr.Option[int]:
    """Parse string to int, returning None on failure."""
    try:
        return Some(int(s))
    except ValueError:
        return Nothing.empty()

def is_even(n: int) -> bool:
    return n % 2 == 0

# Complex pipeline
result = (logerr.option.from_nullable("42")
    .and_then(parse_int)
    .filter(is_even)
    .map(lambda x: x * 2)
    .unwrap_or(0))

print(result)  # 84
```

## Pattern Matching with `match()`

Handle both present and absent cases in a single expression:

```python
import logerr

def find_item(items: list, predicate):
    for item in items:
        if predicate(item):
            return Some(item)
    return Nothing.empty()

items = [1, 2, 3, 4, 5]
result = find_item(items, lambda x: x > 3).match(
    some=lambda value: f"Found: {value}",
    nothing=lambda: "Not found"
)
print(result)  # "Found: 4"

result = find_item(items, lambda x: x > 10).match(
    some=lambda value: f"Found: {value}",
    nothing=lambda: "Not found"
)
print(result)  # "Not found"
```

## Comparison Support

Options can be compared if their contained types support comparison:

```python
from logerr import Some, Nothing

# Compare Some values
assert Some(1) < Some(2)
assert Some("a") < Some("b")

# Some is always greater than Nothing
assert Some(1) > Nothing.empty()
assert Nothing.empty() == Nothing.empty()
```

## Working with Collections

Options work well with collection operations:

```python
import logerr
from typing import List

def first_even(numbers: List[int]) -> logerr.Option[int]:
    """Find the first even number in a list."""
    for num in numbers:
        if num % 2 == 0:
            return Some(num)
    return Nothing.empty()

def safe_divide(a: int, b: int) -> logerr.Option[float]:
    """Safe division returning None for division by zero."""
    if b == 0:
        return Nothing("Division by zero")
    return Some(a / b)

# Process a list of numbers
numbers = [1, 3, 7, 8, 9, 12]
result = (first_even(numbers)
    .and_then(lambda x: safe_divide(100, x))
    .map(lambda x: round(x, 2))
    .unwrap_or(0.0))

print(result)  # 12.5 (100 / 8)
```

## Real-World Example

Here's a complete example showing how Options can be used for configuration management:

```python
import logerr
from typing import Dict, Optional
import os

class ConfigManager:
    def __init__(self, config_dict: Dict[str, str]):
        self.config = config_dict
    
    def get_string(self, key: str) -> logerr.Option[str]:
        """Get a string configuration value."""
        return logerr.option.from_nullable(self.config.get(key))
    
    def get_int(self, key: str) -> logerr.Option[int]:
        """Get an integer configuration value."""
        return (self.get_string(key)
            .and_then(lambda s: logerr.option.from_callable(lambda: int(s))))
    
    def get_bool(self, key: str) -> logerr.Option[bool]:
        """Get a boolean configuration value."""
        return (self.get_string(key)
            .map(str.lower)
            .filter(lambda s: s in ["true", "false"])
            .map(lambda s: s == "true"))

# Usage
config = ConfigManager({
    "database_url": "postgres://localhost/mydb",
    "port": "5432",
    "debug": "true",
    "timeout": "not_a_number"
})

# Get values with sensible defaults
db_url = config.get_string("database_url").unwrap_or("sqlite:///default.db")
port = config.get_int("port").unwrap_or(8080)
debug = config.get_bool("debug").unwrap_or(False)
timeout = config.get_int("timeout").unwrap_or(30)  # "not_a_number" -> default

print(f"Database: {db_url}")  # postgres://localhost/mydb
print(f"Port: {port}")        # 5432
print(f"Debug: {debug}")      # True
print(f"Timeout: {timeout}")  # 30
```

This approach provides clean handling of optional values with excellent observability through automatic logging when values are unexpectedly absent.