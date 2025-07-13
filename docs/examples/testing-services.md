# Testing Services Example

This example demonstrates comprehensive testing strategies for **singleton-service** applications. It showcases unit testing, integration testing, mocking patterns, and test organization.

## 🎯 What You'll Learn

- Unit testing singleton services
- Mocking service dependencies
- Integration testing patterns
- Test isolation and cleanup
- Performance testing
- Test organization and fixtures

## 📋 Complete Implementation

### Dependencies

```bash
pip install singleton-service pytest pytest-asyncio pytest-cov factory-boy faker
```

### Test Utilities

```python
# tests/utils.py
import pytest
from typing import List, Type, Any
from unittest.mock import MagicMock
from singleton_service import BaseService

class ServiceTestHelper:
    """Helper class for testing singleton services."""
    
    @staticmethod
    def reset_services(*services: Type[BaseService]) -> None:
        """Reset initialization state of services."""
        for service in services:
            service._initialized = False
            # Reset any class variables to default values
            for attr_name in dir(service):
                if attr_name.startswith('_') and not attr_name.startswith('__'):
                    attr = getattr(service, attr_name)
                    if hasattr(attr, '__annotations__'):
                        # Reset ClassVar attributes to None or empty collections
                        default_value = None
                        if 'Dict' in str(attr):
                            default_value = {}
                        elif 'List' in str(attr):
                            default_value = []
                        elif 'Set' in str(attr):
                            default_value = set()
                        
                        if default_value is not None:
                            setattr(service, attr_name, default_value)
    
    @staticmethod
    def mock_service_method(service: Type[BaseService], method_name: str, return_value: Any = None) -> MagicMock:
        """Mock a service method and return the mock object."""
        mock = MagicMock(return_value=return_value)
        setattr(service, method_name, mock)
        return mock
    
    @staticmethod
    def create_test_service_data() -> dict:
        """Create test data for services."""
        return {
            "test_user": {
                "id": 1,
                "username": "testuser",
                "email": "test@example.com",
                "password_hash": "$2b$12$test_hash",
                "roles": ["user"],
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00"
            }
        }

@pytest.fixture
def service_helper():
    """Provide service test helper."""
    return ServiceTestHelper

@pytest.fixture(autouse=True)
def reset_all_services():
    """Automatically reset all services before each test."""
    # Import all services that need resetting
    from services.config import ConfigService
    from services.database import DatabaseService
    from services.auth import AuthService
    from services.user_service import UserService
    
    services_to_reset = [
        ConfigService,
        DatabaseService, 
        AuthService,
        UserService
    ]
    
    ServiceTestHelper.reset_services(*services_to_reset)
    
    yield
    
    # Cleanup after test
    ServiceTestHelper.reset_services(*services_to_reset)
```

### Unit Tests

```python
# tests/test_user_service.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from services.user_service import UserService
from services.validation import ValidationService
from services.events import EventService
from models.user import CreateUserRequest, UserRole, UserStatus, UserResponse
from tests.utils import ServiceTestHelper

class TestUserService:
    """Unit tests for UserService."""
    
    def test_create_user_success(self, service_helper):
        """Test successful user creation."""
        # Arrange
        request = CreateUserRequest(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
            first_name="Test",
            last_name="User"
        )
        
        expected_user_data = {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "roles": ["user"],
            "status": "active",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Mock dependencies
        with patch.object(ValidationService, 'sanitize_user_input', return_value=request.dict()), \
             patch.object(ValidationService, 'validate_username_uniqueness', return_value=True), \
             patch.object(ValidationService, 'validate_email_uniqueness', return_value=True), \
             patch.object(UserService, '_hash_password', return_value="hashed_password"), \
             patch.object(UserService, '_create_user_in_db', return_value=expected_user_data), \
             patch.object(EventService, 'publish') as mock_publish:
            
            # Act
            result = UserService.create_user(request)
            
            # Assert
            assert result.username == "testuser"
            assert result.email == "test@example.com"
            assert result.id == 1
            
            # Verify event was published
            mock_publish.assert_called_once_with(
                "user_created", 
                1, 
                {
                    "username": "testuser",
                    "email": "test@example.com",
                    "roles": ["user"],
                    "created_by": None
                }
            )
    
    def test_create_user_duplicate_username(self, service_helper):
        """Test error when username already exists."""
        request = CreateUserRequest(
            username="duplicate",
            email="test@example.com", 
            password="TestPass123!",
            first_name="Test",
            last_name="User"
        )
        
        with patch.object(ValidationService, 'sanitize_user_input', return_value=request.dict()), \
             patch.object(ValidationService, 'validate_username_uniqueness', return_value=False):
            
            with pytest.raises(ValueError, match="Username 'duplicate' is already taken"):
                UserService.create_user(request)
    
    def test_create_user_invalid_email(self, service_helper):
        """Test error when email already exists."""
        request = CreateUserRequest(
            username="testuser",
            email="duplicate@example.com",
            password="TestPass123!",
            first_name="Test", 
            last_name="User"
        )
        
        with patch.object(ValidationService, 'sanitize_user_input', return_value=request.dict()), \
             patch.object(ValidationService, 'validate_username_uniqueness', return_value=True), \
             patch.object(ValidationService, 'validate_email_uniqueness', return_value=False):
            
            with pytest.raises(ValueError, match="Email 'duplicate@example.com' is already registered"):
                UserService.create_user(request)
    
    def test_get_user_by_id_found(self, service_helper):
        """Test getting user by ID when user exists."""
        user_data = {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "roles": ["user"],
            "status": "active",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        with patch.object(UserService, '_get_user_from_db', return_value=user_data):
            result = UserService.get_user_by_id(1)
            
            assert result is not None
            assert result.id == 1
            assert result.username == "testuser"
    
    def test_get_user_by_id_not_found(self, service_helper):
        """Test getting user by ID when user doesn't exist."""
        with patch.object(UserService, '_get_user_from_db', return_value=None):
            result = UserService.get_user_by_id(999)
            assert result is None
    
    def test_update_user_success(self, service_helper):
        """Test successful user update."""
        existing_user = UserResponse(
            id=1,
            username="testuser",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            status=UserStatus.ACTIVE,
            roles=[UserRole.USER],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        update_data = {"first_name": "Updated"}
        
        updated_user_data = {
            **existing_user.dict(),
            "first_name": "Updated",
            "updated_at": datetime.utcnow()
        }
        
        with patch.object(UserService, '_get_user_from_db', return_value=existing_user.dict()), \
             patch.object(ValidationService, 'sanitize_user_input', return_value=update_data), \
             patch.object(UserService, '_update_user_in_db', return_value=updated_user_data), \
             patch.object(EventService, 'publish') as mock_publish:
            
            result = UserService.update_user(1, update_data, updated_by_user=existing_user)
            
            assert result.first_name == "Updated"
            mock_publish.assert_called_once()
    
    def test_update_user_permission_denied(self, service_helper):
        """Test update fails when user lacks permission."""
        target_user = UserResponse(
            id=1, username="target", email="target@example.com",
            first_name="Target", last_name="User",
            status=UserStatus.ACTIVE, roles=[UserRole.USER],
            created_at=datetime.utcnow(), updated_at=datetime.utcnow()
        )
        
        updating_user = UserResponse(
            id=2, username="other", email="other@example.com", 
            first_name="Other", last_name="User",
            status=UserStatus.ACTIVE, roles=[UserRole.USER],
            created_at=datetime.utcnow(), updated_at=datetime.utcnow()
        )
        
        with patch.object(UserService, '_get_user_from_db', return_value=target_user.dict()):
            with pytest.raises(ValueError, match="Insufficient permissions"):
                UserService.update_user(1, {"first_name": "Hacker"}, updated_by_user=updating_user)

class TestUserServiceIntegration:
    """Integration tests that test service interactions."""
    
    @pytest.mark.integration
    def test_user_creation_workflow(self, service_helper):
        """Test complete user creation workflow with all services."""
        # This test uses real service interactions
        request = CreateUserRequest(
            username="integration_test",
            email="integration@test.com",
            password="TestPass123!",
            first_name="Integration",
            last_name="Test"
        )
        
        # Initialize services
        ValidationService.initialize()
        EventService.initialize()
        
        # Create user (this will test the full workflow)
        try:
            user = UserService.create_user(request)
            
            assert user.username == "integration_test"
            assert user.email == "integration@test.com"
            
            # Verify event was recorded
            events = EventService.get_user_events(user.id)
            assert len(events) > 0
            assert events[0].event_type == "user_created"
            
        except Exception as e:
            pytest.fail(f"Integration test failed: {e}")
```

### Mock Factories

```python
# tests/factories.py
import factory
from factory import Factory, Faker, SubFactory, LazyAttribute
from faker import Faker as FakerProvider
from datetime import datetime
from models.user import UserResponse, UserStatus, UserRole

fake = FakerProvider()

class UserResponseFactory(Factory):
    """Factory for creating UserResponse test objects."""
    
    class Meta:
        model = UserResponse
    
    id = factory.Sequence(lambda n: n)
    username = factory.LazyAttribute(lambda obj: fake.user_name())
    email = factory.LazyAttribute(lambda obj: fake.email())
    first_name = factory.LazyAttribute(lambda obj: fake.first_name())
    last_name = factory.LazyAttribute(lambda obj: fake.last_name())
    status = UserStatus.ACTIVE
    roles = [UserRole.USER]
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)
    is_verified = True

class AdminUserFactory(UserResponseFactory):
    """Factory for admin users."""
    roles = [UserRole.ADMIN]
    username = "admin"
    email = "admin@example.com"

class InactiveUserFactory(UserResponseFactory):
    """Factory for inactive users."""
    status = UserStatus.INACTIVE
    is_verified = False

# Usage examples in tests
def test_with_factory():
    """Example test using factories."""
    # Create a regular user
    user = UserResponseFactory()
    assert user.status == UserStatus.ACTIVE
    
    # Create an admin user
    admin = AdminUserFactory()
    assert UserRole.ADMIN in admin.roles
    
    # Create multiple users
    users = UserResponseFactory.create_batch(5)
    assert len(users) == 5
    
    # Create user with specific attributes
    custom_user = UserResponseFactory(username="custom", email="custom@test.com")
    assert custom_user.username == "custom"
```

### Performance Tests

```python
# tests/test_performance.py
import pytest
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from services.user_service import UserService
from services.cache import CacheService
from tests.factories import UserResponseFactory

class TestPerformance:
    """Performance tests for singleton services."""
    
    @pytest.mark.performance
    def test_service_initialization_time(self, service_helper):
        """Test that service initialization is fast."""
        start_time = time.time()
        
        # Initialize multiple services
        services = [UserService, CacheService]
        for service in services:
            service.initialize()
        
        initialization_time = time.time() - start_time
        
        # Should initialize quickly (less than 100ms)
        assert initialization_time < 0.1, f"Initialization took {initialization_time:.3f}s"
    
    @pytest.mark.performance
    def test_concurrent_service_access(self, service_helper):
        """Test concurrent access to singleton services."""
        # Mock user data
        user_data = UserResponseFactory().dict()
        
        with patch.object(UserService, '_get_user_from_db', return_value=user_data):
            def get_user_worker(user_id):
                """Worker function for concurrent access."""
                return UserService.get_user_by_id(user_id)
            
            # Test concurrent access
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(get_user_worker, 1) for _ in range(100)]
                results = [future.result() for future in as_completed(futures)]
            
            access_time = time.time() - start_time
            
            # All requests should succeed
            assert len(results) == 100
            assert all(result is not None for result in results)
            
            # Should handle concurrent access efficiently
            assert access_time < 1.0, f"Concurrent access took {access_time:.3f}s"
    
    @pytest.mark.performance
    def test_memory_usage_stability(self, service_helper):
        """Test that memory usage remains stable across operations."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Perform many operations
        for i in range(1000):
            user_data = UserResponseFactory().dict()
            with patch.object(UserService, '_get_user_from_db', return_value=user_data):
                UserService.get_user_by_id(i)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be minimal (less than 10MB)
        assert memory_increase < 10 * 1024 * 1024, f"Memory increased by {memory_increase} bytes"
```

### Test Configuration

```python
# conftest.py
import pytest
import os
import tempfile
from unittest.mock import patch

# Test configuration
@pytest.fixture(scope="session")
def test_config():
    """Provide test configuration."""
    return {
        "DATABASE_URL": "sqlite:///:memory:",
        "JWT_SECRET_KEY": "test-secret-key-for-testing-only",
        "REDIS_URL": "redis://localhost:6379/15",  # Use test database
        "ENVIRONMENT": "test"
    }

@pytest.fixture(autouse=True)
def setup_test_environment(test_config):
    """Setup test environment variables."""
    with patch.dict(os.environ, test_config):
        yield

@pytest.fixture
def temp_file():
    """Create temporary file for testing."""
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
        yield f.name
    os.unlink(f.name)

# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers."""
    # Add integration marker to tests in integration directories
    for item in items:
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        
        if "performance" in item.nodeid:
            item.add_marker(pytest.mark.performance)

# Pytest command line options
def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run integration tests"
    )
    parser.addoption(
        "--run-performance",
        action="store_true", 
        default=False,
        help="run performance tests"
    )

def pytest_runtest_setup(item):
    """Setup for individual tests."""
    # Skip integration tests unless specifically requested
    if "integration" in item.keywords and not item.config.getoption("--run-integration"):
        pytest.skip("need --run-integration option to run")
    
    # Skip performance tests unless specifically requested
    if "performance" in item.keywords and not item.config.getoption("--run-performance"):
        pytest.skip("need --run-performance option to run")
```

## 🚀 Usage Examples

### Running Tests

```bash
# Run all unit tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=services --cov-report=html

# Run integration tests
pytest tests/ --run-integration

# Run performance tests
pytest tests/ --run-performance

# Run specific test file
pytest tests/test_user_service.py -v

# Run tests matching pattern
pytest tests/ -k "test_create_user" -v

# Run tests in parallel
pytest tests/ -n auto
```

### Test Organization

```
tests/
├── conftest.py              # Test configuration
├── utils.py                 # Test utilities
├── factories.py             # Test data factories
├── unit/                    # Unit tests
│   ├── test_user_service.py
│   ├── test_auth_service.py
│   └── test_validation.py
├── integration/             # Integration tests
│   ├── test_user_workflow.py
│   └── test_api_endpoints.py
├── performance/             # Performance tests
│   ├── test_load.py
│   └── test_memory.py
└── fixtures/                # Test data files
    ├── sample_users.json
    └── test_config.yaml
```

### Test Automation

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run unit tests
      run: pytest tests/unit/ --cov=services
    
    - name: Run integration tests
      run: pytest tests/integration/ --run-integration
      env:
        DATABASE_URL: postgresql://test:test@localhost/test_db
    
    - name: Upload coverage
      uses: codecov/codecov-action@v1
```

## 🎯 Key Patterns Demonstrated

### 1. Test Isolation
- Service state reset between tests
- Mocking external dependencies
- Test-specific configuration
- Cleanup after tests

### 2. Mock Strategies
- Service method mocking
- Dependency injection mocking
- Database operation mocking
- External API mocking

### 3. Test Organization
- Unit vs integration vs performance tests
- Test utilities and helpers
- Factory pattern for test data
- Consistent test structure

### 4. Coverage and Quality
- Code coverage measurement
- Performance benchmarking
- Concurrent access testing
- Memory usage monitoring

### 5. CI/CD Integration
- Automated test running
- Multiple test environments
- Coverage reporting
- Test result analysis

This example demonstrates comprehensive testing strategies for singleton services with proper isolation, mocking, and organization patterns.

---

**Next Example**: Learn advanced patterns → [Service Composition](service-composition.md)