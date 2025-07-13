# Weather Service Example

This example demonstrates a complete weather service implementation using **singleton-service**. It showcases HTTP API integration, caching, error handling, and configuration management patterns.

## 🎯 What You'll Learn

- Building HTTP API clients as services
- Implementing caching strategies
- Error handling and fallback patterns
- Configuration management
- Service testing strategies

## 📋 Complete Implementation

### Dependencies

```bash
pip install singleton-service requests python-dotenv
```

### Configuration Service

```python
# services/config.py
import os
from typing import ClassVar, Optional
from dataclasses import dataclass
from singleton_service import BaseService

@dataclass
class WeatherConfig:
    """Type-safe weather service configuration."""
    api_key: str
    base_url: str
    timeout_seconds: int
    cache_ttl_seconds: int
    max_retries: int

class ConfigService(BaseService):
    """Centralized configuration management."""
    
    _config: ClassVar[Optional[WeatherConfig]] = None
    
    @classmethod
    def initialize(cls) -> None:
        """Load and validate configuration from environment."""
        # Required settings
        api_key = os.getenv("WEATHER_API_KEY")
        if not api_key:
            raise ValueError(
                "WEATHER_API_KEY environment variable is required. "
                "Get your free API key from https://openweathermap.org/api"
            )
        
        # Optional settings with defaults
        base_url = os.getenv("WEATHER_API_URL", "https://api.openweathermap.org/data/2.5")
        
        try:
            timeout = int(os.getenv("WEATHER_TIMEOUT", "30"))
            cache_ttl = int(os.getenv("WEATHER_CACHE_TTL", "300"))  # 5 minutes
            max_retries = int(os.getenv("WEATHER_MAX_RETRIES", "3"))
        except ValueError as e:
            raise ValueError(f"Invalid configuration value: {e}")
        
        # Validate ranges
        if timeout < 1 or timeout > 300:
            raise ValueError("WEATHER_TIMEOUT must be between 1 and 300 seconds")
        
        if cache_ttl < 60 or cache_ttl > 3600:
            raise ValueError("WEATHER_CACHE_TTL must be between 60 and 3600 seconds")
        
        cls._config = WeatherConfig(
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout,
            cache_ttl_seconds=cache_ttl,
            max_retries=max_retries
        )
    
    @classmethod
    def ping(cls) -> bool:
        """Verify configuration is loaded."""
        return cls._config is not None
    
    @classmethod
    @guarded
    def get_config(cls) -> WeatherConfig:
        """Get validated configuration."""
        return cls._config
```

### Cache Service

```python
# services/cache.py
import time
from typing import ClassVar, Dict, Tuple, Any, Optional
from singleton_service import BaseService, guarded

class CacheService(BaseService):
    """Simple in-memory cache with TTL support."""
    
    _cache: ClassVar[Dict[str, Tuple[Any, float]]] = {}
    _stats: ClassVar[Dict[str, int]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize cache storage."""
        cls._cache = {}
        cls._stats = {"hits": 0, "misses": 0, "evictions": 0}
    
    @classmethod
    def ping(cls) -> bool:
        """Test cache functionality."""
        test_key = "__health_check__"
        cls._cache[test_key] = ("test", time.time())
        result = test_key in cls._cache
        cls._cache.pop(test_key, None)
        return result
    
    @classmethod
    @guarded
    def get(cls, key: str, ttl_seconds: int = 300) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key not in cls._cache:
            cls._stats["misses"] += 1
            return None
        
        value, timestamp = cls._cache[key]
        
        # Check if expired
        if time.time() - timestamp > ttl_seconds:
            del cls._cache[key]
            cls._stats["evictions"] += 1
            cls._stats["misses"] += 1
            return None
        
        cls._stats["hits"] += 1
        return value
    
    @classmethod
    @guarded
    def set(cls, key: str, value: Any) -> None:
        """Store value in cache with current timestamp."""
        cls._cache[key] = (value, time.time())
    
    @classmethod
    @guarded
    def clear(cls) -> None:
        """Clear all cached data."""
        evicted_count = len(cls._cache)
        cls._cache.clear()
        cls._stats["evictions"] += evicted_count
    
    @classmethod
    @guarded
    def get_stats(cls) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = cls._stats["hits"] + cls._stats["misses"]
        hit_rate = cls._stats["hits"] / max(total_requests, 1) * 100
        
        return {
            **cls._stats,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
            "cache_size": len(cls._cache)
        }
```

### HTTP Client Service

```python
# services/http_client.py
import time
import requests
from typing import ClassVar, Optional, Dict, Any
from singleton_service import BaseService, requires, guarded
from .config import ConfigService

@requires(ConfigService)
class HttpClientService(BaseService):
    """HTTP client with retries and error handling."""
    
    _session: ClassVar[Optional[requests.Session]] = None
    _request_stats: ClassVar[Dict[str, int]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize HTTP session with configuration."""
        config = ConfigService.get_config()
        
        cls._session = requests.Session()
        cls._session.timeout = config.timeout_seconds
        
        # Set default headers
        cls._session.headers.update({
            "User-Agent": "WeatherService/1.0",
            "Accept": "application/json"
        })
        
        cls._request_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "retries": 0
        }
    
    @classmethod
    def ping(cls) -> bool:
        """Test HTTP client connectivity."""
        try:
            # Test with a simple request
            response = cls._session.get("https://httpbin.org/status/200", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    @classmethod
    @guarded
    def get(cls, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make GET request with retries and error handling."""
        config = ConfigService.get_config()
        last_exception = None
        
        for attempt in range(config.max_retries + 1):
            try:
                cls._request_stats["total_requests"] += 1
                
                response = cls._session.get(url, params=params)
                response.raise_for_status()
                
                cls._request_stats["successful_requests"] += 1
                return response.json()
                
            except requests.exceptions.Timeout as e:
                last_exception = e
                if attempt < config.max_retries:
                    cls._request_stats["retries"] += 1
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                    
            except requests.exceptions.ConnectionError as e:
                last_exception = e
                if attempt < config.max_retries:
                    cls._request_stats["retries"] += 1
                    time.sleep(2 ** attempt)
                    continue
                    
            except requests.exceptions.HTTPError as e:
                # Don't retry 4xx errors
                if 400 <= e.response.status_code < 500:
                    cls._request_stats["failed_requests"] += 1
                    raise ValueError(f"Client error: {e.response.status_code} - {e.response.text}")
                
                # Retry 5xx errors
                last_exception = e
                if attempt < config.max_retries:
                    cls._request_stats["retries"] += 1
                    time.sleep(2 ** attempt)
                    continue
                    
            except Exception as e:
                last_exception = e
                break
        
        cls._request_stats["failed_requests"] += 1
        raise RuntimeError(f"HTTP request failed after {config.max_retries + 1} attempts: {last_exception}")
    
    @classmethod
    @guarded
    def get_stats(cls) -> Dict[str, Any]:
        """Get HTTP client statistics."""
        total = cls._request_stats["total_requests"]
        success_rate = cls._request_stats["successful_requests"] / max(total, 1) * 100
        
        return {
            **cls._request_stats,
            "success_rate_percent": round(success_rate, 2)
        }
```

### Weather Service

```python
# services/weather.py
from typing import ClassVar, Dict, Any, Optional
from dataclasses import dataclass
from singleton_service import BaseService, requires, guarded
from .config import ConfigService
from .cache import CacheService
from .http_client import HttpClientService

@dataclass
class WeatherData:
    """Weather information for a location."""
    location: str
    temperature: float
    feels_like: float
    humidity: int
    pressure: int
    description: str
    wind_speed: float
    timestamp: float

@requires(ConfigService, CacheService, HttpClientService)
class WeatherService(BaseService):
    """Weather data service with caching and error handling."""
    
    _fallback_data: ClassVar[Dict[str, WeatherData]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize weather service with fallback data."""
        # Set up fallback data for when API is unavailable
        cls._fallback_data = {
            "london": WeatherData(
                location="London, UK",
                temperature=15.0,
                feels_like=13.0,
                humidity=70,
                pressure=1013,
                description="partly cloudy",
                wind_speed=3.5,
                timestamp=0
            ),
            "new york": WeatherData(
                location="New York, US", 
                temperature=18.0,
                feels_like=16.0,
                humidity=65,
                pressure=1015,
                description="clear sky",
                wind_speed=2.1,
                timestamp=0
            )
        }
    
    @classmethod
    def ping(cls) -> bool:
        """Test weather service connectivity."""
        try:
            # Test with a simple API call
            cls.get_weather("London", use_cache=False)
            return True
        except Exception:
            return False
    
    @classmethod
    @guarded
    def get_weather(cls, location: str, use_cache: bool = True) -> WeatherData:
        """Get weather data for a location with caching."""
        config = ConfigService.get_config()
        cache_key = f"weather:{location.lower()}"
        
        # Try cache first
        if use_cache:
            cached_data = CacheService.get(cache_key, config.cache_ttl_seconds)
            if cached_data:
                return cached_data
        
        try:
            # Make API request
            weather_data = cls._fetch_weather_from_api(location)
            
            # Cache the result
            CacheService.set(cache_key, weather_data)
            
            return weather_data
            
        except Exception as e:
            # Try fallback data
            fallback = cls._fallback_data.get(location.lower())
            if fallback:
                return fallback
            
            # No fallback available
            raise RuntimeError(f"Weather data unavailable for {location}: {e}")
    
    @classmethod
    def _fetch_weather_from_api(cls, location: str) -> WeatherData:
        """Fetch weather data from OpenWeatherMap API."""
        config = ConfigService.get_config()
        
        # Build API request
        url = f"{config.base_url}/weather"
        params = {
            "q": location,
            "appid": config.api_key,
            "units": "metric"
        }
        
        # Make request
        data = HttpClientService.get(url, params)
        
        # Parse response
        return WeatherData(
            location=f"{data['name']}, {data['sys']['country']}",
            temperature=data['main']['temp'],
            feels_like=data['main']['feels_like'],
            humidity=data['main']['humidity'],
            pressure=data['main']['pressure'],
            description=data['weather'][0]['description'],
            wind_speed=data['wind']['speed'],
            timestamp=data['dt']
        )
    
    @classmethod
    @guarded
    def get_forecast(cls, location: str, days: int = 5) -> List[WeatherData]:
        """Get weather forecast for multiple days."""
        config = ConfigService.get_config()
        cache_key = f"forecast:{location.lower()}:{days}"
        
        # Try cache first
        cached_data = CacheService.get(cache_key, config.cache_ttl_seconds)
        if cached_data:
            return cached_data
        
        try:
            # Build API request for forecast
            url = f"{config.base_url}/forecast"
            params = {
                "q": location,
                "appid": config.api_key,
                "units": "metric",
                "cnt": days * 8  # 8 forecasts per day (3-hour intervals)
            }
            
            data = HttpClientService.get(url, params)
            
            # Parse forecast data (simplified - take one per day)
            forecasts = []
            for i in range(0, min(len(data['list']), days * 8), 8):
                item = data['list'][i]
                forecast = WeatherData(
                    location=f"{data['city']['name']}, {data['city']['country']}",
                    temperature=item['main']['temp'],
                    feels_like=item['main']['feels_like'],
                    humidity=item['main']['humidity'],
                    pressure=item['main']['pressure'],
                    description=item['weather'][0]['description'],
                    wind_speed=item['wind']['speed'],
                    timestamp=item['dt']
                )
                forecasts.append(forecast)
            
            # Cache the result
            CacheService.set(cache_key, forecasts)
            
            return forecasts
            
        except Exception as e:
            raise RuntimeError(f"Weather forecast unavailable for {location}: {e}")
    
    @classmethod
    @guarded
    def clear_cache(cls) -> Dict[str, Any]:
        """Clear weather cache and return statistics."""
        stats_before = CacheService.get_stats()
        CacheService.clear()
        stats_after = CacheService.get_stats()
        
        return {
            "cleared_items": stats_before["cache_size"],
            "cache_stats": stats_after
        }
    
    @classmethod
    @guarded
    def get_service_stats(cls) -> Dict[str, Any]:
        """Get comprehensive service statistics."""
        return {
            "cache_stats": CacheService.get_stats(),
            "http_stats": HttpClientService.get_stats(),
            "fallback_locations": list(cls._fallback_data.keys())
        }
```

## 🚀 Usage Examples

### Basic Usage

```python
# main.py
import os
from dotenv import load_dotenv
from services.weather import WeatherService

def main():
    # Load environment variables
    load_dotenv()
    
    # Set your API key
    os.environ["WEATHER_API_KEY"] = "your_api_key_here"
    
    try:
        # Get current weather
        weather = WeatherService.get_weather("London")
        print(f"Weather in {weather.location}:")
        print(f"  Temperature: {weather.temperature}°C (feels like {weather.feels_like}°C)")
        print(f"  Conditions: {weather.description}")
        print(f"  Humidity: {weather.humidity}%")
        print(f"  Wind: {weather.wind_speed} m/s")
        
        # Get forecast
        forecast = WeatherService.get_forecast("London", days=3)
        print(f"\\n3-day forecast for {forecast[0].location}:")
        for day, weather in enumerate(forecast, 1):
            print(f"  Day {day}: {weather.temperature}°C - {weather.description}")
        
        # Show service statistics
        stats = WeatherService.get_service_stats()
        print(f"\\nService Statistics:")
        print(f"  Cache hit rate: {stats['cache_stats']['hit_rate_percent']}%")
        print(f"  HTTP success rate: {stats['http_stats']['success_rate_percent']}%")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
```

### Environment Configuration

```bash
# .env file
WEATHER_API_KEY=your_openweathermap_api_key
WEATHER_API_URL=https://api.openweathermap.org/data/2.5
WEATHER_TIMEOUT=30
WEATHER_CACHE_TTL=300
WEATHER_MAX_RETRIES=3
```

### CLI Application

```python
# cli.py
import click
import os
from dotenv import load_dotenv
from services.weather import WeatherService

@click.group()
def cli():
    """Weather Service CLI Tool"""
    load_dotenv()
    
    if not os.getenv("WEATHER_API_KEY"):
        click.echo("Error: WEATHER_API_KEY environment variable required")
        click.echo("Get your free API key from https://openweathermap.org/api")
        raise click.Abort()

@cli.command()
@click.argument('location')
@click.option('--no-cache', is_flag=True, help='Skip cache and fetch fresh data')
def current(location, no_cache):
    """Get current weather for a location."""
    try:
        weather = WeatherService.get_weather(location, use_cache=not no_cache)
        
        click.echo(f"Weather in {weather.location}:")
        click.echo(f"  🌡️  Temperature: {weather.temperature}°C (feels like {weather.feels_like}°C)")
        click.echo(f"  ☁️  Conditions: {weather.description.title()}")
        click.echo(f"  💧 Humidity: {weather.humidity}%")
        click.echo(f"  📊 Pressure: {weather.pressure} hPa")
        click.echo(f"  💨 Wind: {weather.wind_speed} m/s")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()

@cli.command()
@click.argument('location')
@click.option('--days', default=5, help='Number of days (1-5)')
def forecast(location, days):
    """Get weather forecast for a location."""
    try:
        forecasts = WeatherService.get_forecast(location, days)
        
        click.echo(f"{days}-day forecast for {forecasts[0].location}:")
        for i, weather in enumerate(forecasts, 1):
            click.echo(f"  Day {i}: {weather.temperature}°C - {weather.description.title()}")
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()

@cli.command()
def stats():
    """Show service statistics."""
    try:
        stats = WeatherService.get_service_stats()
        
        click.echo("Cache Statistics:")
        cache_stats = stats['cache_stats']
        click.echo(f"  Hit rate: {cache_stats['hit_rate_percent']}%")
        click.echo(f"  Cache size: {cache_stats['cache_size']} items")
        click.echo(f"  Total requests: {cache_stats['total_requests']}")
        
        click.echo("\\nHTTP Statistics:")
        http_stats = stats['http_stats']
        click.echo(f"  Success rate: {http_stats['success_rate_percent']}%")
        click.echo(f"  Total requests: {http_stats['total_requests']}")
        click.echo(f"  Retries: {http_stats['retries']}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()

@cli.command()
def clear_cache():
    """Clear the weather cache."""
    try:
        result = WeatherService.clear_cache()
        click.echo(f"Cleared {result['cleared_items']} cached items")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()

if __name__ == '__main__':
    cli()
```

## 🧪 Testing

### Unit Tests

```python
# test_weather.py
import pytest
import time
from unittest.mock import MagicMock, patch
from services.weather import WeatherService, WeatherData
from services.config import ConfigService
from services.cache import CacheService
from services.http_client import HttpClientService

class TestWeatherService:
    def setup_method(self):
        """Reset services before each test."""
        for service in [WeatherService, ConfigService, CacheService, HttpClientService]:
            service._initialized = False
    
    def test_get_weather_success(self):
        """Test successful weather retrieval."""
        # Mock configuration
        with patch.object(ConfigService, 'get_config') as mock_config:
            mock_config.return_value = MagicMock(cache_ttl_seconds=300)
            
            # Mock HTTP response
            mock_response = {
                "name": "London",
                "sys": {"country": "UK"},
                "main": {
                    "temp": 20.0,
                    "feels_like": 18.0,
                    "humidity": 65,
                    "pressure": 1013
                },
                "weather": [{"description": "clear sky"}],
                "wind": {"speed": 3.5},
                "dt": int(time.time())
            }
            
            with patch.object(HttpClientService, 'get', return_value=mock_response):
                weather = WeatherService.get_weather("London", use_cache=False)
                
                assert weather.location == "London, UK"
                assert weather.temperature == 20.0
                assert weather.description == "clear sky"
    
    def test_get_weather_with_cache(self):
        """Test weather retrieval with caching."""
        cached_weather = WeatherData(
            location="London, UK",
            temperature=22.0,
            feels_like=20.0,
            humidity=60,
            pressure=1015,
            description="sunny",
            wind_speed=2.0,
            timestamp=time.time()
        )
        
        with patch.object(CacheService, 'get', return_value=cached_weather):
            weather = WeatherService.get_weather("London")
            
            assert weather.temperature == 22.0
            assert weather.description == "sunny"
    
    def test_get_weather_fallback(self):
        """Test fallback when API fails."""
        with patch.object(HttpClientService, 'get', side_effect=Exception("API Error")):
            weather = WeatherService.get_weather("London", use_cache=False)
            
            # Should return fallback data
            assert weather.location == "London, UK"
            assert weather.temperature == 15.0
    
    def test_get_weather_no_fallback_fails(self):
        """Test error when no fallback available."""
        with patch.object(HttpClientService, 'get', side_effect=Exception("API Error")):
            with pytest.raises(RuntimeError, match="Weather data unavailable"):
                WeatherService.get_weather("Unknown City", use_cache=False)

    def test_clear_cache(self):
        """Test cache clearing functionality."""
        with patch.object(CacheService, 'get_stats') as mock_stats:
            mock_stats.side_effect = [
                {"cache_size": 5, "hits": 10, "misses": 2},  # Before
                {"cache_size": 0, "hits": 10, "misses": 2}   # After
            ]
            
            with patch.object(CacheService, 'clear'):
                result = WeatherService.clear_cache()
                
                assert result["cleared_items"] == 5
                assert result["cache_stats"]["cache_size"] == 0
```

### Integration Tests

```python
# test_integration.py
import pytest
import os
from services.weather import WeatherService

@pytest.mark.integration
class TestWeatherIntegration:
    """Integration tests requiring real API key."""
    
    def setup_method(self):
        """Reset services and check API key."""
        WeatherService._initialized = False
        
        if not os.getenv("WEATHER_API_KEY"):
            pytest.skip("WEATHER_API_KEY not set - skipping integration tests")
    
    def test_real_weather_api(self):
        """Test with real weather API."""
        weather = WeatherService.get_weather("London")
        
        assert weather.location
        assert isinstance(weather.temperature, float)
        assert weather.description
        assert 0 <= weather.humidity <= 100
    
    def test_caching_works(self):
        """Test that caching actually works."""
        # First call
        start_time = time.time()
        weather1 = WeatherService.get_weather("London")
        first_duration = time.time() - start_time
        
        # Second call (should be cached)
        start_time = time.time()
        weather2 = WeatherService.get_weather("London")
        second_duration = time.time() - start_time
        
        # Cached call should be much faster
        assert second_duration < first_duration / 2
        assert weather1.location == weather2.location
```

## 🎯 Key Patterns Demonstrated

### 1. Configuration Management
- Type-safe configuration with validation
- Environment variable loading with defaults
- Centralized configuration access

### 2. Caching Strategy
- TTL-based in-memory caching
- Cache statistics and monitoring
- Cache key management

### 3. HTTP Client Patterns
- Session reuse and configuration
- Retry logic with exponential backoff
- Request statistics tracking

### 4. Error Handling
- Graceful degradation with fallback data
- Specific error types for different scenarios
- Comprehensive error logging

### 5. Service Composition
- Clear dependency relationships
- Service method delegation
- Coordinated initialization

### 6. Testing Strategies
- Service mocking and isolation
- Integration test patterns
- Performance testing

## 🚀 Running the Example

1. **Get an API key** from [OpenWeatherMap](https://openweathermap.org/api)

2. **Set up environment**:
```bash
export WEATHER_API_KEY="your_api_key_here"
```

3. **Install dependencies**:
```bash
pip install singleton-service requests python-dotenv click
```

4. **Run the example**:
```bash
python main.py
python cli.py current London
python cli.py forecast "New York" --days 3
```

5. **Run tests**:
```bash
pytest test_weather.py
WEATHER_API_KEY=your_key pytest test_integration.py -m integration
```

This example demonstrates a production-ready service architecture with proper error handling, caching, configuration management, and testing strategies.

---

**Next Example**: Learn database patterns → [Database Service](database-service.md)