# Error Handling

**singleton-service** provides a comprehensive error handling system designed to give clear, actionable feedback when things go wrong. This section covers the framework's error philosophy, exception hierarchy, and patterns for building resilient applications.

## 🎯 Error Handling Philosophy

### Clear and Actionable Errors

**singleton-service** follows these principles for error handling:

1. **Fail Fast** - Detect errors as early as possible
2. **Clear Messages** - Explain what went wrong and why
3. **Actionable Guidance** - Suggest how to fix the problem
4. **Contextual Information** - Include relevant details for debugging
5. **Consistent Patterns** - Similar errors have similar handling

### Error Categories

The framework organizes errors into logical categories:

```python
ServiceError                    # Base class for all framework errors
├── ServiceInitializationError  # Service failed to start
├── CircularDependencyError     # Impossible dependency cycle
├── SelfDependencyError         # Service calls itself during init
├── DependencyNotInitializedError  # Dependency not ready
└── ServiceNotInitializedError  # Service not ready
```

## 🔧 Exception Hierarchy

### ServiceError (Base Class)

All framework exceptions inherit from `ServiceError`:

```python
from singleton_service.exceptions import ServiceError

try:
    UserService.get_user(123)
except ServiceError as e:
    # Catches any framework-related error
    print(f"Service framework error: {e}")
    print(f"Error type: {type(e).__name__}")
```

**Why a common base class?**
- Easy to catch all framework errors
- Distinguishes framework errors from application errors
- Enables consistent error handling patterns

### ServiceInitializationError

Raised when a service fails to initialize properly:

```python
class DatabaseService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        try:
            cls._connection = connect_to_database()
        except ConnectionError as e:
            # Framework wraps this in ServiceInitializationError
            raise RuntimeError(f"Cannot connect to database: {e}")
    
    @classmethod
    def ping(cls) -> bool:
        # If this returns False, ServiceInitializationError is raised
        return cls._connection and cls._connection.is_alive()

# Usage
try:
    result = DatabaseService.query("SELECT 1")
except ServiceInitializationError as e:
    print(f"Database failed to start: {e}")
    # Error message includes service name and root cause
```

**Common causes:**
- `initialize()` method raises an exception
- `ping()` method returns `False`
- `ping()` method raises an exception
- External dependencies unavailable (database, API, etc.)

### CircularDependencyError

Raised when services have circular dependencies:

```python
# This creates a circular dependency
@requires(ServiceB)
class ServiceA(BaseService):
    pass

@requires(ServiceA)  # ❌ Creates cycle: A → B → A
class ServiceB(BaseService):
    pass

try:
    ServiceA.some_method()
except CircularDependencyError as e:
    print(f"Circular dependency detected: {e}")
    # Error message shows which services are involved in the cycle
```

**How to fix:**
- Remove one of the dependencies
- Introduce a third service that both can depend on
- Refactor to eliminate the circular relationship

### SelfDependencyError

Raised when a service calls its own `@guarded` methods from `initialize()`:

```python
class BadService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        # ❌ This creates a self-dependency!
        cls.load_initial_data()
    
    @classmethod
    @guarded
    def load_initial_data(cls) -> None:
        cls._data = load_data()

try:
    BadService.some_method()
except SelfDependencyError as e:
    print(f"Self-dependency detected: {e}")
    # Error shows which method was called from initialize()
```

**How to fix:**
- Move the logic directly into `initialize()`
- Create a private helper method without `@guarded`
- Restructure initialization to avoid self-calls

## 🚨 Error Handling Patterns

### Defensive Programming

Write services that handle errors gracefully:

```python
class RobustAPIService(BaseService):
    _client: ClassVar[Optional[APIClient]] = None
    _fallback_data: ClassVar[Dict[str, Any]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize with fallback data in case of API issues."""
        api_key = os.getenv("API_KEY")
        if not api_key:
            raise ValueError("API_KEY environment variable is required")
        
        try:
            cls._client = APIClient(api_key, timeout=30)
            # Test connection during initialization
            cls._client.test_connection()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize API client: {e}")
        
        # Load fallback data for when API is unavailable
        cls._fallback_data = {
            "default_user": {"id": 0, "name": "Unknown User"},
            "error_message": "Service temporarily unavailable"
        }
    
    @classmethod
    def ping(cls) -> bool:
        """Test API connectivity."""
        try:
            return cls._client.test_connection().success
        except Exception:
            return False
    
    @classmethod
    @guarded
    def get_user_data(cls, user_id: int) -> Dict[str, Any]:
        """Get user data with fallback handling."""
        try:
            # Try primary API
            response = cls._client.get_user(user_id)
            if response.success:
                return response.data
            else:
                raise APIError(f"API returned error: {response.error}")
                
        except APITimeoutError:
            # API timeout - use fallback
            logging.warning(f"API timeout for user {user_id}, using fallback")
            return cls._fallback_data["default_user"]
            
        except APIConnectionError:
            # API down - use fallback  
            logging.error(f"API connection failed for user {user_id}")
            return cls._fallback_data["default_user"]
            
        except APIError as e:
            # API error - re-raise as user error
            raise ValueError(f"User data unavailable: {e}")
            
        except Exception as e:
            # Unexpected error - log and use fallback
            logging.exception(f"Unexpected error getting user {user_id}: {e}")
            return cls._fallback_data["default_user"]
```

### Error Propagation

Design services to propagate errors appropriately:

```python
@requires(DatabaseService, APIService)
class UserService(BaseService):
    @classmethod
    @guarded
    def create_user(cls, name: str, email: str) -> Dict[str, Any]:
        """Create user with proper error propagation."""
        
        # Validate input (user error)
        if not name or not email:
            raise ValueError("Name and email are required")
        
        if "@" not in email:
            raise ValueError("Invalid email format")
        
        try:
            # Check if user already exists
            existing = DatabaseService.find_user_by_email(email)
            if existing:
                raise ValueError(f"User with email {email} already exists")
            
            # Create user in database
            user_id = DatabaseService.create_user(name, email)
            
            # Send welcome email via API
            APIService.send_welcome_email(email, name)
            
            return {"id": user_id, "name": name, "email": email}
            
        except ValueError:
            # User errors - propagate as-is
            raise
            
        except DatabaseError as e:
            # Database errors - wrap with context
            raise RuntimeError(f"Failed to create user due to database error: {e}")
            
        except APIError as e:
            # API errors - user was created but email failed
            logging.warning(f"User {user_id} created but welcome email failed: {e}")
            # Return success but note the email issue
            return {
                "id": user_id, 
                "name": name, 
                "email": email,
                "warning": "User created but welcome email could not be sent"
            }
            
        except Exception as e:
            # Unexpected errors - provide generic error
            logging.exception(f"Unexpected error creating user {email}: {e}")
            raise RuntimeError("User creation failed due to an internal error")
```

### Circuit Breaker Pattern

Implement circuit breakers to prevent cascading failures:

```python
import time
from enum import Enum
from typing import ClassVar

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreakerService(BaseService):
    _circuit_state: ClassVar[CircuitState] = CircuitState.CLOSED
    _failure_count: ClassVar[int] = 0
    _last_failure_time: ClassVar[float] = 0
    _failure_threshold: ClassVar[int] = 5
    _recovery_timeout: ClassVar[int] = 60  # seconds
    _success_threshold: ClassVar[int] = 3  # successes needed to close circuit
    _consecutive_successes: ClassVar[int] = 0
    
    @classmethod
    def initialize(cls) -> None:
        cls._circuit_state = CircuitState.CLOSED
        cls._failure_count = 0
        cls._consecutive_successes = 0
    
    @classmethod
    @guarded
    def call_external_service(cls, request: str) -> str:
        """Call external service with circuit breaker protection."""
        
        # Check if we should try to recover
        if cls._circuit_state == CircuitState.OPEN:
            if time.time() - cls._last_failure_time > cls._recovery_timeout:
                cls._circuit_state = CircuitState.HALF_OPEN
                cls._consecutive_successes = 0
                logging.info("Circuit breaker entering half-open state")
            else:
                raise RuntimeError("Circuit breaker is open - service unavailable")
        
        try:
            # Attempt the external call
            result = cls._make_external_call(request)
            
            # Success - handle circuit state
            cls._consecutive_successes += 1
            
            if cls._circuit_state == CircuitState.HALF_OPEN:
                if cls._consecutive_successes >= cls._success_threshold:
                    cls._circuit_state = CircuitState.CLOSED
                    cls._failure_count = 0
                    logging.info("Circuit breaker closed - service recovered")
            
            return result
            
        except Exception as e:
            # Failure - update circuit state
            cls._failure_count += 1
            cls._last_failure_time = time.time()
            cls._consecutive_successes = 0
            
            if (cls._circuit_state == CircuitState.CLOSED and 
                cls._failure_count >= cls._failure_threshold):
                cls._circuit_state = CircuitState.OPEN
                logging.error(f"Circuit breaker opened after {cls._failure_count} failures")
            elif cls._circuit_state == CircuitState.HALF_OPEN:
                cls._circuit_state = CircuitState.OPEN
                logging.warning("Circuit breaker re-opened during recovery attempt")
            
            raise RuntimeError(f"External service call failed: {e}")
    
    @classmethod
    def _make_external_call(cls, request: str) -> str:
        """Simulate external service call that might fail."""
        import random
        if random.random() < 0.3:  # 30% failure rate
            raise ConnectionError("External service unavailable")
        return f"Response for: {request}"
    
    @classmethod
    @guarded
    def get_circuit_status(cls) -> Dict[str, Any]:
        """Get current circuit breaker status."""
        return {
            "state": cls._circuit_state.value,
            "failure_count": cls._failure_count,
            "consecutive_successes": cls._consecutive_successes,
            "last_failure_time": cls._last_failure_time
        }
```

### Retry Logic

Implement retry patterns for transient failures:

```python
import random
import time
from typing import Callable, TypeVar

T = TypeVar('T')

class RetryableService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        cls._api_client = create_api_client()
    
    @classmethod
    @guarded
    def fetch_data_with_retry(cls, data_id: str) -> Dict[str, Any]:
        """Fetch data with exponential backoff retry."""
        return cls._retry_with_backoff(
            lambda: cls._api_client.get_data(data_id),
            max_retries=3,
            base_delay=1.0,
            max_delay=10.0,
            backoff_factor=2.0
        )
    
    @classmethod
    def _retry_with_backoff(cls, 
                           func: Callable[[], T],
                           max_retries: int = 3,
                           base_delay: float = 1.0,
                           max_delay: float = 60.0,
                           backoff_factor: float = 2.0) -> T:
        """Retry function with exponential backoff."""
        
        last_exception = None
        delay = base_delay
        
        for attempt in range(max_retries + 1):
            try:
                return func()
                
            except (ConnectionError, TimeoutError) as e:
                # Retryable errors
                last_exception = e
                
                if attempt == max_retries:
                    logging.error(f"Final retry attempt failed: {e}")
                    break
                
                # Add jitter to prevent thundering herd
                jittered_delay = delay * (0.5 + random.random() * 0.5)
                
                logging.warning(
                    f"Attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {jittered_delay:.2f}s"
                )
                
                time.sleep(jittered_delay)
                delay = min(delay * backoff_factor, max_delay)
                
            except Exception as e:
                # Non-retryable errors
                logging.error(f"Non-retryable error: {e}")
                raise
        
        # All retries exhausted
        raise RuntimeError(f"Operation failed after {max_retries + 1} attempts. Last error: {last_exception}")
```

## 📊 Error Monitoring and Observability

### Error Logging

Implement comprehensive error logging:

```python
import logging
import traceback
from typing import ClassVar

class MonitoredService(BaseService):
    _error_counts: ClassVar[Dict[str, int]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        cls._error_counts = {}
        
        # Set up structured logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    @classmethod
    @guarded
    def risky_operation(cls, data: str) -> str:
        """Operation with comprehensive error monitoring."""
        operation_id = f"risky_op_{int(time.time())}"
        
        try:
            logging.info(f"Starting operation {operation_id} with data: {data[:50]}...")
            
            # Simulate risky operation
            result = cls._perform_risky_operation(data)
            
            logging.info(f"Operation {operation_id} completed successfully")
            return result
            
        except ValueError as e:
            # User input error
            error_type = "user_error"
            cls._track_error(error_type)
            
            logging.warning(f"User error in operation {operation_id}: {e}")
            raise
            
        except ExternalServiceError as e:
            # External service error
            error_type = "external_service_error"
            cls._track_error(error_type)
            
            logging.error(
                f"External service error in operation {operation_id}: {e}",
                extra={
                    "operation_id": operation_id,
                    "error_type": error_type,
                    "service": e.service_name
                }
            )
            raise RuntimeError(f"External service unavailable: {e}")
            
        except Exception as e:
            # Unexpected error
            error_type = "unexpected_error"
            cls._track_error(error_type)
            
            logging.exception(
                f"Unexpected error in operation {operation_id}: {e}",
                extra={
                    "operation_id": operation_id,
                    "error_type": error_type,
                    "traceback": traceback.format_exc()
                }
            )
            raise RuntimeError("Operation failed due to an internal error")
    
    @classmethod
    def _track_error(cls, error_type: str) -> None:
        """Track error counts for monitoring."""
        cls._error_counts[error_type] = cls._error_counts.get(error_type, 0) + 1
    
    @classmethod
    @guarded
    def get_error_stats(cls) -> Dict[str, int]:
        """Get error statistics for monitoring."""
        return cls._error_counts.copy()
```

### Health Checks with Error Details

Implement detailed health checks:

```python
class DetailedHealthService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        cls._components = {
            "database": None,
            "api_client": None,
            "cache": None
        }
    
    @classmethod
    def ping(cls) -> bool:
        """Basic health check for framework."""
        return cls._detailed_health_check()["overall_healthy"]
    
    @classmethod
    @guarded
    def detailed_health_check(cls) -> Dict[str, Any]:
        """Detailed health check with component status."""
        return cls._detailed_health_check()
    
    @classmethod
    def _detailed_health_check(cls) -> Dict[str, Any]:
        """Perform detailed health check of all components."""
        health_status = {
            "overall_healthy": True,
            "timestamp": time.time(),
            "components": {}
        }
        
        # Check database
        try:
            if cls._components["database"]:
                cls._components["database"].execute("SELECT 1")
                health_status["components"]["database"] = {
                    "status": "healthy",
                    "response_time_ms": 5
                }
            else:
                health_status["components"]["database"] = {
                    "status": "not_initialized"
                }
        except Exception as e:
            health_status["overall_healthy"] = False
            health_status["components"]["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Check API client
        try:
            if cls._components["api_client"]:
                response = cls._components["api_client"].ping()
                health_status["components"]["api_client"] = {
                    "status": "healthy" if response.ok else "degraded",
                    "response_time_ms": response.response_time
                }
            else:
                health_status["components"]["api_client"] = {
                    "status": "not_initialized"
                }
        except Exception as e:
            health_status["overall_healthy"] = False
            health_status["components"]["api_client"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        return health_status
```

## ✅ Summary

**singleton-service** provides comprehensive error handling through:

- **Clear exception hierarchy** - Organized by error type and cause
- **Actionable error messages** - Include context and suggestions
- **Error propagation** - Framework handles dependency failures gracefully
- **Defensive patterns** - Circuit breakers, retries, fallbacks
- **Monitoring support** - Detailed logging and health checks

### Best Practices

1. **Use appropriate exception types** - Let users understand what failed
2. **Provide clear error messages** - Include context and next steps
3. **Implement fallback strategies** - Keep applications functional during failures
4. **Monitor error patterns** - Track and analyze failure modes
5. **Test error scenarios** - Verify error handling works correctly

The framework's error handling helps you build resilient applications that fail gracefully and provide clear feedback when things go wrong.

---

**Next**: Learn production-ready patterns → [Best Practices](best-practices.md)