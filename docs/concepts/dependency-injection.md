# Dependency Injection

**singleton-service** implements dependency injection (DI) using a declarative approach that's simpler than traditional DI frameworks while providing the same benefits. This section explains how it works and compares it to other approaches.

## 🎯 What Is Dependency Injection?

**Dependency Injection** is a design pattern where dependencies are provided to an object rather than the object creating them directly.

### Without Dependency Injection
```python
class UserService:
    def __init__(self):
        self.db = DatabaseConnection()      # ❌ Hard-coded dependency
        self.cache = RedisCache()           # ❌ Hard-coded dependency
        self.logger = FileLogger()         # ❌ Hard-coded dependency
    
    def get_user(self, user_id):
        # UserService creates its own dependencies
        return self.db.query_user(user_id)
```

**Problems:**
- Hard to test (can't mock dependencies)
- Tight coupling between classes
- Hard to change implementations
- No control over initialization order

### With Dependency Injection
```python
@requires(DatabaseService, CacheService, LoggingService)
class UserService(BaseService):
    @classmethod
    @guarded
    def get_user(cls, user_id: int) -> User:
        # ✅ Dependencies provided by framework
        return DatabaseService.query_user(user_id)
```

**Benefits:**
- Easy to test (dependencies can be mocked)
- Loose coupling between services
- Easy to swap implementations
- Framework controls initialization order

## 🔧 How singleton-service DI Works

### 1. Dependency Declaration

Use the `@requires` decorator to declare what your service needs:

```python
from singleton_service import BaseService, requires, guarded

@requires(DatabaseService, CacheService)  # ✅ Explicit dependencies
class UserService(BaseService):
    @classmethod
    @guarded
    def get_user(cls, user_id: int) -> User:
        # DatabaseService and CacheService guaranteed to be ready
        cached_user = CacheService.get(f"user:{user_id}")
        if cached_user:
            return cached_user
        
        user = DatabaseService.query_user(user_id)
        CacheService.set(f"user:{user_id}", user)
        return user
```

### 2. Dependency Resolution

The framework automatically:

1. **Discovers dependencies** - Analyzes `@requires` declarations
2. **Builds dependency graph** - Maps relationships between services
3. **Detects cycles** - Prevents circular dependencies
4. **Calculates order** - Uses topological sort for safe initialization
5. **Initializes services** - In correct dependency order

```python
# Dependency graph for UserService:
# DatabaseService (no deps) → Initialize first
# CacheService (no deps) → Initialize first  
# UserService (depends on both) → Initialize last
```

### 3. Lazy Resolution

Dependencies are resolved only when needed:

```python
# Services defined but nothing happens yet
@requires(DatabaseService)
class UserService(BaseService): pass

# Still nothing happens
user_service = UserService  # Just a class reference

# NOW dependency resolution happens
user = UserService.get_user(123)  # First @guarded method call
```

## 🏗️ DI Implementation Patterns

### Service Locator Pattern

**singleton-service** uses a service locator pattern where services find dependencies by name:

```python
@requires(DatabaseService, CacheService)
class UserService(BaseService):
    @classmethod
    @guarded
    def get_user(cls, user_id: int) -> User:
        # Service locator: find dependencies by class name
        return DatabaseService.query_user(user_id)  # Framework ensures it's ready
```

### Constructor Injection (Traditional)

Traditional DI frameworks use constructor injection:

```python
# Traditional DI framework approach
class UserService:
    def __init__(self, database: DatabaseService, cache: CacheService):
        self.database = database
        self.cache = cache
    
    def get_user(self, user_id: int) -> User:
        return self.database.query_user(user_id)

# Complex setup required
container = DIContainer()
container.register(DatabaseService, database_instance)
container.register(CacheService, cache_instance)
user_service = container.resolve(UserService)
```

### Method Injection (singleton-service)

**singleton-service** uses implicit method injection:

```python
@requires(DatabaseService, CacheService)
class UserService(BaseService):
    # No constructor needed!
    
    @classmethod
    @guarded  # Dependencies injected automatically
    def get_user(cls, user_id: int) -> User:
        return DatabaseService.query_user(user_id)

# Simple usage - no setup required
user = UserService.get_user(123)
```

## 📊 Comparison with Other DI Frameworks

### Spring Framework (Java)

=== "Spring (XML)"
    ```xml
    <!-- Complex XML configuration -->
    <bean id="databaseService" class="com.example.DatabaseService"/>
    <bean id="cacheService" class="com.example.CacheService"/>
    <bean id="userService" class="com.example.UserService">
        <property name="database" ref="databaseService"/>
        <property name="cache" ref="cacheService"/>
    </bean>
    ```

=== "singleton-service"
    ```python
    # Simple Python decorators
    @requires(DatabaseService, CacheService)
    class UserService(BaseService):
        pass
    ```

### ASP.NET Core (C#)

=== "ASP.NET Core"
    ```csharp
    // Complex service registration
    services.AddScoped<IDatabaseService, DatabaseService>();
    services.AddScoped<ICacheService, CacheService>();
    services.AddScoped<IUserService, UserService>();
    
    // Constructor injection required
    public class UserService {
        public UserService(IDatabaseService db, ICacheService cache) {
            _db = db;
            _cache = cache;
        }
    }
    ```

=== "singleton-service"
    ```python
    # No registration, no constructor injection
    @requires(DatabaseService, CacheService)
    class UserService(BaseService):
        @classmethod
        @guarded
        def get_user(cls, user_id: int) -> User:
            return DatabaseService.query_user(user_id)
    ```

### Dependency Injector (Python)

=== "Dependency Injector"
    ```python
    from dependency_injector import containers, providers
    
    class Container(containers.DeclarativeContainer):
        config = providers.Configuration()
        
        database = providers.Singleton(
            DatabaseService,
            host=config.db.host,
            port=config.db.port,
        )
        
        cache = providers.Singleton(
            CacheService,
            url=config.cache.url,
        )
        
        user_service = providers.Factory(
            UserService,
            database=database,
            cache=cache,
        )
    
    # Complex wiring required
    container = Container()
    user_service = container.user_service()
    ```

=== "singleton-service"
    ```python
    # Zero configuration needed
    @requires(DatabaseService, CacheService)
    class UserService(BaseService):
        pass
    
    # Just use it
    user = UserService.get_user(123)
    ```

## 🔄 Dependency Lifecycle Management

### Service Lifetimes

**singleton-service** uses singleton lifetime for all services:

```python
class DatabaseService(BaseService):
    _connection_pool: ClassVar[ConnectionPool] = None
    
    @classmethod
    def initialize(cls) -> None:
        # Called once per application lifetime
        cls._connection_pool = create_pool()
    
    @classmethod
    @guarded
    def query(cls, sql: str) -> List[Dict]:
        # Shared connection pool across all calls
        return cls._connection_pool.execute(sql)
```

### Comparison with Other Lifetimes

| Lifetime | When Created | When Destroyed | Use Case |
|----------|-------------|----------------|----------|
| **Singleton** | First use | Application end | Services, connections |
| **Scoped** | Request start | Request end | Request-specific data |
| **Transient** | Every use | Immediately | Temporary objects |

**singleton-service** focuses on singleton lifetime because it's designed for services, not business objects:

```python
# ✅ Good singleton candidates
class DatabaseService(BaseService): pass      # Infrastructure
class ConfigService(BaseService): pass       # Application-wide
class PaymentService(BaseService): pass      # External API client

# ❌ Poor singleton candidates  
class User: pass                             # Business object (use instances)
class ShoppingCart: pass                    # User-specific state
class HttpRequest: pass                     # Request-specific data
```

## 🧩 Advanced DI Patterns

### Optional Dependencies

Sometimes dependencies are optional:

```python
@requires(DatabaseService)  # Required
class UserService(BaseService):
    @classmethod
    @guarded
    def get_user(cls, user_id: int) -> User:
        user = DatabaseService.query_user(user_id)
        
        # Optional dependency - check if available
        try:
            from analytics_service import AnalyticsService
            if AnalyticsService._initialized:
                AnalyticsService.track_user_access(user_id)
        except ImportError:
            pass  # Analytics not available
        
        return user
```

### Conditional Dependencies

Dependencies that vary based on configuration:

```python
import os

def get_cache_service():
    """Get appropriate cache service based on environment."""
    if os.getenv("CACHE_TYPE") == "redis":
        from redis_cache_service import RedisCacheService
        return RedisCacheService
    else:
        from memory_cache_service import MemoryCacheService
        return MemoryCacheService

# Note: Dynamic dependencies require advanced patterns
# See Advanced Topics for implementation details
```

### Dependency Groups

Organize related dependencies:

```python
# Infrastructure layer
@requires()
class ConfigService(BaseService): pass

@requires()
class LoggingService(BaseService): pass

@requires(ConfigService)
class DatabaseService(BaseService): pass

# Business layer  
@requires(DatabaseService, LoggingService)
class UserService(BaseService): pass

@requires(DatabaseService, LoggingService)
class OrderService(BaseService): pass

# Application layer
@requires(UserService, OrderService)
class CheckoutService(BaseService): pass
```

## 🔍 Dependency Resolution Algorithm

### Topological Sort

The framework uses **Kahn's algorithm** for topological sorting:

```python
def _get_initialization_order(cls) -> List[Type[BaseService]]:
    """Calculate safe initialization order using topological sort."""
    
    # 1. Build dependency graph
    graph = defaultdict(set)
    in_degree = defaultdict(int)
    
    all_deps = cls._get_all_dependencies()
    all_deps.add(cls)
    
    for service in all_deps:
        for dep in service._dependencies:
            graph[dep].add(service)      # dep → service edge
            in_degree[service] += 1      # service has incoming edge
    
    # 2. Find nodes with no dependencies
    queue = [s for s in all_deps if in_degree[s] == 0]
    result = []
    
    # 3. Process nodes in dependency order
    while queue:
        service = queue.pop(0)
        result.append(service)
        
        # Remove edges from this service
        for dependent in graph[service]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)
    
    # 4. Check for cycles
    if len(result) != len(all_deps):
        raise CircularDependencyError("Circular dependency detected")
    
    return result
```

### Example Resolution

Given this dependency graph:
```python
@requires()
class A(BaseService): pass

@requires(A)  
class B(BaseService): pass

@requires(A)
class C(BaseService): pass

@requires(B, C)
class D(BaseService): pass
```

Resolution process:
```
1. Graph: A→B, A→C, B→D, C→D
2. In-degrees: A=0, B=1, C=1, D=2  
3. Queue starts with: [A] (no dependencies)
4. Process A: Queue becomes [B, C] (A removed from B,C)
5. Process B: Queue becomes [C, D] (B removed from D)
6. Process C: Queue becomes [D] (C removed from D)  
7. Process D: Queue becomes [] (all done)
8. Result: [A, B, C, D] (or [A, C, B, D] - both valid)
```

## 🧪 Testing with Dependency Injection

### Mocking Dependencies

**singleton-service** makes testing easy:

```python
# test_user_service.py
import pytest
from unittest.mock import MagicMock
from user_service import UserService

def test_get_user():
    # Reset services
    UserService._initialized = False
    DatabaseService._initialized = False
    
    # Mock the database service
    DatabaseService.query_user = MagicMock(return_value=User("Test User"))
    DatabaseService._initialized = True  # Pretend it's initialized
    
    # Test user service
    user = UserService.get_user(123)
    
    assert user.name == "Test User"
    DatabaseService.query_user.assert_called_once_with(123)
```

### Test Service Doubles

Create test versions of services:

```python
class TestDatabaseService(BaseService):
    """Test double for database service."""
    
    _test_users: ClassVar[Dict[int, User]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        cls._test_users = {
            123: User("Test User"),
            456: User("Another User"),
        }
    
    @classmethod
    @guarded
    def query_user(cls, user_id: int) -> Optional[User]:
        return cls._test_users.get(user_id)

# Use in tests by monkey-patching
@requires(TestDatabaseService)  # Use test double instead
class TestableUserService(BaseService):
    # Same implementation as UserService
    pass
```

## ✅ Summary

**singleton-service** provides dependency injection that is:

- **Simple** - Declarative dependencies with `@requires`
- **Automatic** - No configuration or setup required
- **Type-safe** - Full IDE support and static analysis
- **Testable** - Easy to mock and reset for testing
- **Performant** - Minimal overhead after initialization

### Key Advantages

1. **Zero configuration** - No XML, no container setup
2. **Declarative dependencies** - Clear, visible relationships
3. **Automatic resolution** - Framework handles initialization order
4. **Lazy initialization** - Services created when needed
5. **Easy testing** - Simple mocking and reset

### When to Use Other DI Frameworks

Consider traditional DI frameworks when you need:
- Multiple service lifetimes (scoped, transient)
- Complex configuration scenarios
- Integration with existing DI infrastructure
- Dynamic service discovery at runtime

For most Python applications, **singleton-service** provides a simpler, more Pythonic approach to dependency injection.

---

**Next**: Understand the service lifecycle → [Service Initialization](initialization.md)