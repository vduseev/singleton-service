# The Singleton Pattern

The singleton pattern is one of the most discussed (and sometimes controversial) design patterns in software engineering. **singleton-service** takes a fresh approach to singletons that addresses common criticisms while preserving the benefits.

## 🤔 What Is a Singleton?

A **singleton** ensures that a class has only one instance and provides global access to that instance. In traditional implementations:

```python
# Traditional singleton (problematic)
class Database:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

## 🚫 Problems with Traditional Singletons

Traditional singleton implementations have several well-known issues:

### 1. Hidden Dependencies
```python
class UserService:
    def get_user(self, user_id):
        db = Database()  # ❌ Hidden dependency!
        return db.query("SELECT * FROM users WHERE id = ?", user_id)
```

The dependency on `Database` is hidden inside the method, making testing and understanding difficult.

### 2. Global State Issues
```python
# ❌ Hard to test, shared state between tests
db = Database()
db.connection = "production_db"  # Oops! All tests use production DB
```

### 3. Initialization Timing Problems
```python
class Database:
    def __init__(self):
        self.connection = connect_to_db()  # ❌ When does this happen?
        
# What if connection fails during import?
db = Database()  # ❌ Might fail at import time
```

### 4. Testing Difficulties
```python
def test_user_service():
    # ❌ How do we mock the database?
    # ❌ How do we reset state between tests?
    user = UserService().get_user(123)
    assert user.name == "Test User"
```

## ✅ The singleton-service Approach

**singleton-service** solves these problems with a different approach:

### 1. Explicit Dependencies
```python
@requires(DatabaseService)  # ✅ Dependencies are explicit
class UserService(BaseService):
    @classmethod
    @guarded
    def get_user(cls, user_id: int) -> User:
        return DatabaseService.query_user(user_id)
```

Dependencies are declared upfront, making them visible and testable.

### 2. No Global State
```python
class DatabaseService(BaseService):
    _connection: ClassVar[Optional[Connection]] = None  # ✅ Controlled state
    
    @classmethod
    def initialize(cls) -> None:
        cls._connection = create_connection()  # ✅ Controlled initialization
```

State is managed through class variables with clear initialization.

### 3. Lazy Initialization
```python
# ✅ Nothing initializes until first use
user = UserService.get_user(123)  # Initialization happens here
```

Services initialize only when needed, in the correct order.

### 4. Testing Support
```python
def test_user_service():
    # ✅ Easy to reset and mock
    reset_services(DatabaseService, UserService)
    MockDatabaseService.set_test_data({123: User("Test User")})
    
    user = UserService.get_user(123)
    assert user.name == "Test User"
```

## 🎯 When to Use Singletons

Singletons are appropriate for:

### ✅ Good Use Cases

**Infrastructure Services**
```python
class DatabaseService(BaseService):
    """Manages database connections and queries."""
    # One connection pool per application
```

**Configuration Management**
```python
class ConfigService(BaseService):
    """Loads and provides application configuration."""
    # One configuration per application
```

**External Service Clients**
```python
class PaymentService(BaseService):
    """Handles payment processing with external APIs."""
    # One API client with shared authentication
```

**Resource Managers**
```python
class FileStorageService(BaseService):
    """Manages file uploads and downloads."""
    # Shared storage configuration and connections
```

### ❌ Poor Use Cases

**Business Logic Objects**
```python
# ❌ Don't make business objects singletons
class User(BaseService):  # Bad! Users should be instances
    pass
```

**Stateful Data Objects**
```python
# ❌ Don't make data containers singletons
class ShoppingCart(BaseService):  # Bad! Each user has their own cart
    pass
```

**Frequently Created Objects**
```python
# ❌ Don't make temporary objects singletons
class EmailMessage(BaseService):  # Bad! Each message is unique
    pass
```

## 🔄 Singleton vs Alternatives

### Singleton vs Global Variables

=== "❌ Global Variables"
    ```python
    # Hard to test, no initialization control
    DATABASE_CONNECTION = None
    API_CLIENT = None
    
    def get_user(user_id):
        global DATABASE_CONNECTION
        if DATABASE_CONNECTION is None:  # Manual checks everywhere
            DATABASE_CONNECTION = create_connection()
        return DATABASE_CONNECTION.query(user_id)
    ```

=== "✅ Singleton Service"
    ```python
    # Controlled initialization, easy to test
    class DatabaseService(BaseService):
        _connection: ClassVar[Optional[Connection]] = None
        
        @classmethod
        def initialize(cls) -> None:
            cls._connection = create_connection()
        
        @classmethod
        @guarded  # Automatic initialization
        def query_user(cls, user_id: int) -> User:
            return cls._connection.query(user_id)
    ```

### Singleton vs Dependency Injection Containers

=== "❌ DI Container"
    ```python
    # Complex setup, lots of configuration
    container = Container()
    container.bind(Database, DatabaseImpl)
    container.bind(UserService, UserServiceImpl)
    
    # Must remember to configure everything
    user_service = container.get(UserService)
    user = user_service.get_user(123)
    ```

=== "✅ Singleton Service"
    ```python
    # Simple, declarative
    @requires(DatabaseService)
    class UserService(BaseService):
        @classmethod
        @guarded
        def get_user(cls, user_id: int) -> User:
            return DatabaseService.query_user(user_id)
    
    # Just use it
    user = UserService.get_user(123)
    ```

### Singleton vs Static Classes

=== "❌ Static Classes"
    ```python
    # No initialization control, hidden dependencies
    class DatabaseUtils:
        @staticmethod
        def get_user(user_id):
            # How do we know when connection is ready?
            return some_global_connection.query(user_id)
    ```

=== "✅ Singleton Service"
    ```python
    # Controlled lifecycle, explicit dependencies
    class DatabaseService(BaseService):
        @classmethod
        def initialize(cls) -> None:
            cls._connection = create_connection()
        
        @classmethod
        @guarded
        def get_user(cls, user_id: int) -> User:
            return cls._connection.query(user_id)
    ```

## 🧵 Thread Safety Considerations

### Framework Thread Safety

**singleton-service** provides basic thread safety guarantees:

```python
class DatabaseService(BaseService):
    _connection: ClassVar[Optional[Connection]] = None
    
    @classmethod
    def initialize(cls) -> None:
        # ✅ Called only once per service
        cls._connection = create_connection()
    
    @classmethod
    @guarded
    def query(cls, sql: str) -> List[Dict]:
        # ⚠️  Your responsibility to ensure thread safety here
        return cls._connection.execute(sql)
```

**Framework guarantees:**
- Services initialize only once
- `@guarded` methods ensure initialization before execution
- Dependency order is respected

**Your responsibility:**
- Make your service methods thread-safe
- Use appropriate connection pooling
- Protect shared state with locks if needed

### Thread-Safe Service Example

```python
import threading
from typing import ClassVar

class ThreadSafeService(BaseService):
    _lock: ClassVar[threading.Lock] = threading.Lock()
    _counter: ClassVar[int] = 0
    
    @classmethod
    def initialize(cls) -> None:
        cls._counter = 0
    
    @classmethod
    @guarded
    def increment(cls) -> int:
        with cls._lock:  # ✅ Thread-safe access
            cls._counter += 1
            return cls._counter
```

## 📊 Performance Implications

### Initialization Overhead

```python
# First call: Initialization + Method execution
result1 = DatabaseService.query("SELECT 1")  # ~100ms (initialization)

# Subsequent calls: Just method execution  
result2 = DatabaseService.query("SELECT 2")  # ~1ms (no initialization)
```

### Memory Usage

```python
class DatabaseService(BaseService):
    # ✅ One connection pool shared across application
    _connection_pool: ClassVar[ConnectionPool] = None
    
    # vs multiple instances:
    # ❌ db1 = DatabaseService()  # Each would have own pool
    # ❌ db2 = DatabaseService()  # Wasteful!
```

### Method Call Overhead

```python
# @guarded methods have minimal overhead after initialization
@classmethod
@guarded  # ~0.001ms overhead per call
def fast_method(cls) -> str:
    return "Fast!"
```

## 🎯 Design Guidelines

### Service Boundaries

**Good service design:**
```python
class PaymentService(BaseService):
    """Handles all payment-related operations."""
    
    @classmethod
    @guarded
    def process_payment(cls, amount: Decimal, card: Card) -> PaymentResult:
        pass
    
    @classmethod
    @guarded
    def refund_payment(cls, payment_id: str) -> RefundResult:
        pass
```

**Avoid over-granular services:**
```python
# ❌ Too many small services
class PaymentValidationService(BaseService): pass
class PaymentProcessingService(BaseService): pass  
class PaymentLoggingService(BaseService): pass
class PaymentNotificationService(BaseService): pass
```

### State Management

**Good state management:**
```python
class CacheService(BaseService):
    _redis_client: ClassVar[Optional[Redis]] = None
    _stats: ClassVar[Dict[str, int]] = {}  # Shared application state
    
    @classmethod
    def initialize(cls) -> None:
        cls._redis_client = Redis()
        cls._stats = {"hits": 0, "misses": 0}
```

**Avoid user-specific state:**
```python
class BadUserService(BaseService):
    _current_user: ClassVar[Optional[User]] = None  # ❌ Wrong!
    
    # User data should not be singleton state
    # Each user should have their own data
```

## ✅ Summary

The singleton pattern, when implemented correctly, provides:

- **Controlled resource management** - One connection pool, not many
- **Explicit dependencies** - Clear service relationships
- **Lazy initialization** - Resources created when needed
- **Testability** - Easy to mock and reset
- **Performance** - Shared resources, minimal overhead

**singleton-service** addresses traditional singleton problems while preserving the benefits for service-oriented architectures.

### Key Takeaways

1. **Use singletons for services, not data** - Infrastructure, not business objects
2. **Declare dependencies explicitly** - Make relationships visible
3. **Initialize lazily** - Resources created when first needed
4. **Design for testability** - Support mocking and reset
5. **Consider thread safety** - Protect shared state appropriately

---

**Next**: Learn how dependency injection works → [Dependency Injection](dependency-injection.md)