# Testing Services

🎯 **Learning Goals**: Master comprehensive testing strategies for singleton services, including mocking, fixtures, and testing complex dependency chains.

Testing singleton services requires special techniques because of their shared state and initialization patterns. In this final tutorial, you'll learn how to write reliable, comprehensive tests that cover all aspects of your service architecture.

## 📚 Understanding Service Testing Challenges

### Unique Testing Challenges

Singleton services present unique testing challenges:

- **Shared State**: Services maintain state across test runs
- **Initialization Order**: Dependencies must be properly set up
- **External Dependencies**: Services often depend on databases, APIs, files
- **Error Scenarios**: Testing failure cases requires careful setup

### Testing Strategy Overview

Our testing approach addresses these challenges:

1. **Reset Between Tests**: Clear service state for isolation
2. **Mock External Dependencies**: Avoid real databases/APIs in tests
3. **Test Initialization**: Verify proper startup and health checks
4. **Test Error Scenarios**: Cover all failure cases
5. **Integration Testing**: Test service interactions

## 💻 Setting Up the Test Environment

### Step 1: Test Infrastructure

First, let's create the testing infrastructure:

```python
# test_base.py
import pytest
from typing import List, Type
from singleton_service import BaseService

class ServiceTestBase:
    """Base class for service testing with cleanup utilities."""
    
    @staticmethod
    def reset_services(*service_classes: Type[BaseService]) -> None:
        """Reset services to uninitialized state."""
        for service_class in service_classes:
            # Reset initialization state
            service_class._initialized = False
            
            # Clear dependencies if they exist
            if hasattr(service_class, '_dependencies'):
                service_class._dependencies = set()
            
            # Reset any class variables to their defaults
            # This is service-specific and might need customization
            ServiceTestBase._reset_service_state(service_class)
    
    @staticmethod
    def _reset_service_state(service_class: Type[BaseService]) -> None:
        """Reset service-specific state variables."""
        # Common patterns for resetting state
        for attr_name in dir(service_class):
            if attr_name.startswith('_') and not attr_name.startswith('__'):
                attr = getattr(service_class, attr_name)
                
                # Reset containers to empty
                if isinstance(attr, dict):
                    attr.clear()
                elif isinstance(attr, list):
                    attr.clear()
                elif isinstance(attr, set):
                    attr.clear()
                # Reset None-able attributes
                elif attr_name.endswith('_connection') or attr_name.endswith('_client'):
                    setattr(service_class, attr_name, None)

@pytest.fixture(autouse=True)
def reset_all_services():
    """Automatically reset all services before each test."""
    # Import all your services here
    from database_service import DatabaseService
    from weather_service import WeatherService
    from notification_service import NotificationService
    
    services = [DatabaseService, WeatherService, NotificationService]
    
    # Reset before test
    ServiceTestBase.reset_services(*services)
    
    yield  # Run the test
    
    # Reset after test (cleanup)
    ServiceTestBase.reset_services(*services)
```

### Step 2: Mock Services for Testing

Create mock versions of services for testing:

```python
# test_mocks.py
from typing import ClassVar, Optional, Dict, Any
from singleton_service import BaseService, guarded

class MockDatabaseService(BaseService):
    """Mock database service for testing."""
    
    _users: ClassVar[Dict[int, Dict[str, Any]]] = {}
    _next_id: ClassVar[int] = 1
    _should_fail: ClassVar[bool] = False
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize mock database."""
        cls._users = {
            1: {"id": 1, "name": "Test User", "email": "test@example.com"},
            2: {"id": 2, "name": "Jane Doe", "email": "jane@example.com"},
        }
        cls._next_id = 3
        cls._should_fail = False
    
    @classmethod
    def ping(cls) -> bool:
        """Mock health check."""
        return not cls._should_fail
    
    @classmethod
    @guarded
    def create_user(cls, name: str, email: str) -> int:
        """Mock user creation."""
        if cls._should_fail:
            raise RuntimeError("Database error")
        
        user_id = cls._next_id
        cls._next_id += 1
        cls._users[user_id] = {"id": user_id, "name": name, "email": email}
        return user_id
    
    @classmethod
    @guarded
    def get_user(cls, user_id: int) -> Optional[Dict[str, Any]]:
        """Mock user retrieval."""
        if cls._should_fail:
            raise RuntimeError("Database error")
        return cls._users.get(user_id)
    
    @classmethod
    def set_failure_mode(cls, should_fail: bool) -> None:
        """Control mock failure for testing."""
        cls._should_fail = should_fail

class MockWeatherService(BaseService):
    """Mock weather service for testing."""
    
    _weather_data: ClassVar[Dict[str, Dict[str, Any]]] = {}
    _should_fail: ClassVar[bool] = False
    _use_fallback: ClassVar[bool] = False
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize mock weather service."""
        cls._weather_data = {
            "london": {"city": "London", "temperature": 15, "description": "Cloudy", "humidity": 65, "source": "api"},
            "paris": {"city": "Paris", "temperature": 18, "description": "Sunny", "humidity": 55, "source": "api"},
        }
        cls._should_fail = False
        cls._use_fallback = False
    
    @classmethod
    def ping(cls) -> bool:
        """Mock health check."""
        return not cls._should_fail
    
    @classmethod
    @guarded
    def get_weather(cls, city: str) -> Dict[str, Any]:
        """Mock weather retrieval."""
        if cls._should_fail:
            raise RuntimeError("Weather API error")
        
        city_lower = city.lower()
        
        if cls._use_fallback or city_lower not in cls._weather_data:
            return {
                "city": city,
                "temperature": 20,
                "description": "Unknown",
                "humidity": 60,
                "source": "fallback"
            }
        
        return cls._weather_data[city_lower].copy()
    
    @classmethod
    def set_failure_mode(cls, should_fail: bool) -> None:
        """Control mock failure for testing."""
        cls._should_fail = should_fail
    
    @classmethod
    def set_fallback_mode(cls, use_fallback: bool) -> None:
        """Control mock fallback behavior."""
        cls._use_fallback = use_fallback
```

## 🧪 Unit Testing Individual Services

### Step 3: Testing Service Initialization

```python
# test_database_service.py
import pytest
from test_base import ServiceTestBase
from test_mocks import MockDatabaseService
from singleton_service.exceptions import ServiceInitializationError

class TestDatabaseService(ServiceTestBase):
    """Test suite for database service."""
    
    def test_service_initialization(self):
        """Test that service initializes correctly."""
        # Service should not be initialized initially
        assert not MockDatabaseService._initialized
        
        # First call should trigger initialization
        users = MockDatabaseService.get_user(1)
        
        # Service should now be initialized
        assert MockDatabaseService._initialized
        assert users is not None
        assert users["name"] == "Test User"
    
    def test_service_ping_healthy(self):
        """Test health check when service is healthy."""
        MockDatabaseService.initialize()
        assert MockDatabaseService.ping() is True
    
    def test_service_ping_unhealthy(self):
        """Test health check when service is unhealthy."""
        MockDatabaseService.initialize()
        MockDatabaseService.set_failure_mode(True)
        assert MockDatabaseService.ping() is False
    
    def test_service_initialization_failure(self):
        """Test service initialization failure."""
        # Set failure mode before initialization
        MockDatabaseService.set_failure_mode(True)
        
        # Should raise ServiceInitializationError
        with pytest.raises(ServiceInitializationError):
            MockDatabaseService.get_user(1)
        
        # Service should not be marked as initialized
        assert not MockDatabaseService._initialized
    
    def test_create_user_success(self):
        """Test successful user creation."""
        user_id = MockDatabaseService.create_user("New User", "new@example.com")
        
        assert isinstance(user_id, int)
        assert user_id > 0
        
        # Verify user was created
        user = MockDatabaseService.get_user(user_id)
        assert user["name"] == "New User"
        assert user["email"] == "new@example.com"
    
    def test_create_user_failure(self):
        """Test user creation failure."""
        MockDatabaseService.initialize()
        MockDatabaseService.set_failure_mode(True)
        
        with pytest.raises(RuntimeError, match="Database error"):
            MockDatabaseService.create_user("Fail User", "fail@example.com")
    
    def test_get_user_not_found(self):
        """Test retrieving non-existent user."""
        user = MockDatabaseService.get_user(999)
        assert user is None
    
    def test_multiple_calls_no_reinitialize(self):
        """Test that multiple calls don't reinitialize service."""
        # First call initializes
        MockDatabaseService.get_user(1)
        first_init_state = MockDatabaseService._initialized
        
        # Second call should not reinitialize
        MockDatabaseService.get_user(2)
        second_init_state = MockDatabaseService._initialized
        
        assert first_init_state is True
        assert second_init_state is True
```

### Step 4: Testing Service Dependencies

```python
# test_notification_service.py
import pytest
from unittest.mock import patch, MagicMock
from test_base import ServiceTestBase
from test_mocks import MockDatabaseService, MockWeatherService

# Create a notification service that uses mocks
from singleton_service import BaseService, requires, guarded

@requires(MockDatabaseService, MockWeatherService)
class TestableNotificationService(BaseService):
    """Notification service using mock dependencies for testing."""
    
    _notifications: ClassVar[List[Dict[str, Any]]] = []
    
    @classmethod
    def initialize(cls) -> None:
        cls._notifications = []
    
    @classmethod
    @guarded
    def send_weather_notification(cls, user_email: str, city: str) -> Dict[str, Any]:
        """Send weather notification."""
        try:
            # Get weather data
            weather = MockWeatherService.get_weather(city)
            
            # Simulate notification
            notification = {
                "email": user_email,
                "city": city,
                "weather": weather,
                "success": True
            }
            cls._notifications.append(notification)
            
            return notification
            
        except Exception as e:
            notification = {
                "email": user_email,
                "city": city,
                "error": str(e),
                "success": False
            }
            cls._notifications.append(notification)
            return notification

class TestNotificationService(ServiceTestBase):
    """Test suite for notification service with dependencies."""
    
    def setup_method(self):
        """Set up test environment."""
        # Reset all services
        self.reset_services(MockDatabaseService, MockWeatherService, TestableNotificationService)
    
    def test_dependency_initialization_order(self):
        """Test that dependencies initialize in correct order."""
        # Track initialization calls
        init_order = []
        
        original_db_init = MockDatabaseService.initialize
        original_weather_init = MockWeatherService.initialize
        original_notification_init = TestableNotificationService.initialize
        
        def track_db_init():
            init_order.append("database")
            original_db_init()
        
        def track_weather_init():
            init_order.append("weather")
            original_weather_init()
        
        def track_notification_init():
            init_order.append("notification")
            original_notification_init()
        
        MockDatabaseService.initialize = classmethod(track_db_init)
        MockWeatherService.initialize = classmethod(track_weather_init)
        TestableNotificationService.initialize = classmethod(track_notification_init)
        
        try:
            # Trigger initialization
            TestableNotificationService.send_weather_notification("test@example.com", "london")
            
            # Verify dependencies initialized before notification service
            assert "database" in init_order
            assert "weather" in init_order
            assert "notification" in init_order
            
            db_index = init_order.index("database")
            weather_index = init_order.index("weather")
            notification_index = init_order.index("notification")
            
            # Dependencies should initialize before dependent service
            assert db_index < notification_index
            assert weather_index < notification_index
            
        finally:
            # Restore original methods
            MockDatabaseService.initialize = original_db_init
            MockWeatherService.initialize = original_weather_init
            TestableNotificationService.initialize = original_notification_init
    
    def test_successful_notification(self):
        """Test successful notification sending."""
        result = TestableNotificationService.send_weather_notification("user@example.com", "london")
        
        assert result["success"] is True
        assert result["email"] == "user@example.com"
        assert result["city"] == "london"
        assert "weather" in result
        assert result["weather"]["temperature"] == 15
    
    def test_notification_with_fallback_weather(self):
        """Test notification when weather service uses fallback."""
        MockWeatherService.set_fallback_mode(True)
        
        result = TestableNotificationService.send_weather_notification("user@example.com", "unknown_city")
        
        assert result["success"] is True
        assert result["weather"]["source"] == "fallback"
    
    def test_notification_with_weather_failure(self):
        """Test notification when weather service fails."""
        MockWeatherService.set_failure_mode(True)
        
        result = TestableNotificationService.send_weather_notification("user@example.com", "london")
        
        assert result["success"] is False
        assert "error" in result
        assert "Weather API error" in result["error"]
    
    def test_dependency_failure_propagation(self):
        """Test that dependency failures propagate correctly."""
        # Set database to fail during initialization
        MockDatabaseService.set_failure_mode(True)
        
        with pytest.raises(ServiceInitializationError):
            TestableNotificationService.send_weather_notification("user@example.com", "london")
        
        # Notification service should not be initialized
        assert not TestableNotificationService._initialized
```

## 🔧 Integration Testing

### Step 5: Testing Complex Service Interactions

```python
# test_integration.py
import pytest
from test_base import ServiceTestBase
from test_mocks import MockDatabaseService, MockWeatherService

class TestServiceIntegration(ServiceTestBase):
    """Integration tests for service interactions."""
    
    def test_end_to_end_workflow(self):
        """Test complete workflow across multiple services."""
        # Create a user
        user_id = MockDatabaseService.create_user("Integration User", "integration@example.com")
        assert user_id > 0
        
        # Verify user was created
        user = MockDatabaseService.get_user(user_id)
        assert user["name"] == "Integration User"
        
        # Get weather data
        weather = MockWeatherService.get_weather("london")
        assert weather["city"] == "London"
        assert weather["source"] == "api"
        
        # Send notification combining both services
        # (Would use a service that combines database + weather + notification)
    
    def test_service_failure_isolation(self):
        """Test that one service failure doesn't break others."""
        # Weather service fails
        MockWeatherService.set_failure_mode(True)
        
        # Database service should still work
        user_id = MockDatabaseService.create_user("Isolation Test", "isolation@example.com")
        assert user_id > 0
        
        user = MockDatabaseService.get_user(user_id)
        assert user["name"] == "Isolation Test"
        
        # Weather service should fail
        with pytest.raises(RuntimeError):
            MockWeatherService.get_weather("london")
    
    def test_service_recovery_after_failure(self):
        """Test service recovery after temporary failure."""
        # Initially working
        weather1 = MockWeatherService.get_weather("london")
        assert weather1["source"] == "api"
        
        # Simulate failure
        MockWeatherService.set_failure_mode(True)
        with pytest.raises(RuntimeError):
            MockWeatherService.get_weather("paris")
        
        # Recovery
        MockWeatherService.set_failure_mode(False)
        weather2 = MockWeatherService.get_weather("paris")
        assert weather2["source"] == "api"
        assert weather2["city"] == "Paris"
```

## 🎯 Testing Error Scenarios

### Step 6: Comprehensive Error Testing

```python
# test_error_scenarios.py
import pytest
from singleton_service.exceptions import (
    ServiceInitializationError, CircularDependencyError, SelfDependencyError
)
from test_base import ServiceTestBase

class TestErrorScenarios(ServiceTestBase):
    """Test error handling and edge cases."""
    
    def test_circular_dependency_detection(self):
        """Test circular dependency detection."""
        from singleton_service import BaseService, requires
        
        # Create circular dependency
        @requires()  # Will be modified to create circle
        class ServiceA(BaseService):
            @classmethod
            def initialize(cls): pass
        
        @requires(ServiceA)
        class ServiceB(BaseService):
            @classmethod
            def initialize(cls): pass
        
        # Create the circle
        ServiceA._dependencies = {ServiceB}
        
        with pytest.raises(CircularDependencyError):
            ServiceA._raise_on_circular_dependencies()
    
    def test_self_dependency_error(self):
        """Test self-dependency detection."""
        from singleton_service import BaseService, guarded
        
        class SelfDependentService(BaseService):
            @classmethod
            def initialize(cls):
                # This should raise SelfDependencyError
                cls.guarded_method()
            
            @classmethod
            @guarded
            def guarded_method(cls):
                return "This shouldn't be called from initialize"
        
        with pytest.raises(SelfDependencyError):
            SelfDependentService.guarded_method()
    
    def test_initialization_error_propagation(self):
        """Test that initialization errors propagate with context."""
        MockDatabaseService.set_failure_mode(True)
        
        try:
            MockDatabaseService.get_user(1)
        except ServiceInitializationError as e:
            # Should contain service name and error context
            assert "MockDatabaseService" in str(e) or "failed to initialize" in str(e)
        else:
            pytest.fail("Expected ServiceInitializationError")
    
    def test_ping_failure_prevents_initialization(self):
        """Test that ping() failure prevents service initialization."""
        from singleton_service import BaseService, guarded
        
        class UnhealthyService(BaseService):
            @classmethod
            def initialize(cls):
                # Initialization succeeds
                pass
            
            @classmethod
            def ping(cls) -> bool:
                # But health check fails
                return False
            
            @classmethod
            @guarded
            def do_something(cls):
                return "Should not reach here"
        
        with pytest.raises(ServiceInitializationError):
            UnhealthyService.do_something()
        
        assert not UnhealthyService._initialized
```

## 📊 Test Coverage and Performance

### Step 7: Testing Best Practices

```python
# test_performance.py
import time
import pytest
from test_base import ServiceTestBase
from test_mocks import MockDatabaseService

class TestServicePerformance(ServiceTestBase):
    """Performance and behavior tests."""
    
    def test_initialization_happens_once(self):
        """Test that services initialize only once."""
        # Track initialization calls
        init_count = 0
        original_init = MockDatabaseService.initialize
        
        def counting_init():
            nonlocal init_count
            init_count += 1
            original_init()
        
        MockDatabaseService.initialize = classmethod(counting_init)
        
        try:
            # Multiple calls should only initialize once
            MockDatabaseService.get_user(1)
            MockDatabaseService.get_user(2)
            MockDatabaseService.create_user("Test", "test@example.com")
            
            assert init_count == 1
        finally:
            MockDatabaseService.initialize = original_init
    
    def test_guarded_method_performance(self):
        """Test that @guarded methods have minimal overhead after initialization."""
        # Initialize service
        MockDatabaseService.get_user(1)
        
        # Time subsequent calls
        start_time = time.time()
        for _ in range(100):
            MockDatabaseService.get_user(1)
        end_time = time.time()
        
        # Should be very fast (no re-initialization)
        avg_time = (end_time - start_time) / 100
        assert avg_time < 0.001  # Less than 1ms per call
    
    def test_memory_cleanup_between_tests(self):
        """Test that service state is properly reset between tests."""
        # Create user in first "test"
        user_id = MockDatabaseService.create_user("Cleanup Test", "cleanup@example.com")
        original_users = MockDatabaseService._users.copy()
        
        # Reset service (simulating test cleanup)
        self.reset_services(MockDatabaseService)
        
        # Service should be uninitialized
        assert not MockDatabaseService._initialized
        
        # Create user again - should start fresh
        MockDatabaseService.initialize()
        new_user_id = MockDatabaseService.create_user("Fresh Test", "fresh@example.com")
        
        # Should get a fresh instance with default data
        assert len(MockDatabaseService._users) == 3  # 2 default + 1 new
        assert MockDatabaseService.get_user(new_user_id)["name"] == "Fresh Test"

# Test runner configuration
def run_all_tests():
    """Run all tests with coverage reporting."""
    pytest.main([
        "test_database_service.py",
        "test_notification_service.py", 
        "test_integration.py",
        "test_error_scenarios.py",
        "test_performance.py",
        "--cov=singleton_service",
        "--cov-report=html",
        "--cov-report=term-missing",
        "-v"
    ])

if __name__ == "__main__":
    run_all_tests()
```

## ✅ Summary

Congratulations! You've completed the complete **singleton-service** tutorial series! Here's what you mastered in this final tutorial:

- ✅ **Service testing infrastructure** - Reset mechanisms and test isolation
- ✅ **Mock services** - Creating controllable test doubles for dependencies
- ✅ **Unit testing** - Testing individual service functionality and error cases
- ✅ **Dependency testing** - Verifying correct initialization order and interactions
- ✅ **Integration testing** - Testing complete workflows across multiple services
- ✅ **Error scenario testing** - Comprehensive coverage of failure cases
- ✅ **Performance testing** - Ensuring initialization efficiency and overhead management

### Key Testing Takeaways

1. **Reset state between tests** - Use fixtures to ensure test isolation
2. **Mock external dependencies** - Avoid real databases/APIs in unit tests
3. **Test initialization order** - Verify dependencies initialize before dependents
4. **Cover error scenarios** - Test all exception types and failure modes
5. **Test performance characteristics** - Ensure minimal overhead after initialization
6. **Use integration tests** - Verify end-to-end workflows work correctly

## 🎓 Tutorial Series Complete!

You've now mastered all aspects of **singleton-service**:

1. ✅ **[Your First Service](first-service.md)** - Basic service creation and concepts
2. ✅ **[Adding Dependencies](dependencies.md)** - Dependency management with `@requires`
3. ✅ **[Initialization Order](initialization-order.md)** - Understanding dependency resolution
4. ✅ **[Health Checks](health-checks.md)** - Implementing robust service verification
5. ✅ **[Error Handling](error-handling.md)** - Comprehensive failure management
6. ✅ **[Testing Services](testing.md)** - Complete testing strategies

## 🚀 What's Next?

Now that you're a **singleton-service** expert, explore these resources:

- **[Examples](../examples/)** - Real-world patterns and use cases
- **[API Reference](../api/)** - Complete API documentation
- **[Advanced Topics](../advanced/)** - Performance optimization and complex patterns
- **[Best Practices](../concepts/best-practices.md)** - Production deployment guidelines

### Start Building!

You're ready to build robust, maintainable service-oriented applications with **singleton-service**. The framework will handle dependency management, initialization order, and error propagation while you focus on your business logic.

Happy coding! 🎉

---

**Tutorial Progress**: 6/6 complete ✅✅✅✅✅✅  
**Previous**: [Error Handling](error-handling.md) | **Completed!** 🎓  
**Total time**: ~2.5 hours ⏱️