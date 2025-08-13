# Examples

This page contains real-world examples showing how to use `logerr` effectively in different scenarios.

## Web Application Example

Here's how you might use `logerr` in a web application for robust error handling:

```python
import logerr
from pathlib import Path
import json
import sqlite3
from typing import Dict, List, Optional

# Configure logging for different components
logerr.configure({
    "level": "INFO",
    "libraries": {
        "webapp.database": {"level": "DEBUG"},
        "webapp.auth": {"level": "WARNING"},
        "webapp.api": {"level": "INFO"}
    }
})

class DatabaseManager:
    """Database operations with Result types for error handling."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def connect(self) -> logerr.Result[sqlite3.Connection, str]:
        """Connect to database."""
        return logerr.result.of(
            lambda: sqlite3.connect(self.db_path)
        ).map_err(lambda e: f"Database connection failed: {e}")
    
    def get_user(self, user_id: int) -> logerr.Result[Dict, str]:
        """Get user by ID."""
        def query_user():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT id, name, email FROM users WHERE id = ?", 
                    (user_id,)
                )
                row = cursor.fetchone()
                if row:
                    return {"id": row[0], "name": row[1], "email": row[2]}
                raise ValueError(f"User {user_id} not found")
        
        return logerr.result.of(query_user)
    
    def create_user(self, name: str, email: str) -> logerr.Result[int, str]:
        """Create a new user."""
        def insert_user():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "INSERT INTO users (name, email) VALUES (?, ?)", 
                    (name, email)
                )
                return cursor.lastrowid
        
        return logerr.result.of(insert_user).map_err(
            lambda e: f"Failed to create user: {e}"
        )

class ConfigManager:
    """Configuration management with Option types."""
    
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
    
    def _load_config(self, path: str) -> Dict:
        """Load configuration file."""
        result = (logerr.result.of(lambda: Path(path).read_text())
            .then(lambda text: logerr.result.of(lambda: json.loads(text))))
        
        return result.unwrap_or({})
    
    def get_string(self, key: str) -> logerr.Option[str]:
        """Get string configuration value."""
        return logerr.option.from_nullable(self.config.get(key))
    
    def get_int(self, key: str) -> logerr.Option[int]:
        """Get integer configuration value."""
        return (self.get_string(key)
            .then(lambda s: logerr.option.of(lambda: int(s))))
    
    def get_bool(self, key: str) -> logerr.Option[bool]:
        """Get boolean configuration value."""
        return (self.get_string(key)
            .map(str.lower)
            .filter(lambda s: s in ["true", "false"])
            .map(lambda s: s == "true"))

class UserService:
    """User service combining database and configuration."""
    
    def __init__(self, db: DatabaseManager, config: ConfigManager):
        self.db = db
        self.config = config
    
    def validate_email(self, email: str) -> logerr.Option[str]:
        """Validate email format."""
        if "@" in email and "." in email:
            return logerr.Some(email)
        return logerr.Nothing("Invalid email format")
    
    def create_user_safely(self, name: str, email: str) -> logerr.Result[int, str]:
        """Create user with validation."""
        return (self.validate_email(email)
            .ok_or("Invalid email address")
            .then(lambda _: self.db.create_user(name, email)))
    
    def get_user_with_defaults(self, user_id: int) -> Dict:
        """Get user with default values."""
        user_result = self.db.get_user(user_id)
        
        if user_result.is_ok():
            return user_result.unwrap()
        else:
            # Return default user when not found
            default_name = self.config.get_string("default_user_name").unwrap_or("Anonymous")
            return {
                "id": user_id,
                "name": default_name,
                "email": "unknown@example.com"
            }

# Usage example
def main():
    config = ConfigManager("config.json")
    db = DatabaseManager(config.get_string("database_path").unwrap_or("app.db"))
    user_service = UserService(db, config)
    
    # Create a user
    result = user_service.create_user_safely("Alice Johnson", "alice@example.com")
    match result:
        case logerr.Ok(user_id):
            print(f"Created user with ID: {user_id}")
        case logerr.Err(error):
            print(f"Failed to create user: {error}")
    
    # Get user with fallback
    user = user_service.get_user_with_defaults(123)
    print(f"User: {user['name']} <{user['email']}>")

if __name__ == "__main__":
    main()
```

## File Processing Pipeline

Process files with comprehensive error handling:

```python
import logerr
from pathlib import Path
import json
import csv
from typing import List, Dict, Any

def read_file(path: str) -> logerr.Result[str, str]:
    """Read file contents."""
    return (logerr.result.of(lambda: Path(path).read_text())
        .map_err(lambda e: f"Failed to read {path}: {e}"))

def parse_json(content: str) -> logerr.Result[Any, str]:
    """Parse JSON content."""
    return (logerr.result.of(lambda: json.loads(content))
        .map_err(lambda e: f"Invalid JSON: {e}"))

def validate_schema(data: Dict, required_fields: List[str]) -> logerr.Result[Dict, str]:
    """Validate that data has required fields."""
    missing = [field for field in required_fields if field not in data]
    if missing:
        return logerr.Err(f"Missing required fields: {', '.join(missing)}")
    return logerr.Ok(data)

def process_user_data(data: Dict) -> logerr.Result[Dict, str]:
    """Process and normalize user data."""
    return (logerr.result.of(lambda: {
        "id": int(data["id"]),
        "name": data["name"].strip(),
        "email": data["email"].lower(),
        "age": int(data.get("age", 0))
    }).map_err(lambda e: f"Data processing error: {e}"))

def write_csv(data: List[Dict], output_path: str) -> logerr.Result[str, str]:
    """Write data to CSV file."""
    def write_data():
        with open(output_path, 'w', newline='') as f:
            if data:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
        return output_path
    
    return (logerr.result.of(write_data)
        .map_err(lambda e: f"Failed to write CSV: {e}"))

def process_file_pipeline(input_path: str, output_path: str) -> logerr.Result[str, str]:
    """Complete file processing pipeline."""
    required_fields = ["id", "name", "email"]
    
    return (read_file(input_path)
        .then(parse_json)
        .then(lambda data: validate_schema(data, required_fields))
        .then(process_user_data)
        .map(lambda user: [user])  # Convert to list for CSV
        .then(lambda users: write_csv(users, output_path)))

# Usage
result = process_file_pipeline("user.json", "user.csv")
match result:
    case logerr.Ok(path):
        print(f"Successfully processed file: {path}")
    case logerr.Err(error):
        print(f"Processing failed: {error}")
        # Error details are automatically logged!
```

## HTTP Client with Retry Logic

Build a robust HTTP client with automatic retries:

```python
import logerr
import requests
import time
from typing import Dict, Any, Optional

class HttpClient:
    """HTTP client with Result-based error handling and retry logic."""
    
    def __init__(self, base_url: str = "", timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
    
    def _make_request(self, method: str, url: str, **kwargs) -> logerr.Result[requests.Response, str]:
        """Make HTTP request."""
        full_url = f"{self.base_url}{url}" if self.base_url else url
        
        return (logerr.result.of(
            lambda: self.session.request(method, full_url, timeout=self.timeout, **kwargs)
        ).map_err(lambda e: f"HTTP request failed: {e}"))
    
    def _check_response(self, response: requests.Response) -> logerr.Result[requests.Response, str]:
        """Check if response indicates success."""
        if response.status_code >= 400:
            return logerr.Err(f"HTTP {response.status_code}: {response.text}")
        return logerr.Ok(response)
    
    def _parse_json(self, response: requests.Response) -> logerr.Result[Dict[str, Any], str]:
        """Parse JSON response."""
        return (logerr.result.of(lambda: response.json())
            .map_err(lambda e: f"Failed to parse JSON: {e}"))
    
    def get_json(self, url: str, **kwargs) -> logerr.Result[Dict[str, Any], str]:
        """GET request returning JSON."""
        return (self._make_request("GET", url, **kwargs)
            .then(self._check_response)
            .then(self._parse_json))
    
    def post_json(self, url: str, data: Dict[str, Any], **kwargs) -> logerr.Result[Dict[str, Any], str]:
        """POST request with JSON data."""
        kwargs.setdefault("json", data)
        return (self._make_request("POST", url, **kwargs)
            .then(self._check_response)
            .then(self._parse_json))
    
    def with_retry(self, operation, max_retries: int = 3, delay: float = 1.0):
        """Retry operation on failure."""
        def retry_logic(error):
            nonlocal max_retries
            if max_retries > 0 and "timeout" in str(error).lower():
                max_retries -= 1
                time.sleep(delay)
                return operation()
            return logerr.Err(f"Max retries exceeded: {error}")
        
        return operation().or_else(retry_logic)

class ApiClient:
    """Example API client using the HTTP client."""
    
    def __init__(self, api_key: str):
        self.client = HttpClient("https://api.example.com")
        self.api_key = api_key
    
    def _auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}
    
    def get_user(self, user_id: int) -> logerr.Result[Dict[str, Any], str]:
        """Get user by ID with automatic retries."""
        return self.client.with_retry(
            lambda: self.client.get_json(f"/users/{user_id}", headers=self._auth_headers())
        )
    
    def create_user(self, user_data: Dict[str, Any]) -> logerr.Result[Dict[str, Any], str]:
        """Create a new user."""
        return (self._validate_user_data(user_data)
            .then(lambda data: self.client.post_json(
                "/users", data, headers=self._auth_headers()
            )))
    
    def _validate_user_data(self, data: Dict[str, Any]) -> logerr.Result[Dict[str, Any], str]:
        """Validate user data before sending."""
        required_fields = ["name", "email"]
        missing = [field for field in required_fields if not data.get(field)]
        
        if missing:
            return logerr.Err(f"Missing required fields: {', '.join(missing)}")
        
        if "@" not in data["email"]:
            return logerr.Err("Invalid email format")
        
        return logerr.Ok(data)

# Usage
api = ApiClient("your-api-key")

# Get user with automatic retry on timeout
user_result = api.get_user(123)
user = user_result.unwrap_or({"name": "Unknown", "email": "unknown@example.com"})
print(f"User: {user['name']}")

# Create user with validation
new_user_result = api.create_user({
    "name": "Bob Smith",
    "email": "bob@example.com"
})

match new_user_result:
    case logerr.Ok(user):
        print(f"Created user: {user['name']}")
    case logerr.Err(error):
        print(f"Failed to create user: {error}")
```

## Configuration Management System

A comprehensive configuration system using Options:

```python
import logerr
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Union
from dataclasses import dataclass, field

@dataclass
class DatabaseConfig:
    host: str = "localhost"
    port: int = 5432
    database: str = "myapp"
    username: str = "user"
    password: str = ""

@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    workers: int = 1

@dataclass
class AppConfig:
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    log_level: str = "INFO"
    features: List[str] = field(default_factory=list)

class ConfigLoader:
    """Configuration loader with Option-based value resolution."""
    
    def __init__(self):
        self.sources = []
    
    def add_file_source(self, path: str) -> 'ConfigLoader':
        """Add a JSON configuration file source."""
        config_data = (logerr.result.of(lambda: Path(path).read_text())
            .then(lambda text: logerr.result.of(lambda: json.loads(text)))
            .unwrap_or({}))
        
        self.sources.append(("file", config_data))
        return self
    
    def add_env_source(self, prefix: str = "APP_") -> 'ConfigLoader':
        """Add environment variables as a source."""
        env_vars = {
            key[len(prefix):].lower(): value 
            for key, value in os.environ.items() 
            if key.startswith(prefix)
        }
        self.sources.append(("env", env_vars))
        return self
    
    def add_dict_source(self, data: Dict[str, Any]) -> 'ConfigLoader':
        """Add a dictionary source."""
        self.sources.append(("dict", data))
        return self
    
    def get_value(self, key: str) -> logerr.Option[str]:
        """Get configuration value, checking sources in order."""
        for source_type, source_data in reversed(self.sources):  # Later sources override
            option = logerr.option.from_nullable(self._get_nested_value(source_data, key))
            if option.is_some():
                return option
        return logerr.Nothing.empty()
    
    def _get_nested_value(self, data: Dict, key: str) -> Any:
        """Get nested value using dot notation (e.g., 'database.host')."""
        keys = key.split('.')
        current = data
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        return current
    
    def get_string(self, key: str, default: str = "") -> str:
        """Get string value with default."""
        return self.get_value(key).unwrap_or(default)
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer value with default."""
        return (self.get_value(key)
            .then(lambda v: logerr.option.of(lambda: int(v)))
            .unwrap_or(default))
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean value with default."""
        return (self.get_value(key)
            .map(str.lower)
            .filter(lambda v: v in ["true", "false", "1", "0", "yes", "no"])
            .map(lambda v: v in ["true", "1", "yes"])
            .unwrap_or(default))
    
    def get_list(self, key: str, separator: str = ",", default: List[str] = None) -> List[str]:
        """Get list value with default."""
        if default is None:
            default = []
        
        return (self.get_value(key)
            .map(lambda v: [item.strip() for item in v.split(separator) if item.strip()])
            .unwrap_or(default))
    
    def build_config(self) -> AppConfig:
        """Build complete application configuration."""
        return AppConfig(
            database=DatabaseConfig(
                host=self.get_string("database.host", "localhost"),
                port=self.get_int("database.port", 5432),
                database=self.get_string("database.database", "myapp"),
                username=self.get_string("database.username", "user"),
                password=self.get_string("database.password", "")
            ),
            server=ServerConfig(
                host=self.get_string("server.host", "0.0.0.0"),
                port=self.get_int("server.port", 8000),
                debug=self.get_bool("server.debug", False),
                workers=self.get_int("server.workers", 1)
            ),
            log_level=self.get_string("log_level", "INFO"),
            features=self.get_list("features", ",", [])
        )

# Usage example
def load_application_config() -> AppConfig:
    """Load configuration from multiple sources."""
    config_loader = (ConfigLoader()
        .add_dict_source({  # Defaults
            "database": {"host": "localhost", "port": 5432},
            "server": {"host": "0.0.0.0", "port": 8000},
            "log_level": "INFO"
        })
        .add_file_source("config.json")  # File overrides
        .add_env_source("MYAPP_"))       # Environment overrides everything
    
    return config_loader.build_config()

# Example usage
if __name__ == "__main__":
    config = load_application_config()
    
    print(f"Database: {config.database.host}:{config.database.port}")
    print(f"Server: {config.server.host}:{config.server.port}")
    print(f"Debug mode: {config.server.debug}")
    print(f"Log level: {config.log_level}")
    print(f"Features: {config.features}")
```

## Error Recovery and Circuit Breaker

Implement a circuit breaker pattern with Result types:

```python
import logerr
import time
from enum import Enum
from typing import Callable, TypeVar, Any
from dataclasses import dataclass, field

T = TypeVar('T')
E = TypeVar('E')

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service is back

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    timeout_seconds: float = 60.0
    test_timeout_seconds: float = 30.0

class CircuitBreaker:
    """Circuit breaker implementation using Result types."""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.last_test_time = 0.0
    
    def call(self, operation: Callable[[], logerr.Result[T, E]]) -> logerr.Result[T, str]:
        """Execute operation through the circuit breaker."""
        current_time = time.time()
        
        if self.state == CircuitState.OPEN:
            if current_time - self.last_failure_time < self.config.timeout_seconds:
                return logerr.Err(f"Circuit breaker {self.name} is OPEN")
            else:
                self.state = CircuitState.HALF_OPEN
                self.last_test_time = current_time
        
        if self.state == CircuitState.HALF_OPEN:
            if current_time - self.last_test_time > self.config.test_timeout_seconds:
                self.state = CircuitState.OPEN
                return logerr.Err(f"Circuit breaker {self.name} test timeout")
        
        # Execute the operation
        result = operation()
        
        if result.is_ok():
            self._on_success()
        else:
            self._on_failure(current_time)
        
        return result.map_err(lambda e: f"Operation failed (circuit: {self.state.value}): {e}")
    
    def _on_success(self):
        """Handle successful operation."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self, current_time: float):
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = current_time
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN

class ServiceClient:
    """Example service client with circuit breaker."""
    
    def __init__(self):
        self.circuit_breaker = CircuitBreaker(
            "external_service",
            CircuitBreakerConfig(failure_threshold=3, timeout_seconds=30.0)
        )
    
    def _call_external_service(self, data: str) -> logerr.Result[str, str]:
        """Simulate external service call."""
        import random
        if random.random() < 0.3:  # 30% failure rate
            return logerr.Err("Service temporarily unavailable")
        return logerr.Ok(f"Processed: {data}")
    
    def process_with_circuit_breaker(self, data: str) -> logerr.Result[str, str]:
        """Process data with circuit breaker protection."""
        return self.circuit_breaker.call(
            lambda: self._call_external_service(data)
        )
    
    def process_with_fallback(self, data: str) -> str:
        """Process with fallback on failure."""
        result = self.process_with_circuit_breaker(data)
        return result.unwrap_or(f"Fallback processing: {data}")

# Usage
client = ServiceClient()

for i in range(10):
    result = client.process_with_fallback(f"data_{i}")
    print(f"Request {i}: {result}")
    time.sleep(1)
```

These examples demonstrate how `logerr` can be used to build robust, observable applications with clean error handling patterns.