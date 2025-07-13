# Initialization Order

🎯 **Learning Goals**: Master initialization timing, understand dependency resolution algorithms, and learn to visualize complex service graphs.

Understanding **when** and **how** services initialize is crucial for building reliable applications. In this tutorial, you'll learn exactly how the framework determines initialization order and how to work with complex dependency graphs.

## 📚 Understanding Initialization Timing

### When Do Services Initialize?

Services initialize **lazily** - only when first needed:

```python
@requires(DatabaseService)
class UserService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        print("UserService initializing...")
    
    @classmethod
    @guarded
    def get_user(cls, user_id: int) -> User:
        return DatabaseService.fetch_user(user_id)

# Service classes are defined, but nothing initializes yet
print("Services defined, but not initialized")

# First call to @guarded method triggers initialization
user = UserService.get_user(123)  # ← Initialization happens HERE
```

### The Initialization Lifecycle

When you call a `@guarded` method for the first time:

1. **Dependency Analysis**: Framework builds complete dependency graph
2. **Circular Detection**: Checks for impossible dependency cycles  
3. **Order Calculation**: Uses topological sort to find safe order
4. **Sequential Initialization**: Initializes services one by one in correct order
5. **Health Verification**: Calls `ping()` on each service
6. **Method Execution**: Finally runs your original method

## 💻 Visualizing Initialization Order

Let's build a complex system and watch initialization happen step by step:

### Step 1: Create a Complex Service Graph

```python
# services.py
from singleton_service import BaseService, requires, guarded
from typing import ClassVar

# Foundational services (no dependencies)
class ConfigService(BaseService):
    _config: ClassVar[dict] = {}
    
    @classmethod
    def initialize(cls) -> None:
        cls._config = {"app_name": "MyApp", "version": "1.0"}
        print("1️⃣  ConfigService initialized")
    
    @classmethod
    @guarded
    def get(cls, key: str) -> str:
        return cls._config.get(key)

class LoggingService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        print("2️⃣  LoggingService initialized")
    
    @classmethod
    @guarded
    def log(cls, message: str) -> None:
        print(f"LOG: {message}")

# Level 1 dependencies
@requires(ConfigService)
class DatabaseService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        app_name = ConfigService.get("app_name")
        print(f"3️⃣  DatabaseService initialized for {app_name}")
    
    @classmethod
    @guarded
    def fetch_user(cls, user_id: int) -> dict:
        return {"id": user_id, "name": f"User{user_id}"}

@requires(ConfigService, LoggingService)
class CacheService(BaseService):
    _cache: ClassVar[dict] = {}
    
    @classmethod
    def initialize(cls) -> None:
        LoggingService.log("Initializing cache service")
        cls._cache = {}
        print("4️⃣  CacheService initialized")
    
    @classmethod
    @guarded
    def get(cls, key: str) -> any:
        return cls._cache.get(key)
    
    @classmethod
    @guarded
    def set(cls, key: str, value: any) -> None:
        cls._cache[key] = value

# Level 2 dependencies  
@requires(DatabaseService, CacheService)
class UserService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        print("5️⃣  UserService initialized")
    
    @classmethod
    @guarded
    def get_user(cls, user_id: int) -> dict:
        # Check cache first
        cached = CacheService.get(f"user:{user_id}")
        if cached:
            return cached
        
        # Fetch from database
        user = DatabaseService.fetch_user(user_id)
        CacheService.set(f"user:{user_id}", user)
        return user

@requires(DatabaseService, LoggingService)
class OrderService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        LoggingService.log("Order service ready for business")
        print("6️⃣  OrderService initialized")
    
    @classmethod
    @guarded
    def get_orders(cls, user_id: int) -> list:
        return [{"id": 1, "user_id": user_id, "total": 29.99}]

# Level 3 dependencies
@requires(UserService, OrderService)
class CheckoutService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        print("7️⃣  CheckoutService initialized")
    
    @classmethod
    @guarded
    def process_checkout(cls, user_id: int) -> dict:
        user = UserService.get_user(user_id)
        orders = OrderService.get_orders(user_id)
        return {"user": user, "orders": orders, "status": "completed"}
```

### Step 2: Trigger Initialization and Watch

```python
# app.py
from services import CheckoutService
import time

def main():
    print("🚀 Application starting...")
    print("📋 Services defined but not yet initialized\n")
    
    print("⏰ Calling CheckoutService.process_checkout() for first time...")
    print("🔄 This will trigger initialization of all dependencies:\n")
    
    # This single call triggers initialization of ALL dependencies
    result = CheckoutService.process_checkout(user_id=123)
    
    print(f"\n✅ Checkout completed: {result}")
    
    print("\n" + "="*50)
    print("🔄 Making second call (no re-initialization)...")
    
    # Subsequent calls are fast - no re-initialization
    start_time = time.time()
    result2 = CheckoutService.process_checkout(user_id=456)
    end_time = time.time()
    
    print(f"⚡ Second call completed in {(end_time - start_time)*1000:.2f}ms")
    print(f"✅ Result: {result2}")

if __name__ == "__main__":
    main()
```

Run it and observe the initialization order:

```bash
python app.py
```

Expected output:
```
🚀 Application starting...
📋 Services defined but not yet initialized

⏰ Calling CheckoutService.process_checkout() for first time...
🔄 This will trigger initialization of all dependencies:

1️⃣  ConfigService initialized
2️⃣  LoggingService initialized
3️⃣  DatabaseService initialized for MyApp
LOG: Initializing cache service
4️⃣  CacheService initialized
5️⃣  UserService initialized
LOG: Order service ready for business
6️⃣  OrderService initialized
7️⃣  CheckoutService initialized
LOG: Getting user 123
✅ Checkout completed: {'user': {'id': 123, 'name': 'User123'}, 'orders': [{'id': 1, 'user_id': 123, 'total': 29.99}], 'status': 'completed'}

==================================================
🔄 Making second call (no re-initialization)...
⚡ Second call completed in 0.15ms
✅ Result: {'user': {'id': 456, 'name': 'User456'}, 'orders': [{'id': 1, 'user_id': 456, 'total': 29.99}], 'status': 'completed'}
```

## 🔍 Deep Dive: Dependency Resolution Algorithm

### Topological Sort Explanation

The framework uses **topological sorting** to determine initialization order:

```python
# Our dependency graph:
#
# ConfigService ──┐
#                 ├─→ DatabaseService ──┐
#                 │                     ├─→ UserService ──┐
# LoggingService ─┼─→ CacheService ──────┤                ├─→ CheckoutService  
#                 │                     │                │
#                 └─→ OrderService ──────┘                │
#                                                         │
#                     OrderService ────────────────────────┘
```

The algorithm:
1. **Find nodes with no dependencies**: `ConfigService`, `LoggingService`
2. **Remove them and their edges**: Now `DatabaseService`, `CacheService`, `OrderService` have no remaining dependencies
3. **Repeat**: Continue until all nodes are processed
4. **Result**: `[ConfigService, LoggingService, DatabaseService, CacheService, OrderService, UserService, CheckoutService]`

### Visualizing Your Dependencies

You can inspect the dependency graph programmatically:

```python
# debug_dependencies.py
from services import CheckoutService

def print_dependency_graph():
    """Print the dependency graph for debugging."""
    
    def get_all_services():
        """Get all services in the dependency tree."""
        visited = set()
        
        def collect_services(service_cls):
            if service_cls in visited:
                return
            visited.add(service_cls)
            for dep in service_cls._dependencies:
                collect_services(dep)
        
        collect_services(CheckoutService)
        return visited
    
    def print_service_deps(service_cls, indent=0):
        """Recursively print service dependencies."""
        spaces = "  " * indent
        deps = list(service_cls._dependencies)
        
        if deps:
            print(f"{spaces}{service_cls.__name__} depends on:")
            for dep in deps:
                print(f"{spaces}  - {dep.__name__}")
                print_service_deps(dep, indent + 2)
        else:
            print(f"{spaces}{service_cls.__name__} (no dependencies)")
    
    print("🔍 Dependency Graph Analysis:")
    print("="*40)
    print_service_deps(CheckoutService)
    
    print(f"\n📊 Initialization Order:")
    order = CheckoutService._get_initialization_order()
    for i, service in enumerate(order, 1):
        print(f"  {i}. {service.__name__}")

if __name__ == "__main__":
    print_dependency_graph()
```

Run it:
```bash
python debug_dependencies.py
```

Output:
```
🔍 Dependency Graph Analysis:
========================================
CheckoutService depends on:
  - UserService
    UserService depends on:
      - DatabaseService
        DatabaseService depends on:
          - ConfigService (no dependencies)
      - CacheService
        CacheService depends on:
          - ConfigService (no dependencies)
          - LoggingService (no dependencies)
  - OrderService
    OrderService depends on:
      - DatabaseService
        DatabaseService depends on:
          - ConfigService (no dependencies)
      - LoggingService (no dependencies)

📊 Initialization Order:
  1. ConfigService
  2. LoggingService
  3. DatabaseService
  4. CacheService
  5. OrderService
  6. UserService
  7. CheckoutService
```

## 🔧 Advanced Initialization Patterns

### Parallel Initialization Groups

Services with no interdependencies can be grouped:

```python
# These could initialize in parallel (if framework supported it)
# Group 1: ConfigService, LoggingService (no dependencies)
# Group 2: DatabaseService, CacheService, OrderService (depend only on Group 1)  
# Group 3: UserService (depends on Group 2)
# Group 4: CheckoutService (depends on Group 3)
```

### Conditional Initialization

Some services might only initialize under certain conditions:

```python
import os

@requires(ConfigService)
class MetricsService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        if os.getenv("ENABLE_METRICS") == "true":
            print("📊 Metrics service initialized")
        else:
            print("📊 Metrics service disabled")
    
    @classmethod
    def ping(cls) -> bool:
        # Only healthy if enabled
        return os.getenv("ENABLE_METRICS") == "true"

# Usage with conditional dependency
def get_user_service_deps():
    deps = [DatabaseService, CacheService]
    if os.getenv("ENABLE_METRICS") == "true":
        deps.append(MetricsService)
    return deps

# Note: Actual implementation would need dynamic dependency injection
# which is an advanced pattern - see Advanced Topics
```

### Initialization State Tracking

You can track which services are initialized:

```python
# service_monitor.py
from singleton_service import BaseService

def get_initialization_status():
    """Get status of all known services."""
    
    # In a real app, you'd maintain a registry of all services
    services = [
        ConfigService, LoggingService, DatabaseService,
        CacheService, OrderService, UserService, CheckoutService
    ]
    
    status = {}
    for service in services:
        status[service.__name__] = {
            "initialized": service._initialized,
            "dependencies": [dep.__name__ for dep in service._dependencies]
        }
    
    return status

def print_status():
    """Print initialization status."""
    status = get_initialization_status()
    
    print("📊 Service Initialization Status:")
    print("="*40)
    
    for name, info in status.items():
        state = "✅ Initialized" if info["initialized"] else "⏳ Not initialized"
        deps = ", ".join(info["dependencies"]) if info["dependencies"] else "None"
        print(f"{name:20} {state}")
        print(f"{'':20} Dependencies: {deps}")
        print()

# Usage
print("Before any service calls:")
print_status()

# Trigger initialization
CheckoutService.process_checkout(123)

print("\nAfter CheckoutService call:")
print_status()
```

## ⚠️ Common Initialization Issues

### ❌ Late Dependency Declaration

```python
class UserService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        # ❌ Too late to discover DatabaseService dependency!
        cls._database = DatabaseService()
    
    @classmethod
    @guarded
    def get_user(cls, user_id: int):
        return cls._database.fetch_user(user_id)
```

**Solution**: Declare dependencies with `@requires`:
```python
@requires(DatabaseService)
class UserService(BaseService):
    # ✅ Framework knows about dependency
    pass
```

### ❌ Initialization Order Assumptions

```python
class UserService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        # ❌ Assuming DatabaseService is already initialized
        # This might not be true!
        if not DatabaseService._initialized:
            raise RuntimeError("Database not ready!")
```

**Solution**: Use `@requires` and let framework handle it:
```python
@requires(DatabaseService)
class UserService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        # ✅ DatabaseService guaranteed to be ready
        # because of @requires declaration
        pass
```

### ❌ Initialization Performance Issues

```python
class SlowService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        # ❌ Expensive operation blocks all dependent services
        time.sleep(10)  # Simulate slow database migration
        print("SlowService finally ready")
```

**Solutions**:
- Keep initialization fast
- Move slow operations to background tasks
- Use lazy loading patterns
- Consider async initialization (advanced topic)

### ❌ Initialization Error Handling

```python
class BrokenService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        # ❌ Unhandled error breaks entire dependency chain
        raise RuntimeError("Database connection failed!")
    
    @classmethod
    def ping(cls) -> bool:
        # This never gets called if initialize() fails
        return True
```

**Better error handling**:
```python
class RobustService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        try:
            cls._connection = connect_to_database()
        except Exception as e:
            # Let the framework handle it with clear error message
            raise ServiceInitializationError(f"Database connection failed: {e}")
    
    @classmethod
    def ping(cls) -> bool:
        return cls._connection is not None and cls._connection.is_alive()
```

## ✅ Summary

You now understand initialization order like a pro! Here's what you mastered:

- ✅ **Lazy initialization** - Services initialize only when first used
- ✅ **Dependency resolution** - Framework uses topological sort to find safe order
- ✅ **Complex graphs** - Multiple levels of dependencies work automatically  
- ✅ **Performance implications** - First call initializes, subsequent calls are fast
- ✅ **Debugging tools** - How to visualize and inspect dependency graphs

### Key Takeaways

1. **Initialization is lazy** - Happens on first `@guarded` method call
2. **Order is automatic** - Framework calculates safe sequence using topological sort
3. **Dependencies are transitive** - Framework finds all dependencies recursively
4. **One-time only** - Each service initializes exactly once per application lifecycle
5. **Fast subsequent calls** - No re-initialization overhead after first call

## 🚀 Next Steps

Ready to make your services bulletproof with health checks?

**[Health Checks →](health-checks.md)**

In the next tutorial, you'll learn how to implement robust health verification that ensures your services are not just initialized, but actually working correctly.

---

**Tutorial Progress**: 3/6 complete ✅✅✅  
**Previous**: [Adding Dependencies](dependencies.md) | **Next**: [Health Checks](health-checks.md)  
**Estimated time**: 25 minutes ⏱️