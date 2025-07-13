# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**singleton-service** is a Python framework for building singleton services with dependency management. Services inherit from `BaseService`, cannot be instantiated, and use class methods exclusively.

## Architecture

### Core Design

1. **Singleton Pattern**: Services inherit from `BaseService` which prevents instantiation via `__new__`
2. **Dependency Declaration**: `@requires` decorator declares dependencies between services
3. **Lazy Initialization**: `@guarded` decorator ensures services initialize on first use
4. **Automatic Ordering**: Dependencies resolved via topological sort in `_get_initialization_order()`

### Key Methods in BaseService

- `initialize()`: Override to set up service resources
- `ping()`: Override for health checks (returns bool)
- `_initialize_impl()`: Internal method that calls initialize() then ping()
- `_raise_on_circular_dependencies()`: DFS-based circular dependency detection
- `_get_initialization_order()`: Topological sort for dependency resolution

### Decorators

- `@requires(*services)`: Sets `_dependencies` on the class
- `@guarded`: Wraps methods to ensure initialization before execution
  - Calls `_get_initialization_order()` to determine order
  - Initializes all dependencies via `_initialize_impl()`
  - Prevents calling guarded methods from within `initialize()`

### Service Pattern

```python
from singleton_service import BaseService, requires, guarded
from typing import ClassVar

@requires(OtherService)
class MyService(BaseService):
    _data: ClassVar[Optional[Any]] = None
    
    @classmethod
    def initialize(cls) -> None:
        # Set up resources
        cls._data = expensive_setup()
    
    @classmethod
    def ping(cls) -> bool:
        # Return True if healthy
        return cls._data is not None
    
    @classmethod
    @guarded
    def do_something(cls) -> Any:
        # Business logic - initialization guaranteed
        return cls._data
```

## Important Implementation Details

- Services track initialization state in `_initialized` class variable
- Dependencies stored in `_dependencies` set
- Circular dependencies detected and raise `CircularDependencyError`
- Self-dependency (calling guarded method from initialize) raises `SelfDependencyError`
- Failed initialization raises `ServiceInitializationError`
- All service state must be in class variables
- Never instantiate services - only use class methods