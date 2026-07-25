# Configuration

`logerr` has two configuration layers:

1. **Basic configuration** (`logerr.configure()`) — a small, flat set of options
   (`enabled`, `level`) exported from the top-level `logerr` package. This is
   all most applications need.
2. **Advanced configuration** (`logerr.recipes.config`) — per-library log
   levels, custom formats, context-capture flags, and file-based configuration
   via [confection](https://github.com/explosion/confection). Confection is
   already a core dependency of `logerr`, so advanced configuration does
   **not** require installing the `recipes` extra — the functionality simply
   lives under `logerr.recipes.config` for API-surface reasons (it keeps the
   top-level `logerr` namespace small).

## Basic Configuration

`logerr.configure()` takes plain keyword arguments — there is no dictionary
argument and no `libraries` sub-config at this level:

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

An invalid log level returns `Err(ValueError(...))` instead of raising:

```python
>>> import logerr
>>> result = logerr.configure(level="NOT_A_LEVEL")
>>> result.is_err()
True

```

### Inspecting and resetting basic configuration

```python
>>> import logerr
>>> _ = logerr.configure(level="INFO")
>>> config = logerr.get_config()
>>> config.level
'INFO'
>>> config.enabled
True

>>> logerr.reset_config()
>>> logerr.get_config().level
'ERROR'

```

## Advanced Configuration

For per-library log levels, custom formats, context-capture control, and
file-based configuration, use `logerr.recipes.config`. Nothing extra needs to
be installed — import it directly:

```python
>>> from logerr.recipes.config import configure_advanced

>>> result = configure_advanced({
...     "level": "WARNING",
...     "libraries": {
...         "myapp.database": {"level": "DEBUG"},
...         "third_party_lib": {"enabled": False},
...     },
...     "capture_locals": True,
... })
>>> result.is_ok()
True

```

`configure_advanced()` accepts a single dictionary with these keys (all
optional):

| Key | Type | Description |
|-----|------|-------------|
| `enabled` | `bool` | Enable/disable all logging |
| `level` | `str` | Global log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |
| `format` | `str` | Custom loguru format string |
| `libraries` | `dict[str, dict]` | Per-library overrides, keyed by library name |
| `capture_function_name` | `bool` | Include function name in logs (default `True`) |
| `capture_filename` | `bool` | Include filename in logs (default `True`) |
| `capture_lineno` | `bool` | Include line number in logs (default `True`) |
| `capture_locals` | `bool` | Include local variables — expensive (default `False`) |

Each entry in `libraries` accepts the same `enabled`/`level` keys, scoped to
that library name:

```python
>>> from logerr.recipes.config import configure_advanced, get_library_config

>>> _ = configure_advanced({
...     "libraries": {
...         "mylib": {"enabled": True, "level": "DEBUG"},
...     },
... })
>>> get_library_config("mylib")
{'enabled': True, 'level': 'DEBUG'}

```

### Inspecting per-library configuration

```python
>>> from logerr.recipes.config import (
...     configure_advanced,
...     should_log_for_library,
...     get_log_level_for_library,
... )

>>> _ = configure_advanced({
...     "level": "WARNING",
...     "libraries": {
...         "chatty_lib": {"enabled": False},
...         "myapp.database": {"level": "DEBUG"},
...     },
... })

>>> should_log_for_library("chatty_lib")
False
>>> get_log_level_for_library("myapp.database")
'DEBUG'
>>> get_log_level_for_library("some.other.module")  # falls back to global level
'WARNING'

```

### Resetting advanced configuration

```python
>>> from logerr.recipes.config import reset_advanced_config, get_advanced_config
>>> reset_advanced_config()
>>> config = get_advanced_config()
>>> config.level
'ERROR'
>>> config.libraries
{}

```

### Keeping basic and advanced configuration in sync

`configure_advanced()` does **not** automatically update the basic
`logerr.configure()` state (they are independent stores). If you use advanced
configuration but still want `logerr.get_config()` to reflect the global
`enabled`/`level` values, call `sync_core_config()`:

```python
>>> from logerr.recipes.config import configure_advanced, sync_core_config, reset_advanced_config
>>> from logerr import get_config, reset_config
>>> reset_advanced_config()
>>> reset_config()
>>> _ = configure_advanced({"level": "DEBUG", "enabled": False})
>>> sync_core_config()
>>> get_config().level
'DEBUG'
>>> get_config().enabled
False

>>> # Restore defaults so later examples aren't affected by enabled=False
>>> reset_advanced_config()
>>> reset_config()

```

## File-Based Configuration

`configure_from_confection()` loads advanced configuration from a confection
config file. Confection files use an INI-style syntax with dotted section
names for nesting — **not** raw JSON. The file must have a top-level
`[logerr]` section; per-library overrides need an explicit (even if empty)
`[logerr.libraries]` section before the per-library subsections:

```ini
[logerr]
enabled = true
level = "WARNING"

[logerr.libraries]

[logerr.libraries.myapp]
level = "DEBUG"

[logerr.libraries.external]
enabled = false
```

Load it with:

```python
from logerr.recipes.config import configure_from_confection

result = configure_from_confection("logerr.cfg")
```

Note that this is `logerr.recipes.config.configure_from_confection` — there is
no `logerr.configure_from_confection()` at the top level.

If the file doesn't exist, or the section can't be parsed, `Err(Exception)` is
returned rather than raising:

```python
>>> from logerr.recipes.config import configure_from_confection
>>> result = configure_from_confection("does-not-exist.cfg")
>>> result.is_err()
True

```

## Log Levels

`logerr` supports standard Python/loguru logging levels:

- `DEBUG`: Detailed information, typically of interest only when diagnosing problems
- `INFO`: Confirmation that things are working as expected
- `WARNING`: An indication that something unexpected happened
- `ERROR`: Due to a more serious problem, the software has not been able to perform some function
- `CRITICAL`: A serious error, indicating that the program itself may be unable to continue

```python
>>> import logerr
>>> from logerr import Err, Nothing

>>> _ = logerr.configure(level="DEBUG")
>>> _ = Nothing("Missing optional config value")  # logged at DEBUG level

>>> _ = logerr.configure(level="ERROR")
>>> _ = Err("Database connection failed")  # logged at ERROR level

>>> _ = logerr.configure(level="ERROR")  # restore default for later examples

```

## Integration with loguru

`logerr` uses `loguru` for the actual logging. You can configure loguru
separately for additional control (handlers, sinks, rotation, etc.):

```python
import logerr
from loguru import logger

# Configure loguru
logger.remove()  # Remove default handler
logger.add("app.log", rotation="1 MB", level="INFO")
logger.add("errors.log", level="ERROR")

# Configure logerr's own level/enabled flag
logerr.configure(level="INFO")

# Now logerr will use your loguru configuration
from logerr import Err
Err("This will go to both app.log and errors.log")
```

## Configuration Best Practices

### 1. Use environment-specific configuration

Prefer file-based configuration for per-environment overrides, falling back
to basic configuration if no file is present:

```python
import os
from logerr.recipes.config import configure_from_confection
import logerr

env = os.getenv("ENV", "development")
config_file = f"config/{env}.cfg"

result = configure_from_confection(config_file)
if result.is_err():
    # Fallback to basic configuration
    if env == "production":
        logerr.configure(level="ERROR")
    else:
        logerr.configure(level="DEBUG")
```

### 2. Configure early

Configure `logerr` as early as possible in your application, before other
modules that raise `Err`/`Nothing` are imported and used:

```python
# main.py
import logerr

def main():
    # Configure logging first
    logerr.configure(level="INFO")

    # Then import and run your application
    from myapp import app
    app.run()

if __name__ == "__main__":
    main()
```

### 3. Only reach for advanced configuration when you need it

If you just need a global on/off switch and a single log level,
`logerr.configure()` is enough. Reach for
`logerr.recipes.config.configure_advanced()` only when you need per-library
levels, custom formats, or context-capture control:

```python
from logerr.recipes.config import configure_advanced

configure_advanced({
    "level": "WARNING",
    "libraries": {
        "myapp.database": {"level": "DEBUG", "capture_locals": True},
        "myapp.auth": {"level": "WARNING"},
        "requests": {"level": "ERROR"},
        "chatty_lib": {"enabled": False},
    },
})
```
