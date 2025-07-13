# API Reference

This section provides comprehensive API documentation for **singleton-service**, automatically generated from the source code docstrings.

## 📋 API Overview

The **singleton-service** framework consists of several core modules:

### Core Framework
- **[BaseService](base-service.md)** - The foundation class for all singleton services
- **[Decorators](decorators.md)** - Essential decorators for dependency management and method guarding
- **[Exceptions](exceptions.md)** - Framework-specific exception classes
- **[BaseRunnable](base-runnable.md)** - Abstract base for runnable services

## 🔍 Navigation Guide

### By Functionality

**Service Creation**
- [`BaseService`](base-service.md) - Core service class with initialization and lifecycle management
- [`@requires`](decorators.md#requires) - Declare service dependencies
- [`@guarded`](decorators.md#guarded) - Ensure initialization before method execution

**Error Handling**
- [`ServiceError`](exceptions.md#serviceerror) - Base exception for all framework errors
- [`CircularDependencyError`](exceptions.md#circulardependencyerror) - Circular dependency detection
- [`ServiceInitializationError`](exceptions.md#serviceinitializationerror) - Initialization failures

**Advanced Patterns**
- [`BaseRunnable`](base-runnable.md) - For services that need to run continuously
- [`_get_initialization_order`](base-service.md#get-initialization-order) - Dependency resolution algorithm

### By Use Case

**Getting Started**
1. Read [`BaseService`](base-service.md) class documentation
2. Understand [`@requires`](decorators.md#requires) and [`@guarded`](decorators.md#guarded) decorators
3. Learn about [exception handling](exceptions.md)

**Advanced Usage**
1. Explore [`BaseRunnable`](base-runnable.md) for background services
2. Study dependency resolution in [`_get_initialization_order`](base-service.md#get-initialization-order)
3. Understand error scenarios in [exceptions reference](exceptions.md)

**Debugging**
1. Check [exception types](exceptions.md) for error identification
2. Use [`ping()`](base-service.md#ping) methods for health checks
3. Review initialization order with debug logging

## 📚 Quick Reference

### Essential Methods

Every service inherits these core methods from `BaseService`:

```python
class MyService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        """Override to set up service resources."""
        pass
    
    @classmethod  
    def ping(cls) -> bool:
        """Override to verify service health."""
        return True
    
    @classmethod
    @guarded
    def my_method(cls) -> Any:
        """Business logic methods should be guarded."""
        pass
```

### Essential Decorators

```python
from singleton_service import BaseService, requires, guarded

@requires(OtherService)  # Declare dependencies
class MyService(BaseService):
    @classmethod
    @guarded  # Ensure initialization
    def do_work(cls) -> str:
        return "work done"
```

### Common Patterns

**Service with Dependencies:**
```python
@requires(DatabaseService, CacheService)
class UserService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        # Dependencies are already initialized
        cls._user_cache = {}
    
    @classmethod
    @guarded
    def get_user(cls, user_id: int) -> User:
        # Safe to use dependencies here
        return DatabaseService.find_user(user_id)
```

**Error Handling:**
```python
try:
    result = UserService.get_user(123)
except ServiceInitializationError as e:
    # Service failed to initialize
    logger.error(f"Service unavailable: {e}")
except CircularDependencyError as e:
    # Dependency cycle detected
    logger.error(f"Configuration error: {e}")
```

## 🔗 Related Documentation

- **[Tutorial](../tutorial/)** - Step-by-step learning guide
- **[Examples](../examples/)** - Real-world usage patterns  
- **[Concepts](../concepts/)** - Framework design principles
- **[Best Practices](../concepts/best-practices.md)** - Production guidelines

## 📖 Reading Guide

**For New Users:**
Start with [`BaseService`](base-service.md) to understand the foundation, then read about [`@requires`](decorators.md#requires) and [`@guarded`](decorators.md#guarded) decorators.

**For Framework Contributors:**
Focus on the internal methods in [`BaseService`](base-service.md), especially `_get_initialization_order()` and `_initialize_impl()`.

**For Debugging:**
Check the [exceptions documentation](exceptions.md) first, then use `ping()` methods and logging to diagnose issues.

---

**Tip:** Use your IDE's "Go to Definition" feature while reading this documentation to see the actual implementation alongside the docs.