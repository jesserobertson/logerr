# Configuration

`logerr` provides extensive configuration options to customize logging behavior for different libraries, modules, and use cases. Configuration is managed through the `confection` library, allowing both programmatic and file-based configuration.

## Quick Configuration

### Basic Configuration

```python
>>> import logerr

>>> # Configure global logging level  
>>> result = logerr.configure(level="WARNING")
>>> result.is_ok()
True

>>> # Disable logging entirely
>>> result = logerr.configure(enabled=False)  
>>> result.is_ok()
True

>>> # Re-enable for other examples
>>> result = logerr.configure(enabled=True)
>>> result.is_ok()
True

```

### Per-Library Configuration

Configure different logging behaviors for different parts of your application:

```python
import logerr

logerr.configure({
    "level": "ERROR",  # Global default
    "libraries": {
        "myapp.database": {"level": "DEBUG"},
        "myapp.auth": {"level": "WARNING"},
        "third_party_lib": {"enabled": False}
    }
})
```

## Configuration Options

### Global Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | `bool` | `True` | Enable/disable all logging |
| `level` | `str` | `"ERROR"` | Global log level |
| `format` | `str` | `None` | Custom log format string |

### Context Capture Settings

Control what context information is captured with log messages:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `capture_function_name` | `bool` | `True` | Include function name in logs |
| `capture_filename` | `bool` | `True` | Include filename in logs |
| `capture_lineno` | `bool` | `True` | Include line number in logs |
| `capture_locals` | `bool` | `False` | Include local variables (expensive) |

### Per-Library Settings

Each library can have its own configuration under the `libraries` key:

```python
logerr.configure({
    "libraries": {
        "mylib": {
            "enabled": True,
            "level": "DEBUG",
            "format": "{time} | {level} | {name} | {message}",
            "capture_locals": True
        }
    }
})
```

## Log Levels

`logerr` supports standard Python logging levels:

- `DEBUG`: Detailed information, typically of interest only when diagnosing problems
- `INFO`: Confirmation that things are working as expected
- `WARNING`: An indication that something unexpected happened
- `ERROR`: Due to a more serious problem, the software has not been able to perform some function
- `CRITICAL`: A serious error, indicating that the program itself may be unable to continue

```python
import logerr
from logerr import Err, Nothing

# Configure different levels
logerr.configure({"level": "DEBUG"})

# These will be logged at DEBUG level
Nothing("Missing optional config value")

logerr.configure({"level": "ERROR"})

# This will be logged at ERROR level
Err("Database connection failed")
```

## File-Based Configuration

### Using confection Config Files

Create a configuration file (e.g., `logerr.cfg`):

```ini
[logerr]
enabled = true
level = "WARNING"
capture_locals = false

[logerr.libraries.myapp]
level = "DEBUG"
enabled = true

[logerr.libraries.external]
enabled = false
```

Load the configuration:

```python
import logerr

logerr.configure_from_confection("logerr.cfg")
```

### JSON Configuration

You can also use JSON files with confection:

```json
{
  "logerr": {
    "enabled": true,
    "level": "ERROR",
    "libraries": {
      "myapp.core": {
        "level": "DEBUG",
        "capture_locals": true
      },
      "myapp.utils": {
        "level": "WARNING"
      }
    }
  }
}
```

## Dynamic Configuration

### Runtime Configuration Changes

Configuration can be updated at runtime:

```python
import logerr

# Initial configuration
logerr.configure({"level": "ERROR"})

# Later in your application...
if debug_mode:
    logerr.configure({"level": "DEBUG", "capture_locals": True})
```

### Configuration Inspection

```python
import logerr

# Get current configuration
config = logerr.get_config()
print(f"Current level: {config.level}")
print(f"Logging enabled: {config.enabled}")

# Reset to defaults
logerr.reset_config()
```

## Advanced Configuration Examples

### Environment-Based Configuration

```python
import os
import logerr

# Configure based on environment
env = os.getenv("ENVIRONMENT", "production")

if env == "development":
    logerr.configure({
        "level": "DEBUG",
        "capture_locals": True,
        "libraries": {
            "myapp": {"level": "DEBUG"}
        }
    })
elif env == "staging":
    logerr.configure({
        "level": "INFO",
        "libraries": {
            "myapp": {"level": "INFO"}
        }
    })
else:  # production
    logerr.configure({
        "level": "ERROR",
        "capture_locals": False
    })
```

### Module-Specific Configuration

```python
import logerr

# Configure different modules differently
logerr.configure({
    "level": "WARNING",
    "libraries": {
        # Database operations - log everything
        "myapp.database": {
            "level": "DEBUG",
            "capture_locals": True
        },
        
        # Authentication - security sensitive
        "myapp.auth": {
            "level": "WARNING",
            "capture_locals": False  # Don't capture passwords, etc.
        },
        
        # Third-party library - only errors
        "requests": {
            "level": "ERROR"
        },
        
        # Disable logging for noisy library
        "chatty_lib": {
            "enabled": False
        }
    }
})
```

### Custom Log Formats

```python
import logerr

# Custom format with more context
logerr.configure({
    "format": "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
    "capture_function_name": True,
    "capture_lineno": True
})

# Minimal format for production
logerr.configure({
    "format": "{time:HH:mm:ss} | {level} | {message}",
    "capture_function_name": False,
    "capture_filename": False,
    "capture_lineno": False
})
```

## Performance Considerations

### Expensive Options

Some configuration options can impact performance:

```python
import logerr

# These options are expensive - use sparingly
logerr.configure({
    "capture_locals": True,    # Captures all local variables
    "level": "DEBUG"           # Generates more log messages
})

# For production, prefer:
logerr.configure({
    "capture_locals": False,
    "level": "ERROR"
})
```

### Selective Library Logging

Enable detailed logging only where needed:

```python
import logerr

# Global configuration - minimal logging
logerr.configure({
    "level": "ERROR",
    "capture_locals": False,
    "libraries": {
        # Enable detailed logging only for critical components
        "myapp.payment": {
            "level": "DEBUG",
            "capture_locals": True
        },
        "myapp.user_auth": {
            "level": "INFO"
        }
    }
})
```

## Integration with loguru

`logerr` uses `loguru` for the actual logging. You can configure loguru separately for additional control:

```python
import logerr
from loguru import logger

# Configure loguru
logger.remove()  # Remove default handler
logger.add("app.log", rotation="1 MB", level="INFO")
logger.add("errors.log", level="ERROR")

# Configure logerr
logerr.configure({"level": "INFO"})

# Now logerr will use your loguru configuration
from logerr import Err
Err("This will go to both app.log and errors.log")
```

## Configuration Best Practices

### 1. Use Environment-Specific Configuration

```python
import logerr
import os

# Load from environment-specific config file
env = os.getenv("ENV", "development")
config_file = f"config/{env}.cfg"

try:
    logerr.configure_from_confection(config_file)
except FileNotFoundError:
    # Fallback to programmatic configuration
    if env == "production":
        logerr.configure({"level": "ERROR"})
    else:
        logerr.configure({"level": "DEBUG"})
```

### 2. Configure Early

Configure `logerr` as early as possible in your application:

```python
# main.py
import logerr

def main():
    # Configure logging first
    logerr.configure({"level": "INFO"})
    
    # Then import and run your application
    from myapp import app
    app.run()

if __name__ == "__main__":
    main()
```

### 3. Use Hierarchical Library Names

Organize your library configuration hierarchically:

```python
logerr.configure({
    "libraries": {
        # Top-level configuration
        "myapp": {"level": "INFO"},
        
        # More specific configuration
        "myapp.database": {"level": "DEBUG"},
        "myapp.database.migrations": {"level": "WARNING"},
        
        # Feature-specific configuration
        "myapp.features.payments": {"level": "DEBUG", "capture_locals": True},
        "myapp.features.auth": {"level": "WARNING"},
    }
})
```

This hierarchical approach allows you to configure logging at different levels of granularity while maintaining organization.