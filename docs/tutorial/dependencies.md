# Adding Dependencies

🎯 **Learning Goals**: Learn to declare dependencies between services and understand automatic initialization order.

Now that you understand basic services, let's explore one of **singleton-service**'s most powerful features: automatic dependency management. You'll learn how to make services depend on each other and let the framework handle all the complexity.

## 📚 Understanding Dependencies

### What Are Service Dependencies?

A **dependency** is when one service needs another service to function:

- A `UserService` needs a `DatabaseService` to load user data
- An `EmailService` needs a `ConfigService` for SMTP settings  
- A `PaymentService` needs both `DatabaseService` AND `LoggingService`

### The Old Way vs The New Way

=== "❌ Manual Dependency Management"
    ```python
    # Error-prone, complex initialization order
    class UserService:
        def __init__(self):
            # What if DatabaseService isn't ready yet?
            self.db = DatabaseService()
            self.config = ConfigService()
        
        def get_user(self, user_id):
            # Manual checks everywhere
            if not self.db.is_connected():
                raise RuntimeError("Database not ready!")
            return self.db.fetch_user(user_id)
    
    # Complex setup required
    config = ConfigService()
    config.initialize()
    
    db = DatabaseService(config)
    db.connect()
    
    users = UserService()  # Hope everything is ready!
    ```

=== "✅ Automatic Dependency Management"
    ```python
    # Clean, declarative, automatic
    @requires(DatabaseService, ConfigService)
    class UserService(BaseService):
        @classmethod
        @guarded  # Dependencies guaranteed to be ready
        def get_user(cls, user_id: int) -> User:
            return DatabaseService.fetch_user(user_id)
    
    # Just use it - framework handles everything!
    user = UserService.get_user(123)
    ```

## 💻 Building Dependent Services

Let's build a realistic example with multiple services that depend on each other:

### Step 1: Base Services (No Dependencies)

First, let's create some foundational services:

```python
# config_service.py
import os
from typing import ClassVar, Optional
from singleton_service import BaseService, guarded

class ConfigService(BaseService):
    """Configuration management service."""
    
    _database_url: ClassVar[Optional[str]] = None
    _log_level: ClassVar[str] = "INFO"
    _email_smtp_host: ClassVar[Optional[str]] = None
    _email_smtp_port: ClassVar[int] = 587
    
    @classmethod
    def initialize(cls) -> None:
        """Load configuration from environment."""
        cls._database_url = os.getenv("DATABASE_URL", "sqlite:///app.db")
        cls._log_level = os.getenv("LOG_LEVEL", "INFO")
        cls._email_smtp_host = os.getenv("SMTP_HOST")
        cls._email_smtp_port = int(os.getenv("SMTP_PORT", "587"))
        
        print("⚙️  Configuration service initialized")
    
    @classmethod
    @guarded
    def get_database_url(cls) -> str:
        return cls._database_url
    
    @classmethod
    @guarded
    def get_log_level(cls) -> str:
        return cls._log_level
    
    @classmethod
    @guarded
    def get_smtp_config(cls) -> tuple[Optional[str], int]:
        return cls._email_smtp_host, cls._email_smtp_port
```

```python
# logging_service.py
import logging
from typing import ClassVar
from singleton_service import BaseService, guarded

class LoggingService(BaseService):
    """Centralized logging service."""
    
    _logger: ClassVar[logging.Logger] = None
    
    @classmethod
    def initialize(cls) -> None:
        """Set up logging configuration."""
        cls._logger = logging.getLogger("app")
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        cls._logger.addHandler(handler)
        cls._logger.setLevel(logging.INFO)
        
        print("📝 Logging service initialized")
    
    @classmethod
    def ping(cls) -> bool:
        """Verify logger is set up."""
        return cls._logger is not None
    
    @classmethod
    @guarded
    def info(cls, message: str) -> None:
        """Log an info message."""
        cls._logger.info(message)
    
    @classmethod
    @guarded
    def error(cls, message: str) -> None:
        """Log an error message."""
        cls._logger.error(message)
    
    @classmethod
    @guarded
    def warning(cls, message: str) -> None:
        """Log a warning message."""
        cls._logger.warning(message)
```

### Step 2: Service with Single Dependency

Now let's create a database service that depends on configuration:

```python
# database_service.py
from typing import ClassVar, Optional, Dict, Any
from singleton_service import BaseService, requires, guarded
from config_service import ConfigService

@requires(ConfigService)  # ← Declare dependency
class DatabaseService(BaseService):
    """Database connection and operations service."""
    
    _connection: ClassVar[Optional[Dict[str, Any]]] = None
    _users: ClassVar[Dict[int, Dict[str, Any]]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        """Connect to database using configuration."""
        # ConfigService is guaranteed to be initialized first
        db_url = ConfigService.get_database_url()
        
        # Simulate database connection
        cls._connection = {
            "url": db_url,
            "connected": True,
            "pool_size": 10
        }
        
        # Load some sample data
        cls._users = {
            1: {"id": 1, "name": "Alice", "email": "alice@example.com"},
            2: {"id": 2, "name": "Bob", "email": "bob@example.com"},
            3: {"id": 3, "name": "Charlie", "email": "charlie@example.com"},
        }
        
        print(f"🗄️  Database service initialized (URL: {db_url})")
    
    @classmethod
    def ping(cls) -> bool:
        """Check database connection."""
        return cls._connection is not None and cls._connection["connected"]
    
    @classmethod
    @guarded
    def get_user(cls, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        return cls._users.get(user_id)
    
    @classmethod
    @guarded
    def get_all_users(cls) -> Dict[int, Dict[str, Any]]:
        """Get all users."""
        return cls._users.copy()
    
    @classmethod
    @guarded
    def create_user(cls, name: str, email: str) -> Dict[str, Any]:
        """Create a new user."""
        user_id = max(cls._users.keys()) + 1 if cls._users else 1
        user = {"id": user_id, "name": name, "email": email}
        cls._users[user_id] = user
        return user
```

### Step 3: Service with Multiple Dependencies

Let's create a user service that depends on both database and logging:

```python
# user_service.py
from typing import Optional, Dict, Any, List
from singleton_service import BaseService, requires, guarded
from database_service import DatabaseService
from logging_service import LoggingService

@requires(DatabaseService, LoggingService)  # ← Multiple dependencies
class UserService(BaseService):
    """High-level user operations with logging."""
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize user service."""
        # Both DatabaseService and LoggingService are guaranteed to be ready
        LoggingService.info("User service initializing...")
        user_count = len(DatabaseService.get_all_users())
        LoggingService.info(f"Found {user_count} existing users")
        print("👥 User service initialized")
    
    @classmethod
    @guarded
    def get_user_by_id(cls, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user with logging."""
        LoggingService.info(f"Fetching user {user_id}")
        user = DatabaseService.get_user(user_id)
        
        if user:
            LoggingService.info(f"User {user_id} found: {user['name']}")
        else:
            LoggingService.warning(f"User {user_id} not found")
        
        return user
    
    @classmethod
    @guarded
    def create_user(cls, name: str, email: str) -> Dict[str, Any]:
        """Create user with logging."""
        LoggingService.info(f"Creating user: {name} ({email})")
        user = DatabaseService.create_user(name, email)
        LoggingService.info(f"User created with ID {user['id']}")
        return user
    
    @classmethod
    @guarded
    def get_all_users(cls) -> List[Dict[str, Any]]:
        """Get all users with logging."""
        users = list(DatabaseService.get_all_users().values())
        LoggingService.info(f"Retrieved {len(users)} users")
        return users
```

### Step 4: Complex Dependencies

Finally, let's add an email service that depends on both config and logging:

```python
# email_service.py
from typing import ClassVar, Optional, Dict, Any
from singleton_service import BaseService, requires, guarded
from config_service import ConfigService
from logging_service import LoggingService

@requires(ConfigService, LoggingService)
class EmailService(BaseService):
    """Email sending service with SMTP configuration."""
    
    _smtp_config: ClassVar[Optional[Dict[str, Any]]] = None
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize email service with SMTP configuration."""
        host, port = ConfigService.get_smtp_config()
        
        cls._smtp_config = {
            "host": host,
            "port": port,
            "connected": host is not None
        }
        
        LoggingService.info(f"Email service initialized (SMTP: {host}:{port})")
        print("📧 Email service initialized")
    
    @classmethod
    def ping(cls) -> bool:
        """Check if email service is configured."""
        return cls._smtp_config is not None
    
    @classmethod
    @guarded
    def send_email(cls, to: str, subject: str, body: str) -> bool:
        """Send an email (simulated)."""
        if not cls._smtp_config["connected"]:
            LoggingService.error("Cannot send email: SMTP not configured")
            return False
        
        # Simulate sending email
        LoggingService.info(f"Sending email to {to}: {subject}")
        print(f"📧 Email sent to {to}: {subject}")
        return True
```

### Step 5: Use the Complete System

```python
# app.py
import os
from user_service import UserService
from email_service import EmailService

# Set up some configuration
os.environ["DATABASE_URL"] = "postgresql://localhost/myapp"
os.environ["SMTP_HOST"] = "smtp.gmail.com"
os.environ["LOG_LEVEL"] = "INFO"

def main():
    print("🚀 Starting application with complex dependencies...\n")
    
    # Just use the services - framework handles initialization order!
    # Order will be: ConfigService → LoggingService → DatabaseService → UserService
    
    # Get existing users
    users = UserService.get_all_users()
    print(f"\n👥 Found {len(users)} users:")
    for user in users:
        print(f"   - {user['name']} ({user['email']})")
    
    # Create a new user
    print(f"\n➕ Creating new user...")
    new_user = UserService.create_user("Diana", "diana@example.com")
    
    # Send welcome email
    print(f"\n📧 Sending welcome email...")
    email_sent = EmailService.send_email(
        to=new_user["email"],
        subject="Welcome!",
        body=f"Welcome to our app, {new_user['name']}!"
    )
    
    if email_sent:
        print("✅ Welcome email sent successfully")
    else:
        print("❌ Failed to send welcome email")

if __name__ == "__main__":
    main()
```

Run it:

```bash
python app.py
```

Expected output:
```
🚀 Starting application with complex dependencies...

⚙️  Configuration service initialized
📝 Logging service initialized
🗄️  Database service initialized (URL: postgresql://localhost/myapp)
2024-01-15 10:30:45,123 - app - INFO - User service initializing...
2024-01-15 10:30:45,124 - app - INFO - Found 3 existing users
👥 User service initialized
📧 Email service initialized
2024-01-15 10:30:45,125 - app - INFO - Email service initialized (SMTP: smtp.gmail.com:587)

2024-01-15 10:30:45,126 - app - INFO - Retrieved 3 users
👥 Found 3 users:
   - Alice (alice@example.com)
   - Bob (bob@example.com)
   - Charlie (charlie@example.com)

➕ Creating new user...
2024-01-15 10:30:45,127 - app - INFO - Creating user: Diana (diana@example.com)
2024-01-15 10:30:45,128 - app - INFO - User created with ID 4

📧 Sending welcome email...
2024-01-15 10:30:45,129 - app - INFO - Sending email to diana@example.com: Welcome!
📧 Email sent to diana@example.com: Welcome!
✅ Welcome email sent successfully
```

## 🔍 Deep Dive: How Dependencies Work

### 1. **Dependency Declaration**

```python
@requires(DatabaseService, LoggingService)  # ← Order doesn't matter
class UserService(BaseService):
    pass
```

The `@requires` decorator:
- Stores dependencies in the `_dependencies` class attribute
- Order in the decorator doesn't matter - framework figures out the right order
- Can list any number of dependencies
- Dependencies can have their own dependencies (transitive dependencies)

### 2. **Initialization Order Resolution**

When you first call a `@guarded` method, the framework:

1. **Builds dependency graph**: Maps all services and their dependencies
2. **Detects circular dependencies**: Raises `CircularDependencyError` if found
3. **Calculates initialization order**: Uses topological sort algorithm
4. **Initializes in order**: Ensures dependencies are ready before dependents

For our example, the order is:
```
ConfigService (no dependencies)
    ↓
LoggingService (no dependencies) 
    ↓
DatabaseService (requires ConfigService)
    ↓
UserService (requires DatabaseService + LoggingService)
```

### 3. **Transitive Dependencies**

Dependencies are recursive - if A depends on B, and B depends on C, then A transitively depends on C:

```python
@requires(DatabaseService)  # DatabaseService requires ConfigService
class UserService(BaseService):
    # UserService transitively depends on ConfigService too!
    pass
```

The framework automatically handles this - `ConfigService` will be initialized before `UserService`.

## 🔧 Advanced Dependency Patterns

### Optional Dependencies

Sometimes you want a dependency that might not exist:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from optional_service import OptionalService

class MyService(BaseService):
    @classmethod
    @guarded
    def do_something(cls) -> None:
        # Check if optional service is available
        try:
            from optional_service import OptionalService
            OptionalService.optional_operation()
        except ImportError:
            print("Optional service not available")
```

### Conditional Dependencies

You can conditionally require services based on configuration:

```python
# This requires more advanced patterns - see Advanced Topics
def get_dependencies():
    deps = [ConfigService]
    if os.getenv("ENABLE_CACHE") == "true":
        from cache_service import CacheService
        deps.append(CacheService)
    return deps

# Apply dependencies dynamically (advanced pattern)
```

### Service Groups

Organize related services:

```python
# Infrastructure services
@requires()
class ConfigService(BaseService): pass

@requires()
class LoggingService(BaseService): pass

@requires(ConfigService)
class DatabaseService(BaseService): pass

# Business services (depend on infrastructure)
@requires(DatabaseService, LoggingService)
class UserService(BaseService): pass

@requires(DatabaseService, LoggingService)
class OrderService(BaseService): pass

# Application services (depend on business services)
@requires(UserService, OrderService)
class CheckoutService(BaseService): pass
```

## ⚠️ Common Mistakes

### ❌ Circular Dependencies

```python
@requires(ServiceB)
class ServiceA(BaseService):
    pass

@requires(ServiceA)  # ❌ Creates a cycle!
class ServiceB(BaseService):
    pass

# This will raise CircularDependencyError
```

**Solution**: Restructure to remove the cycle:
```python
# Option 1: Remove one dependency
@requires(ServiceB)
class ServiceA(BaseService):
    pass

class ServiceB(BaseService):  # ✅ No dependency on A
    pass

# Option 2: Create a common dependency
@requires(CommonService)
class ServiceA(BaseService):
    pass

@requires(CommonService)
class ServiceB(BaseService):
    pass
```

### ❌ Wrong Dependency Types

```python
@requires("DatabaseService")  # ❌ String, not class
class UserService(BaseService):
    pass

@requires(42)  # ❌ Not a service class
class UserService(BaseService):
    pass
```

### ❌ Missing Dependencies

```python
class UserService(BaseService):  # ❌ Missing @requires
    @classmethod
    @guarded
    def get_user(cls, user_id: int):
        # This will fail if DatabaseService isn't initialized!
        return DatabaseService.get_user(user_id)
```

### ❌ Self Dependencies

```python
@requires(UserService)  # ❌ Can't depend on yourself
class UserService(BaseService):
    pass
```

## ✅ Summary

You've mastered service dependencies! Here's what you learned:

- ✅ **Declare dependencies** with `@requires(ServiceA, ServiceB)`
- ✅ **Automatic initialization order** - framework figures it out
- ✅ **Transitive dependencies** - dependencies of dependencies work automatically
- ✅ **Multiple dependencies** - services can depend on many others
- ✅ **Clear error messages** - circular dependencies are caught early

### Key Takeaways

1. **Use @requires to declare dependencies** - Order in decorator doesn't matter
2. **Framework handles initialization order** - Uses topological sort algorithm
3. **Dependencies are transitive** - A → B → C means A depends on C too
4. **Circular dependencies are forbidden** - Framework detects and prevents them
5. **@guarded ensures dependencies are ready** - Always use it for business logic

## 🚀 Next Steps

Ready to understand how initialization timing works?

**[Initialization Order →](initialization-order.md)**

In the next tutorial, you'll learn exactly when and how services initialize, and how to visualize complex dependency graphs.

---

**Tutorial Progress**: 2/6 complete ✅✅  
**Previous**: [Your First Service](first-service.md) | **Next**: [Initialization Order](initialization-order.md)  
**Estimated time**: 20 minutes ⏱️