# Singleton Service

<div class="hero">
  <h1>Modern Singleton Services for Python</h1>
  <p>Type-safe, dependency-managed singleton services that just work.</p>
</div>

[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/singleton-service)](https://pypi.org/project/singleton-service/)
[![PyPI - Status](https://img.shields.io/pypi/status/singleton-service)](https://pypi.org/project/singleton-service/)
[![PyPI - License](https://img.shields.io/pypi/l/singleton-service)](https://github.com/vduseev/singleton-service/blob/main/LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/vduseev/singleton-service/ci.yml)](https://github.com/vduseev/singleton-service/actions)

**singleton-service** is a modern Python framework for building singleton services with automatic dependency management, lazy initialization, and type safety. It makes building service-oriented applications simple and reliable.

## Quick Example

```python
from singleton_service import BaseService, requires, guarded

@requires(DatabaseService)
class UserService(BaseService):
    _users = {}
    
    @classmethod
    def initialize(cls) -> None:
        # Load users from database
        cls._users = DatabaseService.load_all_users()
    
    @classmethod
    @guarded  # Automatically initializes dependencies
    def get_user(cls, user_id: int) -> User:
        return cls._users.get(user_id)

# Just use it - no setup required!
user = UserService.get_user(123)
```

## Key Features

<div class="feature-grid">
  <div class="feature-card">
    <h3>🔗 Automatic Dependencies</h3>
    <p>Declare dependencies with decorators. The framework handles initialization order automatically.</p>
  </div>
  
  <div class="feature-card">
    <h3>⚡ Lazy Initialization</h3>
    <p>Services initialize only when first used, in the correct order, with full error handling.</p>
  </div>
  
  <div class="feature-card">
    <h3>🛡️ Type Safe</h3>
    <p>Full type safety with Python 3.10+ type hints. IDE autocomplete and static analysis just work.</p>
  </div>
  
  <div class="feature-card">
    <h3>🚫 No Instances</h3>
    <p>Pure singleton pattern - no objects to manage, just call class methods directly.</p>
  </div>
  
  <div class="feature-card">
    <h3>🔍 Health Checks</h3>
    <p>Built-in health verification ensures services are properly initialized before use.</p>
  </div>
  
  <div class="feature-card">
    <h3>📦 Zero Dependencies</h3>
    <p>Lightweight framework with no runtime dependencies. Easy to integrate anywhere.</p>
  </div>
</div>

## Why Singleton Service?

Traditional dependency injection frameworks are complex and heavyweight. **singleton-service** gives you the benefits of DI with Python's class system:

=== "Without singleton-service"

    ```python
    # Manual dependency management - error prone
    class UserService:
        def __init__(self):
            self.db = DatabaseService()  # When to initialize?
            self.cache = CacheService()  # What order?
        
        def get_user(self, user_id):
            if not self.db.connected:    # Manual checks
                raise RuntimeError("DB not ready")
            return self.db.get_user(user_id)
    
    # Complex setup required everywhere
    db = DatabaseService()
    db.connect()
    cache = CacheService() 
    cache.connect()
    users = UserService()
    ```

=== "With singleton-service"

    ```python
    # Clean, declarative dependencies
    @requires(DatabaseService, CacheService)
    class UserService(BaseService):
        @classmethod
        @guarded  # Automatic initialization & checks
        def get_user(cls, user_id):
            return DatabaseService.get_user(user_id)
    
    # Just use it - no setup needed!
    user = UserService.get_user(123)
    ```

## Common Use Cases

- **Backend Services**: Database connections, API clients, caches
- **Background Workers**: Job processors, schedulers, monitors  
- **CLI Applications**: Configuration, logging, data access layers
- **Web Applications**: FastAPI/Flask service layers
- **Microservices**: Service mesh components, health checks

## Installation

Install with pip, uv, or your favorite package manager:

```bash
pip install singleton-service
```

## Next Steps

<div class="feature-grid">
  <div class="feature-card">
    <h3>📚 [Quick Start →](quickstart.md)</h3>
    <p>Get up and running in 5 minutes with a complete example.</p>
  </div>
  
  <div class="feature-card">
    <h3>🎓 [Tutorial →](tutorial/)</h3>
    <p>Step-by-step guide from basics to advanced patterns.</p>
  </div>
  
  <div class="feature-card">
    <h3>💡 [Examples →](examples/)</h3>
    <p>Real-world examples and common patterns.</p>
  </div>
  
  <div class="feature-card">
    <h3>📖 [API Reference →](api/)</h3>
    <p>Complete API documentation and reference.</p>
  </div>
</div>

## Community

- **GitHub**: [vduseev/singleton-service](https://github.com/vduseev/singleton-service)
- **Issues**: [Report bugs or request features](https://github.com/vduseev/singleton-service/issues)
- **PyPI**: [singleton-service](https://pypi.org/project/singleton-service/)

**singleton-service** is MIT licensed and welcomes contributions!