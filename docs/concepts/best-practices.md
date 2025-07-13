# Best Practices

This guide covers production-ready patterns, performance optimization, security considerations, and architectural guidelines for building robust applications with **singleton-service**.

## 🏗️ Service Design Principles

### Single Responsibility Principle

Each service should have one clear responsibility:

```python
# ✅ Good: Focused responsibility
class DatabaseService(BaseService):
    """Handles all database operations."""
    
    @classmethod
    @guarded
    def query_user(cls, user_id: int) -> User: pass
    
    @classmethod
    @guarded
    def create_user(cls, user: User) -> int: pass
    
    @classmethod
    @guarded
    def update_user(cls, user: User) -> None: pass

# ❌ Bad: Multiple responsibilities
class MegaService(BaseService):
    """Does everything - database, emails, payments, logging..."""
    
    @classmethod
    @guarded
    def query_user(cls, user_id: int) -> User: pass
    
    @classmethod
    @guarded
    def send_email(cls, to: str, message: str) -> None: pass
    
    @classmethod
    @guarded
    def process_payment(cls, amount: Decimal) -> bool: pass
```

### Service Boundaries

Design clear boundaries between services:

```python
# Infrastructure Layer - No business logic
@requires()
class ConfigService(BaseService):
    """Application configuration management."""
    pass

@requires(ConfigService)  
class DatabaseService(BaseService):
    """Database connection and basic queries."""
    pass

@requires(ConfigService)
class EmailService(BaseService):
    """Email sending infrastructure."""
    pass

# Domain Layer - Business logic
@requires(DatabaseService)
class UserRepository(BaseService):
    """User data access and persistence."""
    pass

@requires(UserRepository, EmailService)
class UserService(BaseService):
    """User business logic and workflows."""
    pass

# Application Layer - Orchestration
@requires(UserService)
class UserController(BaseService):
    """User API endpoints and request handling."""
    pass
```

### Dependency Direction

Dependencies should flow toward stability:

```python
# ✅ Stable dependencies (change rarely)
class ConfigService(BaseService): pass
class LoggingService(BaseService): pass
class DatabaseService(BaseService): pass

# ✅ Business services depend on stable infrastructure
@requires(DatabaseService, LoggingService)
class UserService(BaseService): pass

# ✅ Application services depend on business services
@requires(UserService)
class WebAPIService(BaseService): pass

# ❌ Avoid: Infrastructure depending on business logic
@requires(UserService)  # Wrong direction!
class DatabaseService(BaseService): pass
```

## 🔧 Implementation Best Practices

### State Management

Follow these patterns for service state:

```python
from typing import ClassVar, Optional, Dict, List
import threading

class WellDesignedService(BaseService):
    # ✅ Use ClassVar for type safety
    _connection: ClassVar[Optional[Connection]] = None
    _config: ClassVar[Dict[str, Any]] = {}
    _cache: ClassVar[Dict[str, Any]] = {}
    
    # ✅ Initialize collections to empty containers
    _active_sessions: ClassVar[Set[str]] = set()
    _request_queue: ClassVar[List[Request]] = []
    
    # ✅ Thread safety when needed
    _lock: ClassVar[threading.RLock] = threading.RLock()
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize with clean state."""
        # ✅ Reset state to known values
        cls._config = {}
        cls._cache = {}
        cls._active_sessions = set()
        cls._request_queue = []
        
        # ✅ Set up resources
        cls._connection = create_connection()
    
    @classmethod
    @guarded
    def thread_safe_operation(cls, data: str) -> str:
        """Use locks for thread safety when needed."""
        with cls._lock:
            # Critical section
            cls._active_sessions.add(data)
            result = cls._process_data(data)
            cls._active_sessions.remove(data)
            return result
```

### Configuration Management

Centralize configuration with validation:

```python
from typing import ClassVar, Optional
import os
from dataclasses import dataclass

@dataclass
class AppConfig:
    """Type-safe application configuration."""
    database_url: str
    api_key: str
    debug_mode: bool
    max_connections: int
    timeout_seconds: int

class ConfigService(BaseService):
    _config: ClassVar[Optional[AppConfig]] = None
    
    @classmethod
    def initialize(cls) -> None:
        """Load and validate configuration."""
        # Load from environment with validation
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        api_key = os.getenv("API_KEY")
        if not api_key:
            raise ValueError("API_KEY environment variable is required")
        
        # Parse and validate values
        try:
            max_connections = int(os.getenv("MAX_CONNECTIONS", "10"))
            timeout_seconds = int(os.getenv("TIMEOUT_SECONDS", "30"))
        except ValueError as e:
            raise ValueError(f"Invalid configuration value: {e}")
        
        # Validate ranges
        if max_connections < 1 or max_connections > 100:
            raise ValueError("MAX_CONNECTIONS must be between 1 and 100")
        
        if timeout_seconds < 1 or timeout_seconds > 300:
            raise ValueError("TIMEOUT_SECONDS must be between 1 and 300")
        
        cls._config = AppConfig(
            database_url=database_url,
            api_key=api_key,
            debug_mode=os.getenv("DEBUG", "false").lower() == "true",
            max_connections=max_connections,
            timeout_seconds=timeout_seconds
        )
    
    @classmethod
    @guarded
    def get_config(cls) -> AppConfig:
        """Get validated configuration."""
        return cls._config
    
    @classmethod
    @guarded
    def get(cls, key: str) -> Any:
        """Get configuration value by key."""
        return getattr(cls._config, key)
```

### Resource Management

Properly manage external resources:

```python
import atexit
from contextlib import contextmanager

class ResourceManagedService(BaseService):
    _connection_pool: ClassVar[Optional[ConnectionPool]] = None
    _thread_pool: ClassVar[Optional[ThreadPoolExecutor]] = None
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize resources with cleanup registration."""
        # Create connection pool
        cls._connection_pool = ConnectionPool(
            url=ConfigService.get("database_url"),
            min_connections=5,
            max_connections=ConfigService.get("max_connections")
        )
        
        # Create thread pool
        cls._thread_pool = ThreadPoolExecutor(
            max_workers=4,
            thread_name_prefix="resource_service"
        )
        
        # Register cleanup on application exit
        atexit.register(cls._cleanup)
    
    @classmethod
    def _cleanup(cls) -> None:
        """Clean up resources on shutdown."""
        if cls._connection_pool:
            cls._connection_pool.close()
            cls._connection_pool = None
        
        if cls._thread_pool:
            cls._thread_pool.shutdown(wait=True)
            cls._thread_pool = None
    
    @classmethod
    @contextmanager
    def get_connection(cls):
        """Context manager for database connections."""
        connection = cls._connection_pool.get_connection()
        try:
            yield connection
        finally:
            cls._connection_pool.return_connection(connection)
    
    @classmethod
    @guarded
    def execute_query(cls, sql: str, params: tuple = ()) -> List[Dict]:
        """Execute query with proper resource management."""
        with cls.get_connection() as conn:
            return conn.execute(sql, params).fetchall()
```

## 🚀 Performance Optimization

### Lazy Loading Patterns

Optimize memory usage with lazy loading:

```python
class LazyLoadingService(BaseService):
    _metadata: ClassVar[Optional[Dict]] = None
    _large_dataset: ClassVar[Optional[Any]] = None
    _expensive_client: ClassVar[Optional[Any]] = None
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize only essential data."""
        # Load small, essential data immediately
        cls._metadata = load_metadata()
        
        # Large/expensive resources loaded on demand
        cls._large_dataset = None
        cls._expensive_client = None
    
    @classmethod
    @guarded
    def get_data(cls, key: str) -> Any:
        """Load large dataset only when needed."""
        if cls._large_dataset is None:
            cls._large_dataset = load_large_dataset()  # Expensive operation
        return cls._large_dataset.get(key)
    
    @classmethod
    @guarded
    def call_expensive_api(cls, request: str) -> str:
        """Initialize expensive client only when needed."""
        if cls._expensive_client is None:
            cls._expensive_client = ExpensiveAPIClient()  # Slow initialization
        return cls._expensive_client.call(request)
```

### Caching Strategies

Implement effective caching:

```python
import time
from typing import ClassVar, Tuple, Any

class CachingService(BaseService):
    _cache: ClassVar[Dict[str, Tuple[Any, float]]] = {}
    _cache_ttl: ClassVar[int] = 300  # 5 minutes
    _cache_stats: ClassVar[Dict[str, int]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        cls._cache = {}
        cls._cache_stats = {"hits": 0, "misses": 0, "evictions": 0}
    
    @classmethod
    @guarded
    def get_expensive_data(cls, key: str) -> Any:
        """Get data with caching."""
        # Check cache first
        cached_result = cls._get_from_cache(key)
        if cached_result is not None:
            cls._cache_stats["hits"] += 1
            return cached_result
        
        # Cache miss - compute and cache
        cls._cache_stats["misses"] += 1
        result = cls._compute_expensive_data(key)
        cls._set_cache(key, result)
        
        return result
    
    @classmethod
    def _get_from_cache(cls, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key not in cls._cache:
            return None
        
        value, timestamp = cls._cache[key]
        if time.time() - timestamp > cls._cache_ttl:
            # Expired - remove from cache
            del cls._cache[key]
            cls._cache_stats["evictions"] += 1
            return None
        
        return value
    
    @classmethod
    def _set_cache(cls, key: str, value: Any) -> None:
        """Set value in cache with timestamp."""
        cls._cache[key] = (value, time.time())
    
    @classmethod
    def _compute_expensive_data(cls, key: str) -> Any:
        """Simulate expensive computation."""
        time.sleep(0.1)  # Simulate work
        return f"Computed result for {key}"
    
    @classmethod
    @guarded
    def get_cache_stats(cls) -> Dict[str, int]:
        """Get cache performance statistics."""
        total_requests = cls._cache_stats["hits"] + cls._cache_stats["misses"]
        hit_rate = cls._cache_stats["hits"] / max(total_requests, 1) * 100
        
        return {
            **cls._cache_stats,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
            "cache_size": len(cls._cache)
        }
```

### Connection Pooling

Implement efficient connection pooling:

```python
import queue
import threading
from contextlib import contextmanager

class ConnectionPoolService(BaseService):
    _pool: ClassVar[Optional[queue.Queue]] = None
    _pool_size: ClassVar[int] = 10
    _pool_lock: ClassVar[threading.Lock] = threading.Lock()
    _active_connections: ClassVar[int] = 0
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize connection pool."""
        cls._pool = queue.Queue(maxsize=cls._pool_size)
        cls._active_connections = 0
        
        # Pre-populate pool with connections
        for _ in range(cls._pool_size):
            connection = cls._create_connection()
            cls._pool.put(connection)
    
    @classmethod
    def _create_connection(cls) -> Any:
        """Create a new database connection."""
        return create_database_connection(ConfigService.get("database_url"))
    
    @classmethod
    @contextmanager
    def get_connection(cls, timeout: float = 30.0):
        """Get connection from pool with timeout."""
        connection = None
        try:
            # Get connection from pool
            connection = cls._pool.get(timeout=timeout)
            
            with cls._pool_lock:
                cls._active_connections += 1
            
            # Test connection before use
            if not cls._test_connection(connection):
                connection = cls._create_connection()
            
            yield connection
            
        except queue.Empty:
            raise RuntimeError(f"No database connections available within {timeout}s")
        finally:
            if connection:
                with cls._pool_lock:
                    cls._active_connections -= 1
                
                # Return connection to pool
                try:
                    cls._pool.put_nowait(connection)
                except queue.Full:
                    # Pool is full, close this connection
                    connection.close()
    
    @classmethod
    def _test_connection(cls, connection: Any) -> bool:
        """Test if connection is still valid."""
        try:
            connection.execute("SELECT 1")
            return True
        except Exception:
            return False
    
    @classmethod
    @guarded
    def get_pool_stats(cls) -> Dict[str, int]:
        """Get connection pool statistics."""
        with cls._pool_lock:
            return {
                "pool_size": cls._pool_size,
                "available_connections": cls._pool.qsize(),
                "active_connections": cls._active_connections,
                "utilization_percent": round(cls._active_connections / cls._pool_size * 100, 2)
            }
```

## 🔒 Security Best Practices

### Secure Configuration

Never expose secrets in code:

```python
import os
from cryptography.fernet import Fernet

class SecureConfigService(BaseService):
    _encryption_key: ClassVar[Optional[bytes]] = None
    _secrets: ClassVar[Dict[str, str]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize secure configuration."""
        # Get encryption key from environment
        key_b64 = os.getenv("ENCRYPTION_KEY")
        if not key_b64:
            raise ValueError("ENCRYPTION_KEY environment variable is required")
        
        try:
            cls._encryption_key = key_b64.encode()
            cipher = Fernet(cls._encryption_key)
        except Exception as e:
            raise ValueError(f"Invalid encryption key: {e}")
        
        # Load encrypted secrets
        cls._load_encrypted_secrets(cipher)
    
    @classmethod
    def _load_encrypted_secrets(cls, cipher: Fernet) -> None:
        """Load and decrypt secrets."""
        # Load encrypted secrets from secure storage
        encrypted_secrets = {
            "database_password": os.getenv("DB_PASSWORD_ENCRYPTED"),
            "api_key": os.getenv("API_KEY_ENCRYPTED"),
        }
        
        cls._secrets = {}
        for key, encrypted_value in encrypted_secrets.items():
            if encrypted_value:
                try:
                    decrypted = cipher.decrypt(encrypted_value.encode()).decode()
                    cls._secrets[key] = decrypted
                except Exception as e:
                    raise ValueError(f"Failed to decrypt {key}: {e}")
    
    @classmethod
    @guarded
    def get_secret(cls, key: str) -> Optional[str]:
        """Get decrypted secret."""
        return cls._secrets.get(key)
    
    @classmethod
    @guarded
    def get_database_url(cls) -> str:
        """Get database URL with decrypted password."""
        base_url = os.getenv("DATABASE_BASE_URL", "postgresql://user@host/db")
        password = cls.get_secret("database_password")
        
        if password:
            # Insert password into URL securely
            return base_url.replace("@", f":{password}@")
        return base_url
```

### Input Validation

Always validate inputs:

```python
from typing import Union
import re

class ValidationService(BaseService):
    _email_regex: ClassVar[re.Pattern] = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    _phone_regex: ClassVar[re.Pattern] = re.compile(r'^\+?1?[0-9]{10,15}$')
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize validation patterns."""
        # Validation patterns are compiled at class level
        pass
    
    @classmethod
    @guarded
    def validate_email(cls, email: str) -> str:
        """Validate and normalize email address."""
        if not email:
            raise ValueError("Email is required")
        
        email = email.strip().lower()
        
        if len(email) > 255:
            raise ValueError("Email address too long")
        
        if not cls._email_regex.match(email):
            raise ValueError("Invalid email format")
        
        return email
    
    @classmethod
    @guarded
    def validate_user_input(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate user input data."""
        validated = {}
        
        # Required fields
        required_fields = ["name", "email"]
        for field in required_fields:
            if field not in data or not data[field]:
                raise ValueError(f"{field} is required")
        
        # Validate name
        name = str(data["name"]).strip()
        if len(name) < 2 or len(name) > 100:
            raise ValueError("Name must be between 2 and 100 characters")
        
        if not re.match(r'^[a-zA-Z\s\-\']+$', name):
            raise ValueError("Name contains invalid characters")
        
        validated["name"] = name
        
        # Validate email
        validated["email"] = cls.validate_email(data["email"])
        
        # Optional phone validation
        if "phone" in data and data["phone"]:
            phone = re.sub(r'[^\d+]', '', str(data["phone"]))
            if not cls._phone_regex.match(phone):
                raise ValueError("Invalid phone number format")
            validated["phone"] = phone
        
        return validated
```

### Logging Security

Secure logging practices:

```python
import logging
import hashlib
from typing import Any, Dict

class SecureLoggingService(BaseService):
    _logger: ClassVar[Optional[logging.Logger]] = None
    _sensitive_fields: ClassVar[Set[str]] = {"password", "api_key", "token", "secret", "credit_card"}
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize secure logging."""
        cls._logger = logging.getLogger("secure_app")
        
        # Configure handler with security in mind
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        cls._logger.addHandler(handler)
        cls._logger.setLevel(logging.INFO)
    
    @classmethod
    @guarded
    def log_user_action(cls, user_id: int, action: str, data: Dict[str, Any] = None) -> None:
        """Log user action with sensitive data filtering."""
        # Filter sensitive data
        safe_data = cls._filter_sensitive_data(data) if data else {}
        
        cls._logger.info(
            f"User {cls._hash_user_id(user_id)} performed action: {action}",
            extra={
                "user_id_hash": cls._hash_user_id(user_id),
                "action": action,
                "data": safe_data
            }
        )
    
    @classmethod
    def _filter_sensitive_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter out sensitive information from logs."""
        filtered = {}
        
        for key, value in data.items():
            if key.lower() in cls._sensitive_fields:
                filtered[key] = "[REDACTED]"
            elif isinstance(value, str) and len(value) > 50:
                # Truncate long strings that might contain sensitive data
                filtered[key] = value[:47] + "..."
            else:
                filtered[key] = value
        
        return filtered
    
    @classmethod
    def _hash_user_id(cls, user_id: int) -> str:
        """Hash user ID for privacy."""
        return hashlib.sha256(str(user_id).encode()).hexdigest()[:8]
```

## 📊 Monitoring and Observability

### Health Check Implementation

Comprehensive health monitoring:

```python
import time
from dataclasses import dataclass
from enum import Enum

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

@dataclass
class ComponentHealth:
    status: HealthStatus
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    last_check: Optional[float] = None

class MonitoringService(BaseService):
    _component_health: ClassVar[Dict[str, ComponentHealth]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        cls._component_health = {}
    
    @classmethod
    @guarded
    def check_system_health(cls) -> Dict[str, Any]:
        """Comprehensive system health check."""
        start_time = time.time()
        
        # Check all components
        components = {
            "database": cls._check_database_health,
            "api_client": cls._check_api_health,
            "cache": cls._check_cache_health,
            "storage": cls._check_storage_health
        }
        
        overall_healthy = True
        component_results = {}
        
        for component_name, check_func in components.items():
            try:
                health = check_func()
                cls._component_health[component_name] = health
                component_results[component_name] = {
                    "status": health.status.value,
                    "response_time_ms": health.response_time_ms,
                    "error": health.error_message
                }
                
                if health.status == HealthStatus.UNHEALTHY:
                    overall_healthy = False
                    
            except Exception as e:
                overall_healthy = False
                error_health = ComponentHealth(
                    status=HealthStatus.UNHEALTHY,
                    error_message=str(e),
                    last_check=time.time()
                )
                cls._component_health[component_name] = error_health
                component_results[component_name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        
        total_time = time.time() - start_time
        
        return {
            "overall_status": "healthy" if overall_healthy else "unhealthy",
            "check_duration_ms": round(total_time * 1000, 2),
            "timestamp": time.time(),
            "components": component_results
        }
    
    @classmethod
    def _check_database_health(cls) -> ComponentHealth:
        """Check database component health."""
        start_time = time.time()
        try:
            # Test database connectivity
            with DatabaseService.get_connection() as conn:
                conn.execute("SELECT 1")
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on response time
            if response_time < 100:
                status = HealthStatus.HEALTHY
            elif response_time < 500:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY
                
            return ComponentHealth(
                status=status,
                response_time_ms=round(response_time, 2),
                last_check=time.time()
            )
            
        except Exception as e:
            return ComponentHealth(
                status=HealthStatus.UNHEALTHY,
                error_message=str(e),
                last_check=time.time()
            )
```

### Metrics Collection

Implement performance metrics:

```python
import time
from collections import defaultdict, deque
from typing import ClassVar, Deque

class MetricsService(BaseService):
    _counters: ClassVar[Dict[str, int]] = {}
    _timers: ClassVar[Dict[str, Deque[float]]] = {}
    _gauges: ClassVar[Dict[str, float]] = {}
    _max_timer_samples: ClassVar[int] = 1000
    
    @classmethod
    def initialize(cls) -> None:
        cls._counters = defaultdict(int)
        cls._timers = defaultdict(lambda: deque(maxlen=cls._max_timer_samples))
        cls._gauges = {}
    
    @classmethod
    @guarded
    def increment_counter(cls, name: str, value: int = 1) -> None:
        """Increment a counter metric."""
        cls._counters[name] += value
    
    @classmethod
    @guarded
    def record_timer(cls, name: str, duration_ms: float) -> None:
        """Record a timing measurement."""
        cls._timers[name].append(duration_ms)
    
    @classmethod
    @guarded
    def set_gauge(cls, name: str, value: float) -> None:
        """Set a gauge metric value."""
        cls._gauges[name] = value
    
    @classmethod
    @guarded
    def get_metrics_summary(cls) -> Dict[str, Any]:
        """Get summary of all metrics."""
        summary = {
            "timestamp": time.time(),
            "counters": dict(cls._counters),
            "gauges": dict(cls._gauges),
            "timers": {}
        }
        
        # Calculate timer statistics
        for name, samples in cls._timers.items():
            if samples:
                sorted_samples = sorted(samples)
                count = len(sorted_samples)
                
                summary["timers"][name] = {
                    "count": count,
                    "min_ms": sorted_samples[0],
                    "max_ms": sorted_samples[-1],
                    "avg_ms": round(sum(sorted_samples) / count, 2),
                    "p50_ms": sorted_samples[count // 2],
                    "p95_ms": sorted_samples[int(count * 0.95)] if count > 20 else sorted_samples[-1],
                    "p99_ms": sorted_samples[int(count * 0.99)] if count > 100 else sorted_samples[-1]
                }
        
        return summary
    
    @classmethod
    @contextmanager
    def time_operation(cls, operation_name: str):
        """Context manager for timing operations."""
        start_time = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            cls.record_timer(operation_name, duration_ms)
```

## 🧪 Testing Best Practices

### Test Service Design

Design services to be testable:

```python
# test_user_service.py
import pytest
from unittest.mock import MagicMock, patch
from user_service import UserService

class TestUserService:
    def setup_method(self):
        """Reset services before each test."""
        UserService._initialized = False
        DatabaseService._initialized = False
        EmailService._initialized = False
    
    def test_create_user_success(self):
        """Test successful user creation."""
        # Mock dependencies
        with patch.object(DatabaseService, 'create_user') as mock_db, \
             patch.object(EmailService, 'send_welcome_email') as mock_email:
            
            mock_db.return_value = 123
            mock_email.return_value = True
            
            # Test the service
            result = UserService.create_user("John Doe", "john@example.com")
            
            # Verify results
            assert result["id"] == 123
            assert result["name"] == "John Doe"
            assert result["email"] == "john@example.com"
            
            # Verify mocks were called correctly
            mock_db.assert_called_once_with("John Doe", "john@example.com")
            mock_email.assert_called_once_with("john@example.com", "John Doe")
    
    def test_create_user_validation_error(self):
        """Test user creation with invalid input."""
        with pytest.raises(ValueError, match="Name and email are required"):
            UserService.create_user("", "")
    
    def test_create_user_database_error(self):
        """Test user creation with database failure."""
        with patch.object(DatabaseService, 'create_user') as mock_db:
            mock_db.side_effect = DatabaseError("Connection failed")
            
            with pytest.raises(RuntimeError, match="database error"):
                UserService.create_user("John Doe", "john@example.com")
```

## ✅ Summary

Following these best practices will help you build:

- **Maintainable services** - Clear boundaries and responsibilities
- **Performant applications** - Optimized resource usage and caching
- **Secure systems** - Proper secret management and input validation
- **Observable applications** - Comprehensive monitoring and metrics
- **Testable code** - Services designed for easy testing

### Key Guidelines

1. **Design for single responsibility** - Each service has one clear purpose
2. **Manage resources properly** - Connection pooling, cleanup, lazy loading
3. **Secure by design** - Never expose secrets, validate all inputs
4. **Monitor everything** - Health checks, metrics, structured logging
5. **Test thoroughly** - Unit tests, integration tests, error scenarios

These patterns will help you build production-ready applications that are reliable, secure, and maintainable.

---

**Concepts Complete!** Continue with practical examples → [Examples](../examples/)