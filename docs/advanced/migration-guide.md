# Migration Guide

This guide helps you migrate from other dependency injection frameworks and design patterns to singleton-service. We'll cover common patterns and provide step-by-step migration instructions.

## Migrating from Traditional Singletons

### Classic Singleton Pattern

**Before (Traditional Singleton):**

```python
class DatabaseConnection:
    _instance = None
    _connection = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self._connection = create_connection("postgresql://...")
    
    def execute(self, query):
        return self._connection.execute(query)

# Usage
db = DatabaseConnection()
result = db.execute("SELECT * FROM users")
```

**After (singleton-service):**

```python
from singleton_service import BaseService, guarded

class DatabaseService(BaseService):
    _connection = None
    
    @classmethod
    def initialize(cls) -> None:
        cls._connection = create_connection("postgresql://...")
    
    @classmethod
    def ping(cls) -> bool:
        return cls._connection is not None and cls._connection.is_alive()
    
    @classmethod
    @guarded
    def execute(cls, query: str):
        return cls._connection.execute(query)

# Usage
result = DatabaseService.execute("SELECT * FROM users")
```

### Module-Level Singletons

**Before (Module Singleton):**

```python
# config.py
_config = None

def load_config():
    global _config
    if _config is None:
        _config = parse_config_file("config.yaml")
    return _config

def get_setting(key):
    config = load_config()
    return config.get(key)

# Usage
from config import get_setting
api_key = get_setting("api_key")
```

**After (singleton-service):**

```python
from singleton_service import BaseService, guarded

class ConfigService(BaseService):
    _config: Dict[str, Any] = {}
    
    @classmethod
    def initialize(cls) -> None:
        cls._config = parse_config_file("config.yaml")
    
    @classmethod
    @guarded
    def get_setting(cls, key: str) -> Any:
        return cls._config.get(key)

# Usage
api_key = ConfigService.get_setting("api_key")
```

## Migrating from Dependency Injection Frameworks

### From Python's dependency-injector

**Before (dependency-injector):**

```python
from dependency_injector import containers, providers

class Database:
    def __init__(self, connection_string):
        self.connection = create_connection(connection_string)

class UserRepository:
    def __init__(self, database):
        self.database = database
    
    def get_user(self, user_id):
        return self.database.query(f"SELECT * FROM users WHERE id = {user_id}")

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    
    database = providers.Singleton(
        Database,
        connection_string=config.database.connection_string
    )
    
    user_repository = providers.Factory(
        UserRepository,
        database=database
    )

# Usage
container = Container()
container.config.database.connection_string.from_env("DATABASE_URL")
user_repo = container.user_repository()
user = user_repo.get_user(123)
```

**After (singleton-service):**

```python
from singleton_service import BaseService, requires, guarded

class DatabaseService(BaseService):
    _connection = None
    
    @classmethod
    def initialize(cls) -> None:
        connection_string = os.getenv("DATABASE_URL")
        cls._connection = create_connection(connection_string)
    
    @classmethod
    @guarded
    def query(cls, sql: str):
        return cls._connection.execute(sql)

@requires(DatabaseService)
class UserService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        pass  # No initialization needed
    
    @classmethod
    @guarded
    def get_user(cls, user_id: int):
        return DatabaseService.query(f"SELECT * FROM users WHERE id = {user_id}")

# Usage
user = UserService.get_user(123)
```

### From Flask Extensions

**Before (Flask-SQLAlchemy):**

```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://...'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)

@app.route('/user/<int:user_id>')
def get_user(user_id):
    user = User.query.get(user_id)
    return {"username": user.username}
```

**After (singleton-service with Flask):**

```python
from flask import Flask
from singleton_service import BaseService, requires, guarded
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class DatabaseService(BaseService):
    _engine = None
    _session_factory = None
    
    @classmethod
    def initialize(cls) -> None:
        cls._engine = create_engine('postgresql://...')
        cls._session_factory = sessionmaker(bind=cls._engine)
    
    @classmethod
    @guarded
    def get_session(cls):
        return cls._session_factory()

@requires(DatabaseService)
class UserService(BaseService):
    @classmethod
    @guarded
    def get_user(cls, user_id: int):
        with DatabaseService.get_session() as session:
            user = session.query(User).get(user_id)
            return {"username": user.username} if user else None

app = Flask(__name__)

@app.route('/user/<int:user_id>')
def get_user(user_id):
    return UserService.get_user(user_id) or ("Not found", 404)
```

## Migrating from Factory Patterns

### Simple Factory

**Before (Factory Pattern):**

```python
class LoggerFactory:
    _loggers = {}
    
    @staticmethod
    def get_logger(name):
        if name not in LoggerFactory._loggers:
            logger = logging.getLogger(name)
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            LoggerFactory._loggers[name] = logger
        return LoggerFactory._loggers[name]

# Usage
logger = LoggerFactory.get_logger("myapp.module1")
logger.info("Hello")
```

**After (singleton-service):**

```python
from singleton_service import BaseService, guarded

class LoggingService(BaseService):
    _loggers: Dict[str, logging.Logger] = {}
    _default_formatter = None
    
    @classmethod
    def initialize(cls) -> None:
        cls._default_formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
    
    @classmethod
    @guarded
    def get_logger(cls, name: str) -> logging.Logger:
        if name not in cls._loggers:
            logger = logging.getLogger(name)
            handler = logging.StreamHandler()
            handler.setFormatter(cls._default_formatter)
            logger.addHandler(handler)
            cls._loggers[name] = logger
        return cls._loggers[name]

# Usage
logger = LoggingService.get_logger("myapp.module1")
logger.info("Hello")
```

### Abstract Factory

**Before (Abstract Factory):**

```python
from abc import ABC, abstractmethod

class StorageFactory(ABC):
    @abstractmethod
    def create_storage(self):
        pass

class S3StorageFactory(StorageFactory):
    def create_storage(self):
        return S3Storage(bucket="my-bucket")

class LocalStorageFactory(StorageFactory):
    def create_storage(self):
        return LocalStorage(path="/tmp/storage")

# Configuration-based selection
def get_storage_factory(config):
    if config["storage_type"] == "s3":
        return S3StorageFactory()
    else:
        return LocalStorageFactory()

# Usage
factory = get_storage_factory({"storage_type": "s3"})
storage = factory.create_storage()
```

**After (singleton-service):**

```python
from singleton_service import BaseService, requires, guarded

class ConfigService(BaseService):
    _config = {}
    
    @classmethod
    def initialize(cls) -> None:
        cls._config = load_config()
    
    @classmethod
    @guarded
    def get(cls, key: str) -> Any:
        return cls._config.get(key)

@requires(ConfigService)
class StorageService(BaseService):
    _storage = None
    
    @classmethod
    def initialize(cls) -> None:
        storage_type = ConfigService.get("storage_type")
        
        if storage_type == "s3":
            cls._storage = S3Storage(bucket="my-bucket")
        else:
            cls._storage = LocalStorage(path="/tmp/storage")
    
    @classmethod
    @guarded
    def save_file(cls, name: str, content: bytes) -> None:
        cls._storage.save(name, content)

# Usage
StorageService.save_file("data.txt", b"content")
```

## Migrating from Service Locator Pattern

**Before (Service Locator):**

```python
class ServiceLocator:
    _services = {}
    
    @classmethod
    def register(cls, name, service):
        cls._services[name] = service
    
    @classmethod
    def get(cls, name):
        if name not in cls._services:
            raise KeyError(f"Service {name} not found")
        return cls._services[name]

# Registration
ServiceLocator.register("database", DatabaseConnection())
ServiceLocator.register("cache", RedisCache())
ServiceLocator.register("email", EmailService())

# Usage
db = ServiceLocator.get("database")
cache = ServiceLocator.get("cache")
```

**After (singleton-service):**

```python
from singleton_service import BaseService, requires, guarded

class DatabaseService(BaseService):
    # Implementation...
    pass

class CacheService(BaseService):
    # Implementation...
    pass

@requires(DatabaseService, CacheService)
class EmailService(BaseService):
    @classmethod
    @guarded
    def send_email(cls, to: str, subject: str, body: str) -> None:
        # Can directly use DatabaseService and CacheService
        user = DatabaseService.get_user_by_email(to)
        CacheService.set(f"email_sent:{to}", True)
        # Send email...

# Usage - no registration needed
EmailService.send_email("user@example.com", "Hello", "Message")
```

## Migration Strategies

### 1. Incremental Migration

Start by migrating leaf services (those with no dependencies) and work your way up:

```python
# Phase 1: Migrate configuration service
class ConfigService(BaseService):
    # No dependencies, easy to migrate first
    pass

# Phase 2: Migrate services that only depend on ConfigService
@requires(ConfigService)
class LoggingService(BaseService):
    pass

# Phase 3: Continue up the dependency tree
@requires(ConfigService, LoggingService)
class ApplicationService(BaseService):
    pass
```

### 2. Wrapper Strategy

Create singleton-service wrappers around existing code:

```python
# Existing code
class LegacyDatabase:
    def __init__(self, connection_string):
        self.conn = create_connection(connection_string)
    
    def query(self, sql):
        return self.conn.execute(sql)

# Wrapper service
class DatabaseService(BaseService):
    _legacy_db = None
    
    @classmethod
    def initialize(cls) -> None:
        # Wrap existing implementation
        cls._legacy_db = LegacyDatabase("postgresql://...")
    
    @classmethod
    @guarded
    def query(cls, sql: str):
        return cls._legacy_db.query(sql)
```

### 3. Parallel Run Strategy

Run both systems in parallel during migration:

```python
class HybridService(BaseService):
    _use_legacy = True
    
    @classmethod
    def initialize(cls) -> None:
        # Initialize both systems
        cls._new_implementation = NewImplementation()
        cls._legacy_implementation = LegacyImplementation()
    
    @classmethod
    @guarded
    def process(cls, data: Any) -> Any:
        if cls._use_legacy:
            return cls._legacy_implementation.process(data)
        else:
            result = cls._new_implementation.process(data)
            # Optionally compare results during migration
            legacy_result = cls._legacy_implementation.process(data)
            if result != legacy_result:
                logger.warning(f"Result mismatch: new={result}, legacy={legacy_result}")
            return result
```

## Common Migration Challenges

### 1. Instance State

**Challenge:** Existing code stores state in instances.

**Solution:** Convert instance state to class variables:

```python
# Before
class Cache:
    def __init__(self):
        self.data = {}
    
    def get(self, key):
        return self.data.get(key)

# After
class CacheService(BaseService):
    _data: ClassVar[Dict[str, Any]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        cls._data = {}
    
    @classmethod
    @guarded
    def get(cls, key: str) -> Any:
        return cls._data.get(key)
```

### 2. Circular Dependencies

**Challenge:** Existing code has circular dependencies.

**Solution:** Refactor using patterns from the [circular dependencies guide](circular-dependencies.md):

```python
# Before (circular)
class UserService:
    def __init__(self, auth_service):
        self.auth_service = auth_service

class AuthService:
    def __init__(self, user_service):
        self.user_service = user_service

# After (resolved)
class UserDataService(BaseService):
    # Shared data layer
    pass

@requires(UserDataService)
class UserService(BaseService):
    pass

@requires(UserDataService)
class AuthService(BaseService):
    pass
```

### 3. Testing

**Challenge:** Existing tests rely on dependency injection for mocking.

**Solution:** Use service reset patterns:

```python
import pytest

@pytest.fixture
def clean_services():
    """Reset services for testing."""
    # Store original state
    original_initialized = DatabaseService._initialized
    original_connection = DatabaseService._connection
    
    # Reset service
    DatabaseService._initialized = False
    DatabaseService._connection = None
    
    yield
    
    # Restore original state
    DatabaseService._initialized = original_initialized
    DatabaseService._connection = original_connection

def test_with_mock_database(clean_services):
    # Set up mock
    DatabaseService._connection = MockConnection()
    DatabaseService._initialized = True
    
    # Test code that uses DatabaseService
    result = UserService.get_user(123)
    assert result is not None
```

## Migration Checklist

- [ ] **Identify all services and their dependencies**
- [ ] **Create a dependency graph** to plan migration order
- [ ] **Start with leaf services** (no dependencies)
- [ ] **Convert instance state to class variables**
- [ ] **Replace dependency injection with @requires**
- [ ] **Add @guarded to public methods**
- [ ] **Implement initialize() and ping() methods**
- [ ] **Update tests to handle singleton pattern**
- [ ] **Remove factory/locator registration code**
- [ ] **Update application initialization** to remove manual wiring
- [ ] **Test initialization order** is correct
- [ ] **Verify no circular dependencies** exist
- [ ] **Update documentation** to reflect new patterns
- [ ] **Train team on singleton-service patterns**

By following this migration guide, you can successfully transition from other patterns to the singleton-service framework while maintaining application functionality and improving code organization.