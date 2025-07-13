# Quick Start

Get up and running with **singleton-service** in just 5 minutes! This guide will show you the core concepts through a practical example.

## Installation

First, install singleton-service:

```bash
pip install singleton-service
```

## Your First Service

Let's build a simple weather service that caches API responses:

### Step 1: Create a Basic Service

```python
# weather.py
from singleton_service import BaseService, guarded
from typing import ClassVar, Optional
import requests
import time

class WeatherService(BaseService):
    _api_key: ClassVar[Optional[str]] = None
    _cache: ClassVar[dict] = {}
    _cache_ttl: ClassVar[int] = 300  # 5 minutes
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize the weather service with API configuration."""
        cls._api_key = "your-api-key-here"  # In real apps, use env vars
        cls._cache = {}
        print("🌤️  Weather service initialized")
    
    @classmethod
    def ping(cls) -> bool:
        """Check if the service is properly configured."""
        return cls._api_key is not None
    
    @classmethod
    @guarded
    def get_weather(cls, city: str) -> dict:
        """Get weather for a city with caching."""
        # Check cache first
        cache_key = f"weather:{city}"
        if cache_key in cls._cache:
            cached_data, timestamp = cls._cache[cache_key]
            if time.time() - timestamp < cls._cache_ttl:
                print(f"☁️  Returning cached weather for {city}")
                return cached_data
        
        # Fetch from API (simulated)
        print(f"🌐 Fetching weather for {city} from API")
        weather_data = {
            "city": city,
            "temperature": 22,
            "condition": "sunny",
            "timestamp": time.time()
        }
        
        # Cache the result
        cls._cache[cache_key] = (weather_data, time.time())
        return weather_data
```

### Step 2: Use Your Service

```python
# app.py
from weather import WeatherService

def main():
    # Just use the service - no setup required!
    weather = WeatherService.get_weather("London")
    print(f"Weather in {weather['city']}: {weather['temperature']}°C, {weather['condition']}")
    
    # Call again - this time it will use cache
    weather = WeatherService.get_weather("London")
    print(f"Weather in {weather['city']}: {weather['temperature']}°C, {weather['condition']}")

if __name__ == "__main__":
    main()
```

Run it:

```bash
python app.py
```

Output:
```
🌤️  Weather service initialized
🌐 Fetching weather for London from API
Weather in London: 22°C, sunny
☁️  Returning cached weather for London
Weather in London: 22°C, sunny
```

!!! note "What happened here?"
    1. First call to `get_weather()` triggered initialization automatically
    2. The `@guarded` decorator ensured the service was ready before running
    3. Second call used the cached data
    4. No manual setup or dependency management required!

## Adding Dependencies

Now let's add a database service and make the weather service depend on it:

### Step 3: Create a Database Service

```python
# database.py
from singleton_service import BaseService, guarded
from typing import ClassVar, Optional, Dict, Any

class DatabaseService(BaseService):
    _connection: ClassVar[Optional[dict]] = None
    _data: ClassVar[Dict[str, Any]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize database connection."""
        # Simulate database connection
        cls._connection = {"host": "localhost", "connected": True}
        cls._data = {}
        print("💾 Database service initialized")
    
    @classmethod
    def ping(cls) -> bool:
        """Check database connection."""
        return cls._connection is not None and cls._connection["connected"]
    
    @classmethod
    @guarded
    def save(cls, key: str, value: Any) -> None:
        """Save data to database."""
        cls._data[key] = value
        print(f"💾 Saved {key} to database")
    
    @classmethod  
    @guarded
    def load(cls, key: str) -> Optional[Any]:
        """Load data from database."""
        value = cls._data.get(key)
        if value:
            print(f"💾 Loaded {key} from database")
        return value
```

### Step 4: Add Dependency

Update the weather service to depend on the database:

```python
# weather.py
from singleton_service import BaseService, requires, guarded
from database import DatabaseService  # Import the dependency
from typing import ClassVar, Optional
import time

@requires(DatabaseService)  # ← Declare dependency
class WeatherService(BaseService):
    _api_key: ClassVar[Optional[str]] = None
    _cache_ttl: ClassVar[int] = 300
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize the weather service."""
        cls._api_key = "your-api-key-here"
        print("🌤️  Weather service initialized")
    
    @classmethod
    def ping(cls) -> bool:
        """Check if the service is properly configured."""
        return cls._api_key is not None
    
    @classmethod
    @guarded
    def get_weather(cls, city: str) -> dict:
        """Get weather for a city with database caching."""
        # Check database cache first
        cache_key = f"weather:{city}"
        cached_data = DatabaseService.load(cache_key)
        
        if cached_data and time.time() - cached_data["cached_at"] < cls._cache_ttl:
            print(f"☁️  Returning cached weather for {city}")
            return cached_data["data"]
        
        # Fetch from API (simulated)
        print(f"🌐 Fetching weather for {city} from API")
        weather_data = {
            "city": city,
            "temperature": 22,
            "condition": "sunny",
            "timestamp": time.time()
        }
        
        # Save to database with cache info
        cache_entry = {
            "data": weather_data,
            "cached_at": time.time()
        }
        DatabaseService.save(cache_key, cache_entry)
        
        return weather_data
```

### Step 5: Test Dependencies

```python
# app.py
from weather import WeatherService

def main():
    # The framework will initialize DatabaseService first, then WeatherService
    weather = WeatherService.get_weather("London")
    print(f"Weather in {weather['city']}: {weather['temperature']}°C, {weather['condition']}")
    
    # Second call uses database cache
    weather = WeatherService.get_weather("London")
    print(f"Weather in {weather['city']}: {weather['temperature']}°C, {weather['condition']}")

if __name__ == "__main__":
    main()
```

Run it:

```bash
python app.py
```

Output:
```
💾 Database service initialized
🌤️  Weather service initialized
🌐 Fetching weather for London from API
💾 Saved weather:London to database
Weather in London: 22°C, sunny
💾 Loaded weather:London from database
☁️  Returning cached weather for London
Weather in London: 22°C, sunny
```

!!! success "Dependencies Just Work!"
    Notice how `DatabaseService` was automatically initialized before `WeatherService`, even though we never explicitly initialized it!

## Key Concepts Summary

You've just learned the core concepts of singleton-service:

### 🏗️ **Services are Classes**
- Inherit from `BaseService`
- All state in class variables
- All methods are `@classmethod`
- No instances - just use the class directly

### 🔄 **Automatic Initialization**
- Override `initialize()` to set up resources
- Override `ping()` for health checks  
- Services initialize lazily on first use

### 🔗 **Dependency Management**
- Use `@requires(ServiceA, ServiceB)` to declare dependencies
- Dependencies initialize in the correct order automatically
- No circular dependencies allowed

### 🛡️ **Safety Guarantees**
- `@guarded` methods ensure initialization before execution
- Type-safe with full IDE support
- Clear error messages for common mistakes

## Error Handling

singleton-service provides clear errors for common issues:

```python
# This would raise CircularDependencyError
@requires(WeatherService)
class DatabaseService(BaseService):  # Creates a cycle!
    pass

# This would raise SelfDependencyError  
class BadService(BaseService):
    @classmethod
    def initialize(cls):
        cls.some_method()  # Can't call @guarded methods from initialize!
    
    @classmethod
    @guarded
    def some_method(cls):
        pass
```

## Next Steps

🎉 **Congratulations!** You now understand the fundamentals of singleton-service.

### Continue Learning

- **[Tutorial](tutorial/)** - Deep dive with step-by-step examples
- **[Examples](examples/)** - Real-world patterns and use cases  
- **[Concepts](concepts/)** - Understanding the design principles
- **[API Reference](api/)** - Complete API documentation

### Common Patterns

- **[Database Services](examples/database-service.md)** - Connection pooling and transactions
- **[Background Workers](examples/background-worker.md)** - Job processing and queues
- **[Web Servers](examples/web-server.md)** - FastAPI integration
- **[CLI Apps](examples/cli-app.md)** - Click integration

### Best Practices

- Use environment variables for configuration in `initialize()`
- Keep `ping()` methods fast and lightweight
- Store all state in class variables with type hints
- Always use `@guarded` for business logic methods
- Handle errors gracefully in `initialize()` and `ping()`

Ready to build something awesome? Start with the [Tutorial](tutorial/) for a deeper understanding!