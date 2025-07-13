# Circular Dependencies

Circular dependencies occur when two or more services depend on each other, creating a loop in the dependency graph. The singleton-service framework provides built-in detection and prevention mechanisms to help you avoid these issues.

## Understanding Circular Dependencies

### What Are Circular Dependencies?

A circular dependency happens when:

- Service A depends on Service B
- Service B depends on Service A (direct circular dependency)
- Or when Service A → Service B → Service C → Service A (indirect circular dependency)

### Why Are They Problematic?

Circular dependencies can cause:

- **Infinite initialization loops** - Services try to initialize each other forever
- **Stack overflow errors** - Recursive calls exhaust the call stack
- **Unpredictable behavior** - Undefined initialization order
- **Difficult debugging** - Hard to trace the source of the problem

## Built-in Detection

The framework automatically detects circular dependencies using depth-first search (DFS) during initialization order calculation.

### CircularDependencyError

When a circular dependency is detected, the framework raises a `CircularDependencyError`:

```python
from singleton_service import BaseService, requires
from singleton_service.exceptions import CircularDependencyError

@requires(ServiceB)
class ServiceA(BaseService):
    @classmethod
    def initialize(cls) -> None:
        print("ServiceA initializing")

@requires(ServiceA)  # This creates a circular dependency
class ServiceB(BaseService):
    @classmethod
    def initialize(cls) -> None:
        print("ServiceB initializing")

# This will raise CircularDependencyError
try:
    ServiceA.some_guarded_method()
except CircularDependencyError as e:
    print(f"Circular dependency detected: {e}")
```

### Error Message Details

The error message includes:

- **Cycle path** - Shows the exact sequence of services in the cycle
- **All services involved** - Lists every service participating in the cycle
- **Detection point** - Where the cycle was discovered

```python
# Example error message:
# CircularDependencyError: Circular dependency detected in services: 
# ServiceA -> ServiceB -> ServiceA
```

## Prevention Strategies

### 1. Dependency Inversion

Instead of services depending on each other directly, introduce an abstraction:

```python
from abc import ABC, abstractmethod
from singleton_service import BaseService, requires

# Define an interface/protocol
class NotificationProtocol(ABC):
    @abstractmethod
    def send_notification(self, message: str) -> None:
        pass

# UserService depends on the protocol, not concrete implementation
@requires()  # No direct dependencies
class UserService(BaseService):
    _notification_service: NotificationProtocol | None = None
    
    @classmethod
    def initialize(cls) -> None:
        # Inject the dependency after initialization
        cls._notification_service = NotificationService
    
    @classmethod
    @guarded
    def create_user(cls, email: str) -> None:
        # Create user logic...
        if cls._notification_service:
            cls._notification_service.send_notification(f"Welcome {email}!")

# NotificationService can now safely depend on UserService for user data
@requires()  # Or depend on a data service instead
class NotificationService(BaseService, NotificationProtocol):
    @classmethod
    def send_notification(cls, message: str) -> None:
        # Send notification logic...
        pass
```

### 2. Event-Driven Architecture

Use events to decouple services:

```python
from typing import Dict, List, Callable
from singleton_service import BaseService, requires

class EventBus(BaseService):
    _listeners: Dict[str, List[Callable]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        cls._listeners = {}
    
    @classmethod
    @guarded
    def emit(cls, event: str, data: dict) -> None:
        for listener in cls._listeners.get(event, []):
            listener(data)
    
    @classmethod
    @guarded
    def listen(cls, event: str, callback: Callable) -> None:
        if event not in cls._listeners:
            cls._listeners[event] = []
        cls._listeners[event].append(callback)

@requires(EventBus)
class UserService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        # Register for events we care about
        EventBus.listen("user_created", cls._on_user_created)
    
    @classmethod
    @guarded
    def create_user(cls, email: str) -> None:
        # Create user...
        EventBus.emit("user_created", {"email": email})
    
    @classmethod
    def _on_user_created(cls, data: dict) -> None:
        print(f"User created: {data['email']}")

@requires(EventBus)
class NotificationService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        # Listen for user events
        EventBus.listen("user_created", cls._send_welcome_email)
    
    @classmethod
    def _send_welcome_email(cls, data: dict) -> None:
        print(f"Sending welcome email to {data['email']}")
```

### 3. Layered Architecture

Organize services into layers where dependencies only flow downward:

```python
# Layer 1: Data/Repository Layer
class DatabaseService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        # Initialize database connection
        pass

# Layer 2: Business Logic Layer
@requires(DatabaseService)
class UserService(BaseService):
    @classmethod
    def create_user(cls, email: str) -> dict:
        # Business logic for user creation
        return {"id": 1, "email": email}

@requires(DatabaseService)
class OrderService(BaseService):
    @classmethod
    def create_order(cls, user_id: int, items: list) -> dict:
        # Business logic for order creation
        return {"id": 1, "user_id": user_id, "items": items}

# Layer 3: Application/Controller Layer
@requires(UserService, OrderService)
class ApplicationService(BaseService):
    @classmethod
    @guarded
    def process_checkout(cls, email: str, items: list) -> dict:
        user = UserService.create_user(email)
        order = OrderService.create_order(user["id"], items)
        return {"user": user, "order": order}
```

## Refactoring Circular Dependencies

### Step 1: Identify the Cycle

Use the error message to understand the dependency path:

```python
# Error: ServiceA -> ServiceB -> ServiceC -> ServiceA
```

### Step 2: Analyze the Relationships

Determine why each service needs the others:

- What specific functionality does each service need?
- Can the dependency be eliminated or reversed?
- Is there shared state that could be extracted?

### Step 3: Apply Refactoring Patterns

Choose the appropriate pattern based on your analysis:

```python
# Original problematic design
@requires(AuthService)
class UserService(BaseService):
    @classmethod
    @guarded
    def authenticate_user(cls, token: str) -> bool:
        return AuthService.validate_token(token)

@requires(UserService)  # Circular dependency!
class AuthService(BaseService):
    @classmethod
    @guarded
    def get_user_permissions(cls, user_id: int) -> list:
        return UserService.get_user_by_id(user_id).permissions

# Refactored: Extract shared data layer
class UserRepository(BaseService):
    @classmethod
    @guarded
    def get_user_by_id(cls, user_id: int) -> dict:
        # Database access logic
        return {"id": user_id, "permissions": ["read", "write"]}

@requires(UserRepository)
class UserService(BaseService):
    @classmethod
    @guarded
    def get_user_permissions(cls, user_id: int) -> list:
        user = UserRepository.get_user_by_id(user_id)
        return user["permissions"]

@requires(UserRepository)
class AuthService(BaseService):
    @classmethod
    @guarded
    def validate_token(cls, token: str) -> dict:
        # Token validation logic
        user_id = cls._extract_user_id_from_token(token)
        return UserRepository.get_user_by_id(user_id)
```

## Testing for Circular Dependencies

### Unit Testing

Test each service in isolation:

```python
import pytest
from singleton_service.exceptions import CircularDependencyError

def test_no_circular_dependencies():
    """Test that our service graph has no circular dependencies."""
    try:
        # Try to initialize all services
        MyService.some_method()
        assert True, "No circular dependencies detected"
    except CircularDependencyError:
        pytest.fail("Circular dependency detected in service graph")
```

### Dependency Graph Visualization

Create a tool to visualize your service dependencies:

```python
def print_dependency_graph():
    """Print the dependency graph for debugging."""
    services = [UserService, AuthService, DatabaseService]
    
    for service in services:
        deps = getattr(service, '_dependencies', set())
        dep_names = [dep.__name__ for dep in deps]
        print(f"{service.__name__} -> {dep_names}")

# Output:
# UserService -> ['DatabaseService']
# AuthService -> ['DatabaseService']
# DatabaseService -> []
```

## Best Practices

1. **Design dependencies top-down** - Start with high-level services and work down
2. **Use interfaces/protocols** - Depend on abstractions, not concrete implementations
3. **Prefer composition over inheritance** - Avoid complex inheritance hierarchies
4. **Keep services focused** - Single responsibility principle reduces coupling
5. **Use events for loose coupling** - Decouple services with event-driven patterns
6. **Test dependency graphs** - Regularly verify no circular dependencies exist
7. **Document service relationships** - Maintain clear documentation of dependencies

## Common Patterns That Cause Cycles

### Mutual Authentication

```python
# AVOID: Services authenticating each other
@requires(ServiceB)
class ServiceA(BaseService):
    @classmethod
    @guarded
    def process(cls) -> None:
        if ServiceB.verify_caller("ServiceA"):
            # Process logic
            pass

@requires(ServiceA)  # Circular!
class ServiceB(BaseService):
    @classmethod
    @guarded
    def verify_caller(cls, caller: str) -> bool:
        return ServiceA.is_authorized(caller)
```

**Solution**: Use a dedicated authentication service or token-based auth.

### Cross-Service Validation

```python
# AVOID: Services validating each other's data
@requires(OrderService)
class UserService(BaseService):
    @classmethod
    @guarded
    def delete_user(cls, user_id: int) -> None:
        if not OrderService.has_pending_orders(user_id):
            # Delete user
            pass

@requires(UserService)  # Circular!
class OrderService(BaseService):
    @classmethod
    @guarded
    def create_order(cls, user_id: int) -> None:
        if UserService.user_exists(user_id):
            # Create order
            pass
```

**Solution**: Extract validation into a separate service or use data constraints.

By following these patterns and practices, you can build complex service architectures while avoiding the pitfalls of circular dependencies.