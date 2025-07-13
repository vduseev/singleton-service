# Your First Service

🎯 **Learning Goals**: Create a singleton service, understand the core concepts, and see initialization in action.

In this tutorial, you'll create your first singleton service and learn the fundamental concepts that make **singleton-service** so powerful.

## 📚 Core Concepts

Before we dive into code, let's understand what makes singleton services special:

### What is a Singleton Service?

A **singleton service** is a class that:
- ✅ **Cannot be instantiated** - No `MyService()` calls
- ✅ **Has only one "instance"** - Shared state across your application  
- ✅ **Uses class methods only** - All functionality through `@classmethod`
- ✅ **Initializes automatically** - Sets up resources when first used

### Why Use Singleton Services?

Traditional approaches have problems:

=== "❌ Global Variables"
    ```python
    # Messy, hard to test, no initialization control
    DATABASE_CONNECTION = None
    CACHE_CLIENT = None
    
    def get_user(user_id):
        if DATABASE_CONNECTION is None:  # Manual checks everywhere!
            DATABASE_CONNECTION = connect_to_db()
        return DATABASE_CONNECTION.fetch_user(user_id)
    ```

=== "❌ Manual Singletons"
    ```python
    # Lots of boilerplate, error-prone
    class DatabaseService:
        _instance = None
        
        def __new__(cls):
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.connection = None
            return cls._instance
        
        def initialize(self):
            if self.connection is None:  # More manual checks!
                self.connection = connect_to_db()
    ```

=== "✅ singleton-service"
    ```python
    # Clean, automatic, type-safe
    class DatabaseService(BaseService):
        _connection: ClassVar[Optional[Connection]] = None
        
        @classmethod
        def initialize(cls) -> None:
            cls._connection = connect_to_db()
        
        @classmethod
        @guarded  # Automatic initialization + checks
        def get_user(cls, user_id: int) -> User:
            return cls._connection.fetch_user(user_id)
    ```

## 💻 Creating Your First Service

Let's build a configuration service that loads settings from environment variables:

### Step 1: Basic Service Structure

```python
# config_service.py
import os
from typing import ClassVar, Optional
from singleton_service import BaseService, guarded

class ConfigService(BaseService):
    """Service for managing application configuration."""
    
    # Store configuration in class variables
    _database_url: ClassVar[Optional[str]] = None
    _api_key: ClassVar[Optional[str]] = None
    _debug_mode: ClassVar[bool] = False
    _max_connections: ClassVar[int] = 10
    
    @classmethod
    def initialize(cls) -> None:
        """Load configuration from environment variables."""
        cls._database_url = os.getenv("DATABASE_URL")
        cls._api_key = os.getenv("API_KEY")
        cls._debug_mode = os.getenv("DEBUG", "false").lower() == "true"
        cls._max_connections = int(os.getenv("MAX_CONNECTIONS", "10"))
        
        print("⚙️  Configuration loaded:")
        print(f"   Debug mode: {cls._debug_mode}")
        print(f"   Max connections: {cls._max_connections}")
        print(f"   Database URL: {'***' if cls._database_url else 'Not set'}")
        print(f"   API key: {'***' if cls._api_key else 'Not set'}")
    
    @classmethod
    def ping(cls) -> bool:
        """Verify that required configuration is present."""
        # In a real app, you might check that required config exists
        return True  # For this example, we allow missing config
    
    @classmethod
    @guarded
    def get_database_url(cls) -> Optional[str]:
        """Get the database URL."""
        return cls._database_url
    
    @classmethod
    @guarded
    def get_api_key(cls) -> Optional[str]:
        """Get the API key."""
        return cls._api_key
    
    @classmethod
    @guarded
    def is_debug_mode(cls) -> bool:
        """Check if debug mode is enabled."""
        return cls._debug_mode
    
    @classmethod
    @guarded
    def get_max_connections(cls) -> int:
        """Get the maximum number of connections."""
        return cls._max_connections
```

### Step 2: Use Your Service

```python
# app.py
import os
from config_service import ConfigService

# Set some environment variables for testing
os.environ["DEBUG"] = "true"
os.environ["MAX_CONNECTIONS"] = "20"
os.environ["API_KEY"] = "secret-key-123"

def main():
    print("🚀 Starting application...")
    
    # Just use the service - no setup required!
    # The first call will trigger initialization automatically
    debug = ConfigService.is_debug_mode()
    max_conn = ConfigService.get_max_connections()
    api_key = ConfigService.get_api_key()
    
    print(f"\n📊 Application settings:")
    print(f"   Debug mode: {debug}")
    print(f"   Max connections: {max_conn}")
    print(f"   API key: {api_key}")
    
    # Subsequent calls are fast - no re-initialization
    print(f"\n🔄 Second call (no re-initialization):")
    print(f"   Debug mode: {ConfigService.is_debug_mode()}")

if __name__ == "__main__":
    main()
```

Run it:

```bash
python app.py
```

Expected output:
```
🚀 Starting application...
⚙️  Configuration loaded:
   Debug mode: True
   Max connections: 20
   Database URL: Not set
   API key: ***

📊 Application settings:
   Debug mode: True
   Max connections: 20
   API key: secret-key-123

🔄 Second call (no re-initialization):
   Debug mode: True
```

## 🔍 Deep Dive: What Just Happened?

Let's break down the magic:

### 1. **Automatic Initialization**

```python
# First call to ANY @guarded method triggers initialization
debug = ConfigService.is_debug_mode()  # ← Initialization happens here!
```

The framework:
1. Detects this is the first call to a `@guarded` method
2. Calls `ConfigService.initialize()` automatically
3. Calls `ConfigService.ping()` to verify initialization succeeded
4. Marks the service as initialized
5. Executes the original method (`is_debug_mode`)

### 2. **The @guarded Decorator**

```python
@classmethod
@guarded  # ← This decorator provides the magic
def is_debug_mode(cls) -> bool:
    return cls._debug_mode
```

`@guarded` guarantees:
- ✅ Service is initialized before method runs
- ✅ Initialization happens only once
- ✅ Clear errors if initialization fails
- ✅ Works with both sync and async methods

### 3. **State Management**

```python
class ConfigService(BaseService):
    # All state stored in class variables
    _debug_mode: ClassVar[bool] = False  # ← Type-safe class state
    _api_key: ClassVar[Optional[str]] = None
```

Why class variables?
- **Shared state**: All calls see the same data
- **Type safety**: Full IDE support and type checking
- **Memory efficient**: No instance overhead
- **Thread safe**: When used properly

### 4. **The ping() Method**

```python
@classmethod
def ping(cls) -> bool:
    """Verify that required configuration is present."""
    return True  # Could check required config exists
```

The `ping()` method is your health check:
- Called automatically after `initialize()`
- Should be fast and lightweight
- Return `False` or raise exception if unhealthy
- Prevents service from being marked as initialized if it fails

## 🔧 Common Patterns

### Environment Variable Loading

```python
class ConfigService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        # Load with defaults
        cls._port = int(os.getenv("PORT", "8000"))
        
        # Required values
        cls._secret_key = os.getenv("SECRET_KEY")
        if not cls._secret_key:
            raise ValueError("SECRET_KEY environment variable is required")
        
        # Boolean parsing
        cls._debug = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
```

### Validation in ping()

```python
@classmethod
def ping(cls) -> bool:
    """Validate configuration is correct."""
    # Check required values
    if not cls._secret_key:
        return False
    
    # Validate formats
    if cls._port < 1 or cls._port > 65535:
        return False
    
    # Check file existence
    if cls._config_file and not os.path.exists(cls._config_file):
        return False
    
    return True
```

### Type-Safe Getters

```python
@classmethod
@guarded
def get_database_config(cls) -> DatabaseConfig:
    """Get typed database configuration."""
    return DatabaseConfig(
        url=cls._database_url,
        max_connections=cls._max_connections,
        timeout=cls._timeout
    )
```

## ⚠️ Common Mistakes

### ❌ Don't Create Instances

```python
# This will raise RuntimeError!
config = ConfigService()  # ❌ Services can't be instantiated
```

### ❌ Don't Forget @guarded

```python
@classmethod
def get_api_key(cls) -> str:  # ❌ Missing @guarded
    return cls._api_key  # Might be None if not initialized!
```

### ❌ Don't Call @guarded from initialize()

```python
@classmethod
def initialize(cls) -> None:
    cls._api_key = "secret"
    cls.validate_key()  # ❌ SelfDependencyError!

@classmethod
@guarded
def validate_key(cls) -> bool:
    return len(cls._api_key) > 0
```

### ❌ Don't Store State in Instance Variables

```python
class BadService(BaseService):
    def __init__(self):  # ❌ Services can't be instantiated anyway!
        self.value = 42  # ❌ Use class variables instead
    
# Use this instead:
class GoodService(BaseService):
    _value: ClassVar[int] = 42  # ✅ Class variable
```

## ✅ Summary

Congratulations! You've learned:

- ✅ **How to create singleton services** with `BaseService`
- ✅ **Automatic initialization** with `initialize()` and `ping()`
- ✅ **Method protection** with `@guarded`
- ✅ **State management** with class variables
- ✅ **Common patterns** for configuration services

### Key Takeaways

1. **Services are classes, not instances** - Use `@classmethod` for everything
2. **@guarded ensures initialization** - Always use it for business logic
3. **State goes in class variables** - Use `ClassVar` for type safety
4. **initialize() sets up resources** - Called automatically on first use
5. **ping() validates health** - Keep it fast and simple

## 🚀 Next Steps

Ready for more? Let's learn about dependencies:

**[Adding Dependencies →](dependencies.md)**

In the next tutorial, you'll learn how to make services depend on each other and let the framework handle initialization order automatically.

---

**Tutorial Progress**: 1/6 complete ✅  
**Next**: [Adding Dependencies](dependencies.md)  
**Estimated time**: 15 minutes ⏱️