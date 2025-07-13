# Health Checks

🎯 **Learning Goals**: Implement robust health verification to ensure services are not just initialized, but actually working correctly.

Initialization success doesn't guarantee your service is working properly. In this tutorial, you'll learn how to implement comprehensive health checks that verify your services are actually functional and ready to handle requests.

## 📚 Understanding Health Checks

### What Are Health Checks?

A **health check** verifies that a service is not only initialized, but actually working correctly:

- ✅ **Database service**: Connection is alive and can execute queries
- ✅ **API service**: Can reach the external API and authenticate
- ✅ **Cache service**: Can read and write data
- ✅ **File service**: Required directories exist and are writable

### When Health Checks Run

Health checks happen automatically:

1. **After initialization**: Called immediately after `initialize()` completes
2. **Before first use**: Framework verifies service is healthy before allowing access
3. **Optionally on-demand**: You can call `ping()` manually for monitoring

### Health Check Lifecycle

```python
class MyService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        # 1. Set up resources
        cls._connection = create_connection()
    
    @classmethod
    def ping(cls) -> bool:
        # 2. Called automatically after initialize()
        # 3. Should verify the service actually works
        return cls._connection.is_alive()
    
    @classmethod
    @guarded
    def do_work(cls):
        # 4. Only called if ping() returned True
        pass
```

## 💻 Implementing Effective Health Checks

### Step 1: Basic Health Checks

Let's start with simple but effective health checks:

```python
# database_service.py
import sqlite3
import os
from typing import ClassVar, Optional
from singleton_service import BaseService, guarded

class DatabaseService(BaseService):
    """Database service with comprehensive health checks."""
    
    _connection: ClassVar[Optional[sqlite3.Connection]] = None
    _db_path: ClassVar[str] = "app.db"
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize database connection."""
        try:
            cls._connection = sqlite3.connect(cls._db_path)
            cls._connection.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)")
            cls._connection.commit()
            print("🗄️  Database service initialized")
        except Exception as e:
            # Let framework wrap this in ServiceInitializationError
            raise RuntimeError(f"Failed to initialize database: {e}")
    
    @classmethod
    def ping(cls) -> bool:
        """Comprehensive database health check."""
        if cls._connection is None:
            return False
        
        try:
            # Test basic connectivity
            cursor = cls._connection.execute("SELECT 1")
            result = cursor.fetchone()
            
            # Verify we got expected result
            if result != (1,):
                return False
            
            # Test write capability  
            cls._connection.execute("SELECT COUNT(*) FROM users")
            
            return True
            
        except Exception as e:
            print(f"🚨 Database health check failed: {e}")
            return False
    
    @classmethod
    @guarded
    def create_user(cls, name: str) -> int:
        """Create a user and return their ID."""
        cursor = cls._connection.execute("INSERT INTO users (name) VALUES (?)", (name,))
        cls._connection.commit()
        return cursor.lastrowid
    
    @classmethod
    @guarded
    def get_user(cls, user_id: int) -> Optional[tuple]:
        """Get user by ID."""
        cursor = cls._connection.execute("SELECT id, name FROM users WHERE id = ?", (user_id,))
        return cursor.fetchone()
```

### Step 2: External Service Health Checks

For services that depend on external systems:

```python
# api_client_service.py
import requests
from typing import ClassVar, Optional
from singleton_service import BaseService, guarded

class WeatherAPIService(BaseService):
    """Weather API client with health verification."""
    
    _api_key: ClassVar[Optional[str]] = None
    _base_url: ClassVar[str] = "https://api.openweathermap.org/data/2.5"
    _timeout: ClassVar[int] = 5
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize API client configuration."""
        cls._api_key = os.getenv("WEATHER_API_KEY")
        if not cls._api_key:
            raise ValueError("WEATHER_API_KEY environment variable is required")
        
        print("🌤️  Weather API service initialized")
    
    @classmethod
    def ping(cls) -> bool:
        """Test API connectivity and authentication."""
        if not cls._api_key:
            return False
        
        try:
            # Test with a simple API call
            response = requests.get(
                f"{cls._base_url}/weather",
                params={
                    "q": "London",  # Test city
                    "appid": cls._api_key,
                    "units": "metric"
                },
                timeout=cls._timeout
            )
            
            # Check if request was successful
            if response.status_code != 200:
                print(f"🚨 Weather API returned status {response.status_code}")
                return False
            
            # Verify response structure
            data = response.json()
            required_fields = ["main", "weather", "name"]
            for field in required_fields:
                if field not in data:
                    print(f"🚨 Weather API response missing field: {field}")
                    return False
            
            print("✅ Weather API health check passed")
            return True
            
        except requests.exceptions.Timeout:
            print("🚨 Weather API health check timed out")
            return False
        except requests.exceptions.ConnectionError:
            print("🚨 Weather API connection failed")
            return False
        except Exception as e:
            print(f"🚨 Weather API health check failed: {e}")
            return False
    
    @classmethod
    @guarded
    def get_weather(cls, city: str) -> dict:
        """Get weather data for a city."""
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
        return response.json()
```

### Step 3: File System Health Checks

For services that work with files and directories:

```python
# file_service.py
import os
import tempfile
from pathlib import Path
from typing import ClassVar
from singleton_service import BaseService, guarded

class FileStorageService(BaseService):
    """File storage service with directory and permission checks."""
    
    _storage_dir: ClassVar[Path] = None
    _temp_dir: ClassVar[Path] = None
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize storage directories."""
        cls._storage_dir = Path("./storage")
        cls._temp_dir = Path("./temp")
        
        # Create directories if they don't exist
        cls._storage_dir.mkdir(exist_ok=True)
        cls._temp_dir.mkdir(exist_ok=True)
        
        print("📁 File storage service initialized")
    
    @classmethod
    def ping(cls) -> bool:
        """Verify directories exist and are writable."""
        try:
            # Check if directories exist
            if not cls._storage_dir.exists():
                print("🚨 Storage directory does not exist")
                return False
            
            if not cls._temp_dir.exists():
                print("🚨 Temp directory does not exist")
                return False
            
            # Test write permissions by creating temporary files
            test_file_storage = cls._storage_dir / "health_check.tmp"
            test_file_temp = cls._temp_dir / "health_check.tmp"
            
            try:
                # Test storage directory
                test_file_storage.write_text("health check")
                if test_file_storage.read_text() != "health check":
                    print("🚨 Storage directory write/read test failed")
                    return False
                test_file_storage.unlink()  # Clean up
                
                # Test temp directory
                test_file_temp.write_text("health check")
                if test_file_temp.read_text() != "health check":
                    print("🚨 Temp directory write/read test failed")
                    return False
                test_file_temp.unlink()  # Clean up
                
            except PermissionError:
                print("🚨 Insufficient permissions for file operations")
                return False
            
            # Check available disk space (at least 100MB)
            storage_stats = os.statvfs(cls._storage_dir)
            available_bytes = storage_stats.f_bavail * storage_stats.f_frsize
            min_required = 100 * 1024 * 1024  # 100MB
            
            if available_bytes < min_required:
                print(f"🚨 Insufficient disk space: {available_bytes} bytes available, {min_required} required")
                return False
            
            print("✅ File storage health check passed")
            return True
            
        except Exception as e:
            print(f"🚨 File storage health check failed: {e}")
            return False
    
    @classmethod
    @guarded
    def save_file(cls, filename: str, content: str) -> Path:
        """Save content to a file."""
        file_path = cls._storage_dir / filename
        file_path.write_text(content)
        return file_path
    
    @classmethod
    @guarded
    def read_file(cls, filename: str) -> str:
        """Read content from a file."""
        file_path = cls._storage_dir / filename
        return file_path.read_text()
```

### Step 4: Composite Health Checks

For services that aggregate multiple dependencies:

```python
# application_service.py
from singleton_service import BaseService, requires, guarded
from database_service import DatabaseService
from weather_api_service import WeatherAPIService
from file_storage_service import FileStorageService

@requires(DatabaseService, WeatherAPIService, FileStorageService)
class ApplicationService(BaseService):
    """Main application service that coordinates other services."""
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize application-level resources."""
        print("🚀 Application service initialized")
    
    @classmethod
    def ping(cls) -> bool:
        """Comprehensive application health check."""
        print("🔍 Running application health check...")
        
        # All dependencies are guaranteed to be initialized and healthy
        # because of @requires, but we can do additional checks
        
        try:
            # Test database functionality
            test_user_id = DatabaseService.create_user("healthcheck_user")
            user = DatabaseService.get_user(test_user_id)
            if not user or user[1] != "healthcheck_user":
                print("🚨 Database integration test failed")
                return False
            
            # Test weather API functionality  
            weather_data = WeatherAPIService.get_weather("London")
            if "main" not in weather_data:
                print("🚨 Weather API integration test failed")
                return False
            
            # Test file storage functionality
            test_file = FileStorageService.save_file("health_check.txt", "test content")
            content = FileStorageService.read_file("health_check.txt")
            if content != "test content":
                print("🚨 File storage integration test failed")
                return False
            
            print("✅ All application health checks passed")
            return True
            
        except Exception as e:
            print(f"🚨 Application health check failed: {e}")
            return False
    
    @classmethod
    @guarded
    def process_weather_report(cls, city: str) -> dict:
        """Process weather data and store report."""
        # Get weather data
        weather = WeatherAPIService.get_weather(city)
        
        # Create user for this report
        user_id = DatabaseService.create_user(f"weather_user_{city}")
        
        # Save report to file
        report = {
            "city": city,
            "temperature": weather["main"]["temp"],
            "description": weather["weather"][0]["description"],
            "user_id": user_id
        }
        
        report_content = f"Weather Report for {city}:\nTemp: {report['temperature']}°C\nCondition: {report['description']}"
        FileStorageService.save_file(f"weather_report_{city}.txt", report_content)
        
        return report
```

## 🔍 Advanced Health Check Patterns

### Health Check with Retries

```python
class RobustAPIService(BaseService):
    @classmethod
    def ping(cls) -> bool:
        """Health check with retry logic."""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Attempt health check
                response = requests.get(cls._health_endpoint, timeout=5)
                if response.status_code == 200:
                    return True
                    
            except Exception as e:
                if attempt == max_retries - 1:  # Last attempt
                    print(f"🚨 Health check failed after {max_retries} attempts: {e}")
                    return False
                else:
                    print(f"⚠️  Health check attempt {attempt + 1} failed, retrying...")
                    time.sleep(1)  # Wait before retry
        
        return False
```

### Cached Health Checks

```python
import time
from typing import ClassVar, Optional

class CachedHealthService(BaseService):
    _last_health_check: ClassVar[Optional[float]] = None
    _last_health_result: ClassVar[bool] = False
    _health_check_ttl: ClassVar[int] = 30  # 30 seconds
    
    @classmethod
    def ping(cls) -> bool:
        """Health check with caching to avoid expensive operations."""
        now = time.time()
        
        # Use cached result if recent
        if (cls._last_health_check is not None and 
            now - cls._last_health_check < cls._health_check_ttl):
            return cls._last_health_result
        
        # Perform actual health check
        try:
            # Expensive health check operation
            result = cls._perform_expensive_health_check()
            
            # Cache the result
            cls._last_health_check = now
            cls._last_health_result = result
            
            return result
            
        except Exception:
            # Cache failure too, but for shorter time
            cls._last_health_check = now
            cls._last_health_result = False
            return False
    
    @classmethod
    def _perform_expensive_health_check(cls) -> bool:
        """Implement your expensive health check here."""
        # Simulate expensive operation
        time.sleep(2)
        return True
```

### Manual Health Check Monitoring

```python
# health_monitor.py
from typing import Dict, List
from singleton_service import BaseService

def check_all_services_health(services: List[type]) -> Dict[str, bool]:
    """Manually check health of all services."""
    results = {}
    
    for service_class in services:
        try:
            # Only check if service is initialized
            if hasattr(service_class, '_initialized') and service_class._initialized:
                results[service_class.__name__] = service_class.ping()
            else:
                results[service_class.__name__] = None  # Not initialized
        except Exception as e:
            print(f"Error checking {service_class.__name__}: {e}")
            results[service_class.__name__] = False
    
    return results

def print_health_report(services: List[type]):
    """Print a comprehensive health report."""
    results = check_all_services_health(services)
    
    print("🏥 Service Health Report")
    print("=" * 40)
    
    for service_name, health in results.items():
        if health is None:
            status = "⏳ Not Initialized"
        elif health:
            status = "✅ Healthy"
        else:
            status = "❌ Unhealthy"
        
        print(f"{service_name:25} {status}")

# Usage
if __name__ == "__main__":
    services = [
        DatabaseService,
        WeatherAPIService, 
        FileStorageService,
        ApplicationService
    ]
    
    print("Before initialization:")
    print_health_report(services)
    
    # Trigger initialization
    ApplicationService.process_weather_report("London")
    
    print("\nAfter initialization:")
    print_health_report(services)
```

## ⚠️ Common Health Check Mistakes

### ❌ Expensive Health Checks

```python
class BadService(BaseService):
    @classmethod
    def ping(cls) -> bool:
        # ❌ Too expensive - blocks initialization
        cls._full_database_migration()  # Takes 30 seconds!
        return True
```

**Solution**: Keep health checks fast and lightweight:
```python
class GoodService(BaseService):
    @classmethod
    def ping(cls) -> bool:
        # ✅ Quick connectivity test
        return cls._connection.execute("SELECT 1").fetchone() == (1,)
```

### ❌ Health Checks with Side Effects

```python
class BadService(BaseService):
    @classmethod
    def ping(cls) -> bool:
        # ❌ Health check shouldn't modify state
        cls._create_test_user()  # Side effect!
        return True
```

**Solution**: Make health checks read-only:
```python
class GoodService(BaseService):
    @classmethod
    def ping(cls) -> bool:
        # ✅ Read-only check
        return len(cls._get_users()) >= 0
```

### ❌ No Error Handling

```python
class BadService(BaseService):
    @classmethod
    def ping(cls) -> bool:
        # ❌ Unhandled exception fails initialization
        return cls._connection.is_alive()  # Might raise exception
```

**Solution**: Handle all possible errors:
```python
class GoodService(BaseService):
    @classmethod
    def ping(cls) -> bool:
        try:
            return cls._connection.is_alive()
        except Exception:
            return False  # ✅ Health check failed gracefully
```

## ✅ Summary

You've mastered service health checks! Here's what you learned:

- ✅ **Health check purpose** - Verify services actually work, not just initialize
- ✅ **When they run** - Automatically after initialization, before first use
- ✅ **Implementation patterns** - Database, API, file system, and composite checks
- ✅ **Advanced patterns** - Retries, caching, and monitoring
- ✅ **Best practices** - Fast, side-effect-free, with proper error handling

### Key Takeaways

1. **Health checks verify functionality** - Not just initialization success
2. **Keep them fast** - Avoid expensive operations that block startup
3. **Handle all errors** - Return False or raise exceptions for failed checks
4. **No side effects** - Health checks should be read-only operations
5. **Test real functionality** - Verify actual service capabilities, not just configuration

## 🚀 Next Steps

Ready to handle failures gracefully when things go wrong?

**[Error Handling →](error-handling.md)**

In the next tutorial, you'll learn comprehensive error handling strategies for when services fail to initialize or encounter runtime issues.

---

**Tutorial Progress**: 4/6 complete ✅✅✅✅  
**Previous**: [Initialization Order](initialization-order.md) | **Next**: [Error Handling](error-handling.md)  
**Estimated time**: 15 minutes ⏱️