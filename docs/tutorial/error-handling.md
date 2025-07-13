# Error Handling

🎯 **Learning Goals**: Master comprehensive error handling strategies for initialization failures, runtime issues, and graceful degradation patterns.

Even the best-designed services can fail. In this tutorial, you'll learn how to handle errors gracefully, provide meaningful diagnostics, and implement fallback strategies that keep your application running even when individual services encounter problems.

## 📚 Understanding Service Errors

### Types of Service Errors

**singleton-service** provides specific exceptions for different failure scenarios:

| Exception | When It Occurs | What It Means |
|-----------|---------------|---------------|
| `ServiceInitializationError` | During `initialize()` or `ping()` | Service couldn't start properly |
| `CircularDependencyError` | At dependency resolution | Impossible dependency cycle detected |
| `SelfDependencyError` | During initialization | Service calls its own `@guarded` methods from `initialize()` |
| `ServiceError` | Any framework error | Base class for all service-related errors |

### Error Propagation Chain

When a service fails, the error propagates through the dependency chain:

```python
# If DatabaseService fails to initialize:
DatabaseService.initialize()  # ❌ Raises exception
    ↓
ServiceInitializationError("DatabaseService failed...")
    ↓  
UserService.get_user()  # ❌ Fails because DatabaseService failed
    ↓
ServiceInitializationError("Failed to initialize UserService because of DatabaseService...")
```

## 💻 Implementing Error Handling

### Step 1: Graceful Initialization Errors

Let's start with proper error handling in service initialization:

```python
# database_service.py
import sqlite3
import os
from typing import ClassVar, Optional
from singleton_service import BaseService, guarded
from singleton_service.exceptions import ServiceInitializationError

class DatabaseService(BaseService):
    """Database service with comprehensive error handling."""
    
    _connection: ClassVar[Optional[sqlite3.Connection]] = None
    _db_path: ClassVar[str] = "app.db"
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize database with proper error handling."""
        try:
            # Check if database file is accessible
            db_dir = os.path.dirname(os.path.abspath(cls._db_path))
            if not os.path.exists(db_dir):
                raise FileNotFoundError(f"Database directory does not exist: {db_dir}")
            
            # Test write permissions
            if not os.access(db_dir, os.W_OK):
                raise PermissionError(f"No write permission for database directory: {db_dir}")
            
            # Create connection
            cls._connection = sqlite3.connect(cls._db_path)
            cls._connection.execute("PRAGMA journal_mode=WAL")  # Better concurrency
            
            # Create required tables
            cls._connection.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cls._connection.commit()
            
            print("🗄️  Database service initialized successfully")
            
        except sqlite3.OperationalError as e:
            # Database-specific errors
            raise ServiceInitializationError(
                f"Database operational error: {e}. "
                f"Check if database file is accessible and not corrupted."
            )
        except PermissionError as e:
            # Permission issues
            raise ServiceInitializationError(
                f"Database permission error: {e}. "
                f"Ensure the application has write access to {db_dir}"
            )
        except Exception as e:
            # Catch-all for unexpected errors
            raise ServiceInitializationError(
                f"Unexpected database initialization error: {e}. "
                f"Check database configuration and file system permissions."
            )
    
    @classmethod
    def ping(cls) -> bool:
        """Health check with detailed error logging."""
        if cls._connection is None:
            print("🚨 Database ping failed: No connection")
            return False
        
        try:
            # Test basic connectivity
            cursor = cls._connection.execute("SELECT 1")
            result = cursor.fetchone()
            
            if result != (1,):
                print(f"🚨 Database ping failed: Unexpected result {result}")
                return False
            
            # Test table access
            cls._connection.execute("SELECT COUNT(*) FROM users")
            
            return True
            
        except sqlite3.OperationalError as e:
            print(f"🚨 Database ping failed: {e}")
            return False
        except Exception as e:
            print(f"🚨 Database ping failed with unexpected error: {e}")
            return False
    
    @classmethod
    @guarded
    def create_user(cls, name: str, email: str) -> int:
        """Create user with proper error handling."""
        try:
            cursor = cls._connection.execute(
                "INSERT INTO users (name, email) VALUES (?, ?)",
                (name, email)
            )
            cls._connection.commit()
            return cursor.lastrowid
            
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                raise ValueError(f"User with email '{email}' already exists")
            else:
                raise ValueError(f"Database constraint violation: {e}")
        except sqlite3.OperationalError as e:
            raise RuntimeError(f"Database operation failed: {e}")
```

### Step 2: External Service Error Handling

For services that depend on external systems:

```python
# weather_service.py
import requests
import os
from typing import ClassVar, Optional, Dict, Any
from singleton_service import BaseService, guarded
from singleton_service.exceptions import ServiceInitializationError

class WeatherService(BaseService):
    """Weather service with robust error handling and fallbacks."""
    
    _api_key: ClassVar[Optional[str]] = None
    _base_url: ClassVar[str] = "https://api.openweathermap.org/data/2.5"
    _timeout: ClassVar[int] = 10
    _fallback_data: ClassVar[Dict[str, Any]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize with configuration validation."""
        cls._api_key = os.getenv("WEATHER_API_KEY")
        
        if not cls._api_key:
            raise ServiceInitializationError(
                "WEATHER_API_KEY environment variable is required. "
                "Get your free API key from https://openweathermap.org/api"
            )
        
        if len(cls._api_key) < 10:  # Basic validation
            raise ServiceInitializationError(
                f"WEATHER_API_KEY appears to be invalid (too short: {len(cls._api_key)} characters). "
                "Please check your API key."
            )
        
        # Initialize fallback data for common cities
        cls._fallback_data = {
            "london": {"temp": 15, "description": "Partly cloudy", "humidity": 65},
            "new york": {"temp": 18, "description": "Clear sky", "humidity": 55},
            "tokyo": {"temp": 22, "description": "Light rain", "humidity": 75},
        }
        
        print("🌤️  Weather service initialized")
    
    @classmethod
    def ping(cls) -> bool:
        """Test API connectivity with timeout and retry."""
        if not cls._api_key:
            return False
        
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    f"{cls._base_url}/weather",
                    params={
                        "q": "London",
                        "appid": cls._api_key,
                        "units": "metric"
                    },
                    timeout=cls._timeout
                )
                
                if response.status_code == 200:
                    return True
                elif response.status_code == 401:
                    print("🚨 Weather API authentication failed - check API key")
                    return False
                elif response.status_code == 429:
                    print("🚨 Weather API rate limit exceeded")
                    return False
                else:
                    print(f"🚨 Weather API returned status {response.status_code}")
                    if attempt == max_retries - 1:
                        return False
                    
            except requests.exceptions.Timeout:
                print(f"⚠️  Weather API timeout (attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    return False
            except requests.exceptions.ConnectionError:
                print(f"⚠️  Weather API connection error (attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    return False
            except Exception as e:
                print(f"🚨 Weather API unexpected error: {e}")
                return False
        
        return False
    
    @classmethod
    @guarded
    def get_weather(cls, city: str) -> Dict[str, Any]:
        """Get weather with fallback handling."""
        try:
            return cls._fetch_weather_from_api(city)
        except requests.exceptions.Timeout:
            print(f"⚠️  Weather API timeout for {city}, using fallback data")
            return cls._get_fallback_weather(city)
        except requests.exceptions.ConnectionError:
            print(f"⚠️  Weather API connection error for {city}, using fallback data")
            return cls._get_fallback_weather(city)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise ValueError(f"City '{city}' not found")
            elif e.response.status_code == 401:
                raise RuntimeError("Weather API authentication failed")
            elif e.response.status_code == 429:
                print(f"⚠️  Weather API rate limited for {city}, using fallback data")
                return cls._get_fallback_weather(city)
            else:
                raise RuntimeError(f"Weather API error: {e}")
        except Exception as e:
            print(f"⚠️  Unexpected weather API error for {city}: {e}, using fallback data")
            return cls._get_fallback_weather(city)
    
    @classmethod
    def _fetch_weather_from_api(cls, city: str) -> Dict[str, Any]:
        """Fetch weather data from API with error handling."""
        response = requests.get(
            f"{cls._base_url}/weather",
            params={
                "q": city,
                "appid": cls._api_key,
                "units": "metric"
            },
            timeout=cls._timeout
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Validate response structure
        required_fields = ["main", "weather", "name"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Invalid API response: missing field '{field}'")
        
        return {
            "city": data["name"],
            "temperature": data["main"]["temp"],
            "description": data["weather"][0]["description"],
            "humidity": data["main"]["humidity"],
            "source": "api"
        }
    
    @classmethod
    def _get_fallback_weather(cls, city: str) -> Dict[str, Any]:
        """Get fallback weather data for common cities."""
        city_lower = city.lower()
        
        if city_lower in cls._fallback_data:
            fallback = cls._fallback_data[city_lower].copy()
            fallback.update({
                "city": city,
                "source": "fallback",
                "note": "This is fallback data due to API unavailability"
            })
            return fallback
        else:
            # Generic fallback for unknown cities
            return {
                "city": city,
                "temperature": 20,
                "description": "Unknown (API unavailable)",
                "humidity": 60,
                "source": "fallback",
                "note": "Generic fallback data - actual weather unavailable"
            }
```

### Step 3: Service Error Recovery

Create a service that demonstrates error recovery patterns:

```python
# notification_service.py
from typing import ClassVar, List, Dict, Any
from singleton_service import BaseService, requires, guarded
from database_service import DatabaseService
from weather_service import WeatherService

@requires(DatabaseService, WeatherService)
class NotificationService(BaseService):
    """Notification service with graceful degradation."""
    
    _failed_notifications: ClassVar[List[Dict[str, Any]]] = []
    _retry_count: ClassVar[Dict[str, int]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize notification tracking."""
        cls._failed_notifications = []
        cls._retry_count = {}
        print("📢 Notification service initialized")
    
    @classmethod
    @guarded
    def send_weather_notification(cls, user_email: str, city: str) -> Dict[str, Any]:
        """Send weather notification with error recovery."""
        notification_id = f"{user_email}:{city}"
        result = {
            "notification_id": notification_id,
            "success": False,
            "message": "",
            "weather_data": None,
            "fallback_used": False
        }
        
        try:
            # Try to get weather data
            weather = WeatherService.get_weather(city)
            result["weather_data"] = weather
            
            # Check if we're using fallback data
            if weather.get("source") == "fallback":
                result["fallback_used"] = True
                result["message"] = f"Weather notification sent to {user_email} using fallback data"
            else:
                result["message"] = f"Weather notification sent to {user_email} with live data"
            
            # Simulate sending notification (this could fail)
            cls._simulate_send_notification(user_email, weather)
            
            result["success"] = True
            
            # Clear any previous retry count on success
            if notification_id in cls._retry_count:
                del cls._retry_count[notification_id]
            
            return result
            
        except ValueError as e:
            # User error (like invalid city)
            result["message"] = f"Cannot send notification: {e}"
            return result
            
        except Exception as e:
            # Service error - add to retry queue
            result["message"] = f"Notification failed: {e}"
            cls._handle_notification_failure(notification_id, user_email, city, str(e))
            return result
    
    @classmethod
    def _simulate_send_notification(cls, email: str, weather: Dict[str, Any]) -> None:
        """Simulate sending notification - might fail."""
        import random
        
        # Simulate 20% failure rate
        if random.random() < 0.2:
            raise RuntimeError("Email service temporarily unavailable")
        
        # Simulate successful send
        print(f"📧 Sent weather notification to {email}: "
              f"{weather['city']} is {weather['temperature']}°C, {weather['description']}")
    
    @classmethod
    def _handle_notification_failure(cls, notification_id: str, 
                                   user_email: str, city: str, error: str) -> None:
        """Handle notification failure with retry logic."""
        retry_count = cls._retry_count.get(notification_id, 0) + 1
        cls._retry_count[notification_id] = retry_count
        
        max_retries = 3
        if retry_count <= max_retries:
            # Add to retry queue
            cls._failed_notifications.append({
                "notification_id": notification_id,
                "user_email": user_email,
                "city": city,
                "error": error,
                "retry_count": retry_count,
                "timestamp": "2024-01-15T10:30:00Z"  # In real app, use actual timestamp
            })
            print(f"⚠️  Notification {notification_id} failed (attempt {retry_count}/{max_retries}), added to retry queue")
        else:
            print(f"❌ Notification {notification_id} failed permanently after {max_retries} attempts")
    
    @classmethod
    @guarded
    def retry_failed_notifications(cls) -> Dict[str, Any]:
        """Retry failed notifications."""
        if not cls._failed_notifications:
            return {"retried": 0, "succeeded": 0, "failed": 0}
        
        succeeded = 0
        failed = 0
        remaining_failures = []
        
        for notification in cls._failed_notifications:
            try:
                result = cls.send_weather_notification(
                    notification["user_email"],
                    notification["city"]
                )
                
                if result["success"]:
                    succeeded += 1
                    print(f"✅ Retry succeeded for {notification['notification_id']}")
                else:
                    remaining_failures.append(notification)
                    failed += 1
                    
            except Exception as e:
                remaining_failures.append(notification)
                failed += 1
                print(f"❌ Retry failed for {notification['notification_id']}: {e}")
        
        # Update failed notifications list
        cls._failed_notifications = remaining_failures
        
        return {
            "retried": len(cls._failed_notifications) + succeeded + failed,
            "succeeded": succeeded,
            "failed": failed,
            "remaining": len(remaining_failures)
        }
    
    @classmethod
    @guarded
    def get_notification_status(cls) -> Dict[str, Any]:
        """Get current notification system status."""
        return {
            "failed_notifications": len(cls._failed_notifications),
            "retry_counts": dict(cls._retry_count),
            "service_health": {
                "database": DatabaseService.ping() if hasattr(DatabaseService, '_initialized') and DatabaseService._initialized else None,
                "weather": WeatherService.ping() if hasattr(WeatherService, '_initialized') and WeatherService._initialized else None
            }
        }
```

### Step 4: Application-Level Error Handling

Create a comprehensive error handling example:

```python
# app.py
import traceback
from typing import Dict, Any
from singleton_service.exceptions import (
    ServiceError, ServiceInitializationError, 
    CircularDependencyError, SelfDependencyError
)
from notification_service import NotificationService

def safe_service_call(func, *args, **kwargs) -> Dict[str, Any]:
    """Safely call a service method with comprehensive error handling."""
    try:
        result = func(*args, **kwargs)
        return {
            "success": True,
            "data": result,
            "error": None,
            "error_type": None
        }
        
    except ServiceInitializationError as e:
        return {
            "success": False,
            "data": None,
            "error": str(e),
            "error_type": "initialization",
            "suggestion": "Check service configuration and external dependencies"
        }
        
    except CircularDependencyError as e:
        return {
            "success": False,
            "data": None,
            "error": str(e),
            "error_type": "circular_dependency",
            "suggestion": "Review and restructure service dependencies to remove cycles"
        }
        
    except SelfDependencyError as e:
        return {
            "success": False,
            "data": None,
            "error": str(e),
            "error_type": "self_dependency",
            "suggestion": "Don't call @guarded methods from within initialize()"
        }
        
    except ServiceError as e:
        return {
            "success": False,
            "data": None,
            "error": str(e),
            "error_type": "service",
            "suggestion": "Check service logs for more details"
        }
        
    except ValueError as e:
        return {
            "success": False,
            "data": None,
            "error": str(e),
            "error_type": "validation",
            "suggestion": "Check input parameters"
        }
        
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": f"Unexpected error: {e}",
            "error_type": "unexpected",
            "suggestion": "Check application logs",
            "traceback": traceback.format_exc()
        }

def main():
    """Main application with comprehensive error handling."""
    print("🚀 Starting application with error handling...\n")
    
    # Test normal operation
    print("📧 Testing normal notification...")
    result = safe_service_call(
        NotificationService.send_weather_notification,
        "user@example.com",
        "London"
    )
    
    if result["success"]:
        print(f"✅ Success: {result['data']['message']}")
        if result['data']['fallback_used']:
            print("⚠️  Note: Fallback weather data was used")
    else:
        print(f"❌ Failed: {result['error']} (Type: {result['error_type']})")
        print(f"💡 Suggestion: {result['suggestion']}")
    
    print("\n" + "="*50)
    
    # Test error cases
    print("\n📧 Testing invalid city...")
    result = safe_service_call(
        NotificationService.send_weather_notification,
        "user@example.com", 
        "NonexistentCity123"
    )
    
    if not result["success"]:
        print(f"❌ Expected failure: {result['error']} (Type: {result['error_type']})")
    
    print("\n" + "="*50)
    
    # Test retry functionality
    print("\n🔄 Testing notification retry system...")
    retry_result = safe_service_call(NotificationService.retry_failed_notifications)
    
    if retry_result["success"]:
        print(f"✅ Retry system status: {retry_result['data']}")
    
    # Test status reporting
    print("\n📊 System status:")
    status_result = safe_service_call(NotificationService.get_notification_status)
    
    if status_result["success"]:
        status = status_result["data"]
        print(f"   Failed notifications: {status['failed_notifications']}")
        print(f"   Service health: {status['service_health']}")

if __name__ == "__main__":
    main()
```

## 🔧 Error Recovery Patterns

### Circuit Breaker Pattern

```python
import time
from typing import ClassVar

class CircuitBreakerService(BaseService):
    _failure_count: ClassVar[int] = 0
    _last_failure_time: ClassVar[float] = 0
    _circuit_open: ClassVar[bool] = False
    _failure_threshold: ClassVar[int] = 5
    _recovery_timeout: ClassVar[int] = 60  # seconds
    
    @classmethod
    @guarded
    def call_external_service(cls) -> str:
        """Call external service with circuit breaker protection."""
        current_time = time.time()
        
        # Check if circuit should be reset
        if (cls._circuit_open and 
            current_time - cls._last_failure_time > cls._recovery_timeout):
            cls._circuit_open = False
            cls._failure_count = 0
            print("🔄 Circuit breaker reset - attempting recovery")
        
        # If circuit is open, fail fast
        if cls._circuit_open:
            raise RuntimeError("Circuit breaker is open - service unavailable")
        
        try:
            # Simulate external service call
            result = cls._simulate_external_call()
            
            # Reset failure count on success
            cls._failure_count = 0
            return result
            
        except Exception as e:
            cls._failure_count += 1
            cls._last_failure_time = current_time
            
            # Open circuit if threshold reached
            if cls._failure_count >= cls._failure_threshold:
                cls._circuit_open = True
                print(f"⚠️  Circuit breaker opened after {cls._failure_count} failures")
            
            raise e
    
    @classmethod
    def _simulate_external_call(cls) -> str:
        """Simulate external service call that might fail."""
        import random
        if random.random() < 0.3:  # 30% failure rate
            raise RuntimeError("External service error")
        return "External service response"
```

## ✅ Summary

You've mastered comprehensive error handling! Here's what you learned:

- ✅ **Error types** - Understanding different exception categories and their meanings
- ✅ **Graceful initialization** - Proper error handling during service setup
- ✅ **External service errors** - Handling API failures, timeouts, and authentication issues
- ✅ **Fallback strategies** - Providing alternative functionality when services fail
- ✅ **Error recovery** - Retry logic, circuit breakers, and graceful degradation
- ✅ **Application-level handling** - Comprehensive error catching and user feedback

### Key Takeaways

1. **Fail fast with clear messages** - Provide actionable error information
2. **Use appropriate exception types** - Help users understand what went wrong
3. **Implement fallback strategies** - Keep applications functional during outages
4. **Plan for recovery** - Design retry mechanisms and circuit breakers
5. **Monitor and track failures** - Build visibility into error patterns

## 🚀 Next Steps

Ready to ensure your services work correctly with comprehensive testing?

**[Testing Services →](testing.md)**

In the final tutorial, you'll learn how to write comprehensive tests for your singleton services, including mocking dependencies and testing error scenarios.

---

**Tutorial Progress**: 5/6 complete ✅✅✅✅✅  
**Previous**: [Health Checks](health-checks.md) | **Next**: [Testing Services](testing.md)  
**Estimated time**: 30 minutes ⏱️