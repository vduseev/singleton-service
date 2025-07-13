# Service Initialization

Understanding the service initialization lifecycle is crucial for building reliable applications with **singleton-service**. This section covers initialization patterns, timing, state management, and performance considerations.

## 🔄 Initialization Lifecycle

### The Complete Lifecycle

Every service goes through these phases:

```python
# Phase 1: Definition
class MyService(BaseService):  # Service class defined
    _data: ClassVar[Optional[Any]] = None

# Phase 2: Declaration  
@requires(OtherService)       # Dependencies declared
class MyService(BaseService): pass

# Phase 3: First Access
result = MyService.method()   # Triggers initialization

# Phase 4: Initialization
# 1. Dependency analysis
# 2. Order calculation  
# 3. Dependency initialization
# 4. Service initialization
# 5. Health check
# 6. Method execution

# Phase 5: Operational
result2 = MyService.method()  # No re-initialization
```

### Initialization Trigger Points

Initialization happens automatically on **first access** to a `@guarded` method:

```python
class DatabaseService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        print("Database initializing...")
    
    @classmethod
    @guarded
    def query(cls, sql: str) -> List[Dict]:
        return cls._connection.execute(sql)

# Service defined but not initialized
print("Service defined")

# First @guarded method call triggers initialization
result = DatabaseService.query("SELECT 1")  # ← Initialization happens here
print("Query completed")

# Subsequent calls are fast
result2 = DatabaseService.query("SELECT 2")  # ← No initialization
```

Output:
```
Service defined
Database initializing...
Query completed
```

## ⚡ Lazy vs Eager Initialization

### Lazy Initialization (Default)

**singleton-service** uses lazy initialization by default:

```python
class ExpensiveService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        # This expensive operation only happens when needed
        cls._ml_model = load_machine_learning_model()  # Takes 10 seconds
        cls._database = connect_to_database()          # Takes 2 seconds
        print("Expensive service ready")
    
    @classmethod
    @guarded
    def predict(cls, data: List[float]) -> float:
        return cls._ml_model.predict(data)

# Application starts instantly - no initialization yet
print("Application started")  # ← Instant

# Initialization happens when service is first used
prediction = ExpensiveService.predict([1, 2, 3])  # ← 12 seconds delay here
```

**Benefits of lazy initialization:**
- Fast application startup
- Resources allocated only when needed
- Memory efficient for unused services
- Better error isolation

### Eager Initialization Pattern

For critical services that should initialize at startup:

```python
class CriticalService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        cls._connection = create_critical_connection()
        print("Critical service initialized")
    
    @classmethod
    @guarded
    def critical_operation(cls) -> str:
        return "Critical result"

# Force eager initialization at application startup
def initialize_critical_services():
    """Initialize critical services at startup."""
    try:
        # Trigger initialization by calling a @guarded method
        CriticalService.critical_operation()
        print("All critical services ready")
    except Exception as e:
        print(f"Critical service initialization failed: {e}")
        raise SystemExit(1)

if __name__ == "__main__":
    initialize_critical_services()  # Initialize at startup
    # Rest of application starts with services ready
```

## 🏗️ Initialization Patterns

### Basic Initialization

Simple resource setup:

```python
class ConfigService(BaseService):
    _config: ClassVar[Dict[str, Any]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        """Load configuration from environment and files."""
        # Load from environment variables
        cls._config["database_url"] = os.getenv("DATABASE_URL", "sqlite:///default.db")
        cls._config["api_key"] = os.getenv("API_KEY")
        cls._config["debug"] = os.getenv("DEBUG", "false").lower() == "true"
        
        # Load from config file if exists
        config_file = Path("config.json")
        if config_file.exists():
            with config_file.open() as f:
                file_config = json.load(f)
                cls._config.update(file_config)
        
        print(f"Configuration loaded: {len(cls._config)} settings")
```

### Connection Pooling

Managing expensive resources:

```python
class DatabaseService(BaseService):
    _connection_pool: ClassVar[Optional[ConnectionPool]] = None
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize database connection pool."""
        database_url = ConfigService.get("database_url")
        
        cls._connection_pool = ConnectionPool(
            database_url,
            min_connections=5,
            max_connections=20,
            connection_timeout=30
        )
        
        # Test the pool
        with cls._connection_pool.get_connection() as conn:
            conn.execute("SELECT 1")
        
        print(f"Database pool initialized with {cls._connection_pool.size} connections")
    
    @classmethod
    def ping(cls) -> bool:
        """Verify database connection health."""
        if not cls._connection_pool:
            return False
        
        try:
            with cls._connection_pool.get_connection(timeout=5) as conn:
                result = conn.execute("SELECT 1").fetchone()
                return result == (1,)
        except Exception:
            return False
```

### API Client Initialization

Setting up external service clients:

```python
class PaymentService(BaseService):
    _client: ClassVar[Optional[PaymentClient]] = None
    _webhook_secret: ClassVar[Optional[str]] = None
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize payment service client."""
        api_key = ConfigService.get("payment_api_key")
        environment = ConfigService.get("payment_environment", "sandbox")
        
        if not api_key:
            raise ValueError("Payment API key is required")
        
        cls._client = PaymentClient(
            api_key=api_key,
            environment=environment,
            timeout=30,
            retry_count=3
        )
        
        cls._webhook_secret = ConfigService.get("payment_webhook_secret")
        
        print(f"Payment service initialized for {environment}")
    
    @classmethod
    def ping(cls) -> bool:
        """Test payment service connectivity."""
        try:
            # Test API connectivity with a simple call
            result = cls._client.test_connection()
            return result.status == "ok"
        except Exception as e:
            print(f"Payment service health check failed: {e}")
            return False
```

### Composite Initialization

Services that coordinate multiple resources:

```python
@requires(ConfigService, DatabaseService, LoggingService)
class ApplicationService(BaseService):
    _metrics: ClassVar[Dict[str, int]] = {}
    _background_tasks: ClassVar[List[asyncio.Task]] = []
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize application-level coordination."""
        # Initialize metrics
        cls._metrics = {
            "requests_processed": 0,
            "errors_encountered": 0,
            "uptime_start": int(time.time())
        }
        
        # Start background tasks
        if ConfigService.get("enable_background_cleanup", True):
            cls._start_background_tasks()
        
        # Register shutdown handlers
        atexit.register(cls._cleanup)
        
        LoggingService.info("Application service initialized")
    
    @classmethod
    def _start_background_tasks(cls) -> None:
        """Start background maintenance tasks."""
        # Note: This is a simplified example
        # Real implementation would use proper async task management
        print("Background tasks started")
    
    @classmethod
    def _cleanup(cls) -> None:
        """Cleanup resources on shutdown."""
        LoggingService.info("Application service shutting down")
        # Cancel background tasks, close connections, etc.
```

## 🔧 State Management

### Class Variable Patterns

**singleton-service** stores state in class variables:

```python
from typing import ClassVar, Optional, Dict, List

class StateExamples(BaseService):
    # Nullable values - use Optional
    _connection: ClassVar[Optional[Connection]] = None
    _client: ClassVar[Optional[APIClient]] = None
    
    # Collections - initialize to empty
    _cache: ClassVar[Dict[str, Any]] = {}
    _queue: ClassVar[List[Task]] = []
    _active_sessions: ClassVar[Set[str]] = set()
    
    # Configuration values - provide defaults
    _timeout: ClassVar[int] = 30
    _max_retries: ClassVar[int] = 3
    _debug_mode: ClassVar[bool] = False
    
    # Complex objects
    _thread_pool: ClassVar[Optional[ThreadPoolExecutor]] = None
    _scheduler: ClassVar[Optional[BackgroundScheduler]] = None
```

### State Initialization

Reset and initialize state properly:

```python
class CacheService(BaseService):
    _data: ClassVar[Dict[str, Any]] = {}
    _stats: ClassVar[Dict[str, int]] = {}
    _last_cleanup: ClassVar[float] = 0
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize cache state."""
        # Reset state to known values
        cls._data = {}
        cls._stats = {
            "hits": 0,
            "misses": 0, 
            "evictions": 0
        }
        cls._last_cleanup = time.time()
        
        # Start background cleanup if needed
        cls._schedule_cleanup()
    
    @classmethod
    def ping(cls) -> bool:
        """Verify cache is working."""
        # Test basic functionality
        test_key = "__health_check__"
        cls._data[test_key] = "ok"
        result = cls._data.get(test_key) == "ok"
        cls._data.pop(test_key, None)
        return result
```

### Thread-Safe State

When services are accessed from multiple threads:

```python
import threading
from typing import ClassVar

class ThreadSafeCacheService(BaseService):
    _data: ClassVar[Dict[str, Any]] = {}
    _lock: ClassVar[threading.RLock] = threading.RLock()
    _stats: ClassVar[Dict[str, int]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        cls._data = {}
        cls._stats = {"hits": 0, "misses": 0}
    
    @classmethod
    @guarded
    def get(cls, key: str) -> Optional[Any]:
        """Thread-safe cache get."""
        with cls._lock:
            if key in cls._data:
                cls._stats["hits"] += 1
                return cls._data[key]
            else:
                cls._stats["misses"] += 1
                return None
    
    @classmethod
    @guarded  
    def set(cls, key: str, value: Any) -> None:
        """Thread-safe cache set."""
        with cls._lock:
            cls._data[key] = value
```

## ⚠️ Initialization Pitfalls

### Common Mistakes

**Calling @guarded methods from initialize():**
```python
class BadService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        # ❌ This raises SelfDependencyError!
        cls.load_data()
    
    @classmethod
    @guarded
    def load_data(cls) -> None:
        pass
```

**Fix:** Move logic directly into `initialize()`:
```python
class GoodService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        # ✅ Direct implementation
        cls._data = load_initial_data()
    
    @classmethod
    @guarded
    def get_data(cls) -> Any:
        return cls._data
```

**Assuming initialization order:**
```python
class BadService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        # ❌ Assuming DatabaseService is already initialized
        if not DatabaseService._initialized:
            raise RuntimeError("Database not ready!")
```

**Fix:** Use `@requires` to declare dependencies:
```python
@requires(DatabaseService)
class GoodService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        # ✅ DatabaseService guaranteed to be ready
        cls._connection = DatabaseService.get_connection()
```

### Error Handling in Initialization

Proper error handling during initialization:

```python
class RobustService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        """Initialize with comprehensive error handling."""
        try:
            # Validate configuration
            api_key = ConfigService.get("api_key")
            if not api_key:
                raise ValueError("API key is required but not configured")
            
            # Create client with validation
            cls._client = APIClient(api_key)
            
            # Test connectivity
            test_result = cls._client.test_connection()
            if not test_result.success:
                raise ConnectionError(f"API connection test failed: {test_result.error}")
            
            LoggingService.info("Robust service initialized successfully")
            
        except ValueError as e:
            raise ServiceInitializationError(f"Configuration error: {e}")
        except ConnectionError as e:
            raise ServiceInitializationError(f"Connection error: {e}")
        except Exception as e:
            raise ServiceInitializationError(f"Unexpected initialization error: {e}")
```

## 📊 Performance Considerations

### Initialization Cost

Measure and optimize initialization time:

```python
import time

class MonitoredService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        """Initialization with performance monitoring."""
        start_time = time.time()
        
        # Expensive operations
        cls._load_configuration()      # ~100ms
        cls._connect_to_database()     # ~500ms  
        cls._warm_up_cache()          # ~200ms
        cls._start_background_tasks()  # ~50ms
        
        total_time = time.time() - start_time
        print(f"Service initialized in {total_time:.2f}s")
        
        # Log slow initialization
        if total_time > 1.0:
            LoggingService.warning(f"Slow initialization: {total_time:.2f}s")
```

### Memory Usage

Optimize memory usage during initialization:

```python
class MemoryEfficientService(BaseService):
    _large_dataset: ClassVar[Optional[Any]] = None
    
    @classmethod
    def initialize(cls) -> None:
        """Memory-efficient initialization."""
        # Load data lazily, not all at once
        cls._data_loader = DataLoader("large_dataset.db")
        
        # Pre-load only essential data
        cls._metadata = cls._data_loader.load_metadata()
        
        # Large dataset loaded on-demand in methods
        cls._large_dataset = None  # Loaded later
    
    @classmethod
    @guarded
    def get_data(cls, key: str) -> Any:
        """Load large dataset only when needed."""
        if cls._large_dataset is None:
            cls._large_dataset = cls._data_loader.load_full_dataset()
        
        return cls._large_dataset.get(key)
```

### Parallel Initialization

While **singleton-service** initializes services sequentially, you can optimize within services:

```python
import asyncio
import concurrent.futures

class ParallelInitService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        """Initialize multiple resources in parallel."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Submit multiple initialization tasks
            future_db = executor.submit(cls._init_database)
            future_cache = executor.submit(cls._init_cache)  
            future_api = executor.submit(cls._init_api_client)
            
            # Wait for all to complete
            cls._database = future_db.result()
            cls._cache = future_cache.result()
            cls._api_client = future_api.result()
    
    @classmethod
    def _init_database(cls) -> Database:
        return Database.connect(ConfigService.get("db_url"))
    
    @classmethod 
    def _init_cache(cls) -> Cache:
        return Cache.connect(ConfigService.get("cache_url"))
    
    @classmethod
    def _init_api_client(cls) -> APIClient:
        return APIClient(ConfigService.get("api_key"))
```

## ✅ Summary

Service initialization in **singleton-service** provides:

- **Lazy initialization** - Services initialize only when needed
- **Dependency ordering** - Framework ensures correct initialization sequence
- **Error handling** - Clear error messages for initialization failures
- **State management** - Clean patterns for service state
- **Performance control** - Optimize initialization timing and resource usage

### Best Practices

1. **Keep initialize() focused** - Set up resources, don't do business logic
2. **Use ping() for validation** - Verify service health after initialization
3. **Handle errors gracefully** - Provide clear error messages
4. **Optimize for your use case** - Lazy for most services, eager for critical ones
5. **Measure performance** - Monitor initialization time and optimize bottlenecks

---

**Next**: Learn about comprehensive error handling → [Error Handling](error-handling.md)