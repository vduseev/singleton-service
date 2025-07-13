# Debugging Services

Debugging singleton services requires understanding the initialization flow, dependency resolution, and error handling mechanisms. This guide provides techniques and tools for effective debugging.

## Common Issues and Solutions

### 1. Service Not Initializing

**Symptoms:**
- Methods failing with "Service not initialized" errors
- `ping()` returning False
- Initialization code not being executed

**Debugging Steps:**

```python
from singleton_service import BaseService, requires, guarded

class DebugService(BaseService):
    _initialized_at: ClassVar[float | None] = None
    
    @classmethod
    def initialize(cls) -> None:
        """Track initialization for debugging."""
        print(f"[DEBUG] {cls.__name__}.initialize() called")
        cls._initialized_at = time.time()
        
        # Add debug logging
        import traceback
        print(f"[DEBUG] Called from: {traceback.format_stack()[-2].strip()}")
    
    @classmethod
    def ping(cls) -> bool:
        """Enhanced ping for debugging."""
        result = cls._initialized_at is not None
        print(f"[DEBUG] {cls.__name__}.ping() = {result}")
        if not result:
            print(f"[DEBUG] _initialized_at = {cls._initialized_at}")
        return result
    
    @classmethod
    @guarded
    def test_method(cls) -> str:
        """Test method with debugging."""
        print(f"[DEBUG] {cls.__name__}.test_method() executed")
        return "success"

# Debug initialization
print("[DEBUG] Before calling test_method")
result = DebugService.test_method()
print(f"[DEBUG] Result: {result}")
```

### 2. Dependency Resolution Issues

**Debugging Dependency Order:**

```python
from typing import Set, Type
from singleton_service import BaseService, requires

def debug_dependencies(service: Type[BaseService], visited: Set[Type] = None) -> None:
    """Recursively print service dependencies."""
    if visited is None:
        visited = set()
    
    if service in visited:
        print(f"  [CIRCULAR] {service.__name__} (already visited)")
        return
    
    visited.add(service)
    deps = getattr(service, '_dependencies', set())
    
    print(f"{service.__name__} depends on: {[d.__name__ for d in deps]}")
    
    for dep in deps:
        print(f"  -> ", end="")
        debug_dependencies(dep, visited)

# Visualize dependency tree
print("[DEBUG] Dependency Tree:")
debug_dependencies(MyComplexService)

# Check initialization order
def debug_initialization_order(service: Type[BaseService]) -> None:
    """Debug the initialization order calculation."""
    try:
        order = service._get_initialization_order()
        print(f"[DEBUG] Initialization order for {service.__name__}:")
        for i, svc in enumerate(order):
            deps = getattr(svc, '_dependencies', set())
            dep_names = [d.__name__ for d in deps]
            print(f"  {i+1}. {svc.__name__} (deps: {dep_names})")
    except Exception as e:
        print(f"[ERROR] Failed to calculate order: {e}")

debug_initialization_order(MyComplexService)
```

### 3. Circular Dependency Detection

**Enhanced Circular Dependency Debugging:**

```python
from singleton_service.exceptions import CircularDependencyError

class CircularDebugMixin:
    """Mixin for debugging circular dependencies."""
    
    @classmethod
    def _raise_on_circular_dependencies(cls) -> None:
        """Enhanced circular dependency detection with path tracking."""
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(service: Type['BaseService']) -> bool:
            visited.add(service)
            rec_stack.add(service)
            path.append(service.__name__)
            
            for dep in getattr(service, '_dependencies', set()):
                if dep not in visited:
                    if dfs(dep):
                        return True
                elif dep in rec_stack:
                    # Found cycle
                    cycle_start = path.index(dep.__name__)
                    cycle_path = path[cycle_start:] + [dep.__name__]
                    print(f"[DEBUG] Circular dependency detected:")
                    print(f"[DEBUG] Full path: {' -> '.join(path)}")
                    print(f"[DEBUG] Cycle: {' -> '.join(cycle_path)}")
                    return True
            
            path.pop()
            rec_stack.remove(service)
            return False
        
        if dfs(cls):
            raise CircularDependencyError(
                f"Circular dependency detected starting from {cls.__name__}"
            )

# Use the mixin for debugging
class DebugServiceWithMixin(BaseService, CircularDebugMixin):
    pass
```

## Logging and Tracing

### 1. Service Activity Logging

```python
import logging
from functools import wraps
from typing import Any, Callable
from singleton_service import BaseService, guarded

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class LoggedService(BaseService):
    """Base service with comprehensive logging."""
    
    @classmethod
    def _get_logger(cls) -> logging.Logger:
        """Get logger for this service."""
        return logging.getLogger(f"singleton_service.{cls.__name__}")
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize with logging."""
        logger = cls._get_logger()
        logger.info(f"Initializing {cls.__name__}")
        
        try:
            # Call the actual initialization
            if hasattr(super(), 'initialize'):
                super().initialize()
            logger.info(f"Successfully initialized {cls.__name__}")
        except Exception as e:
            logger.error(f"Failed to initialize {cls.__name__}: {e}", exc_info=True)
            raise
    
    @classmethod
    def log_method(cls, func: Callable) -> Callable:
        """Decorator to log method calls."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = cls._get_logger()
            method_name = func.__name__
            
            # Log method entry
            logger.debug(f"Entering {method_name} with args={args[1:]}, kwargs={kwargs}")
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log successful execution
                logger.debug(f"Exiting {method_name} after {duration:.3f}s with result={result}")
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Error in {method_name} after {duration:.3f}s: {e}", exc_info=True)
                raise
        
        return wrapper

# Example usage
class MyLoggedService(LoggedService):
    _data: ClassVar[Dict[str, Any]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        super().initialize()
        cls._data = {"initialized": True}
    
    @classmethod
    @guarded
    @LoggedService.log_method
    def process_data(cls, input_data: str) -> str:
        """Process data with automatic logging."""
        return f"Processed: {input_data}"
```

### 2. Tracing Service Calls

```python
import sys
from contextlib import contextmanager
from typing import List, Tuple
from singleton_service import BaseService, guarded

class ServiceTracer(BaseService):
    """Trace all service method calls."""
    
    _trace_enabled: ClassVar[bool] = False
    _trace_stack: ClassVar[List[Tuple[str, float]]] = []
    _trace_results: ClassVar[List[Dict[str, Any]]] = []
    
    @classmethod
    def initialize(cls) -> None:
        cls._trace_stack = []
        cls._trace_results = []
    
    @classmethod
    @contextmanager
    def trace(cls):
        """Context manager to enable tracing."""
        cls._trace_enabled = True
        cls._trace_stack = []
        cls._trace_results = []
        
        # Install trace function
        original_trace = sys.gettrace()
        sys.settrace(cls._trace_function)
        
        try:
            yield cls
        finally:
            sys.settrace(original_trace)
            cls._trace_enabled = False
    
    @classmethod
    def _trace_function(cls, frame, event, arg):
        """Trace function for sys.settrace."""
        if not cls._trace_enabled:
            return None
        
        # Check if this is a service method
        if event == 'call':
            func_name = frame.f_code.co_name
            if 'BaseService' in str(frame.f_locals.get('cls', '')):
                cls._trace_stack.append((func_name, time.time()))
                
        elif event == 'return':
            if cls._trace_stack:
                func_name, start_time = cls._trace_stack.pop()
                duration = time.time() - start_time
                
                cls._trace_results.append({
                    'function': func_name,
                    'duration': duration,
                    'depth': len(cls._trace_stack),
                    'return_value': str(arg)[:100]  # Truncate long values
                })
        
        return cls._trace_function
    
    @classmethod
    @guarded
    def get_trace_results(cls) -> List[Dict[str, Any]]:
        """Get trace results."""
        return cls._trace_results.copy()
    
    @classmethod
    @guarded
    def print_trace_tree(cls) -> None:
        """Print trace as a tree."""
        for result in cls._trace_results:
            indent = "  " * result['depth']
            duration_ms = result['duration'] * 1000
            print(f"{indent}{result['function']} ({duration_ms:.2f}ms)")

# Usage example
with ServiceTracer.trace():
    MyComplexService.complex_operation()
    
ServiceTracer.print_trace_tree()
```

## Debugging Tools

### 1. Service Inspector

```python
from typing import Type, Dict, Any, List
from singleton_service import BaseService

class ServiceInspector(BaseService):
    """Inspect service state and configuration."""
    
    @classmethod
    def initialize(cls) -> None:
        pass
    
    @classmethod
    @guarded
    def inspect_service(cls, service: Type[BaseService]) -> Dict[str, Any]:
        """Comprehensive service inspection."""
        return {
            "name": service.__name__,
            "initialized": getattr(service, '_initialized', False),
            "dependencies": [dep.__name__ for dep in getattr(service, '_dependencies', set())],
            "methods": cls._get_service_methods(service),
            "class_variables": cls._get_class_variables(service),
            "mro": [c.__name__ for c in service.__mro__],
            "module": service.__module__,
            "file": getattr(service, '__file__', 'Unknown')
        }
    
    @classmethod
    def _get_service_methods(cls, service: Type[BaseService]) -> List[Dict[str, Any]]:
        """Get all service methods with metadata."""
        methods = []
        
        for name in dir(service):
            if name.startswith('_'):
                continue
                
            attr = getattr(service, name)
            if callable(attr) and hasattr(attr, '__func__'):
                is_guarded = hasattr(attr.__func__, '_guarded')
                methods.append({
                    "name": name,
                    "guarded": is_guarded,
                    "doc": (attr.__doc__ or "").strip().split('\n')[0]
                })
        
        return methods
    
    @classmethod
    def _get_class_variables(cls, service: Type[BaseService]) -> Dict[str, Any]:
        """Get class variables (safely)."""
        vars = {}
        
        for name in dir(service):
            if name.startswith('_') and not name.startswith('__'):
                try:
                    value = getattr(service, name)
                    # Only include simple types
                    if isinstance(value, (str, int, float, bool, type(None))):
                        vars[name] = value
                    else:
                        vars[name] = f"<{type(value).__name__}>"
                except Exception:
                    vars[name] = "<Error accessing>"
        
        return vars
    
    @classmethod
    @guarded
    def print_service_tree(cls, service: Type[BaseService], indent: int = 0) -> None:
        """Print service dependency tree."""
        prefix = "  " * indent
        info = cls.inspect_service(service)
        
        status = "✓" if info["initialized"] else "✗"
        print(f"{prefix}{status} {info['name']}")
        
        # Print dependencies recursively
        for dep_name in info["dependencies"]:
            # Find the actual dependency class
            for dep in getattr(service, '_dependencies', set()):
                if dep.__name__ == dep_name:
                    cls.print_service_tree(dep, indent + 1)
                    break
```

### 2. Runtime State Debugger

```python
import json
from typing import Any
from singleton_service import BaseService, guarded

class StateDebugger(BaseService):
    """Debug service state at runtime."""
    
    _snapshots: ClassVar[Dict[str, List[Dict[str, Any]]]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        cls._snapshots = {}
    
    @classmethod
    @guarded
    def capture_state(cls, service: Type[BaseService], label: str = "") -> None:
        """Capture current state of a service."""
        service_name = service.__name__
        
        if service_name not in cls._snapshots:
            cls._snapshots[service_name] = []
        
        # Capture state
        state = {
            "timestamp": time.time(),
            "label": label,
            "initialized": getattr(service, '_initialized', False),
            "class_vars": {}
        }
        
        # Capture class variables
        for attr in dir(service):
            if attr.startswith('_') and not attr.startswith('__'):
                try:
                    value = getattr(service, attr)
                    # Try to serialize to JSON
                    json.dumps(value)
                    state["class_vars"][attr] = value
                except Exception:
                    state["class_vars"][attr] = f"<Non-serializable: {type(value).__name__}>"
        
        cls._snapshots[service_name].append(state)
    
    @classmethod
    @guarded
    def compare_states(cls, service: Type[BaseService], index1: int = -2, index2: int = -1) -> Dict[str, Any]:
        """Compare two state snapshots."""
        service_name = service.__name__
        
        if service_name not in cls._snapshots:
            return {"error": "No snapshots for service"}
        
        snapshots = cls._snapshots[service_name]
        if len(snapshots) < 2:
            return {"error": "Not enough snapshots to compare"}
        
        try:
            state1 = snapshots[index1]
            state2 = snapshots[index2]
        except IndexError:
            return {"error": "Invalid snapshot indices"}
        
        # Find differences
        differences = {
            "time_diff": state2["timestamp"] - state1["timestamp"],
            "label1": state1["label"],
            "label2": state2["label"],
            "changes": {}
        }
        
        # Compare class variables
        all_keys = set(state1["class_vars"].keys()) | set(state2["class_vars"].keys())
        
        for key in all_keys:
            val1 = state1["class_vars"].get(key, "<Not present>")
            val2 = state2["class_vars"].get(key, "<Not present>")
            
            if val1 != val2:
                differences["changes"][key] = {
                    "before": val1,
                    "after": val2
                }
        
        return differences
```

## Error Diagnosis

### 1. Enhanced Error Messages

```python
from singleton_service import BaseService, requires
from singleton_service.exceptions import ServiceInitializationError

class DiagnosticService(BaseService):
    """Service with enhanced error diagnostics."""
    
    @classmethod
    def initialize(cls) -> None:
        try:
            # Initialization logic that might fail
            cls._perform_initialization()
        except Exception as e:
            # Capture detailed context
            import traceback
            
            context = {
                "service": cls.__name__,
                "dependencies": [d.__name__ for d in getattr(cls, '_dependencies', set())],
                "traceback": traceback.format_exc(),
                "locals": {k: str(v)[:100] for k, v in locals().items() if k != 'cls'},
                "timestamp": time.time()
            }
            
            # Log detailed error
            print(f"[ERROR] Service initialization failed: {json.dumps(context, indent=2)}")
            
            # Re-raise with context
            raise ServiceInitializationError(
                f"Failed to initialize {cls.__name__}: {str(e)}\n"
                f"Context: {json.dumps(context, indent=2)}"
            ) from e
```

### 2. Debug Mode

```python
class DebugMode(BaseService):
    """Global debug mode for all services."""
    
    _debug_enabled: ClassVar[bool] = False
    _debug_config: ClassVar[Dict[str, Any]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        cls._debug_config = {
            "log_initialization": True,
            "log_method_calls": True,
            "capture_stack_traces": True,
            "validate_dependencies": True
        }
    
    @classmethod
    @guarded
    def enable(cls, **config) -> None:
        """Enable debug mode with configuration."""
        cls._debug_enabled = True
        cls._debug_config.update(config)
        print(f"[DEBUG] Debug mode enabled with config: {cls._debug_config}")
    
    @classmethod
    @guarded
    def disable(cls) -> None:
        """Disable debug mode."""
        cls._debug_enabled = False
        print("[DEBUG] Debug mode disabled")
    
    @classmethod
    def is_enabled(cls) -> bool:
        """Check if debug mode is enabled."""
        return cls._debug_enabled
    
    @classmethod
    def get_config(cls, key: str, default: Any = None) -> Any:
        """Get debug configuration value."""
        return cls._debug_config.get(key, default) if cls._debug_enabled else default

# Integration with BaseService
class DebugAwareService(BaseService):
    """Service that respects debug mode."""
    
    @classmethod
    def initialize(cls) -> None:
        if DebugMode.is_enabled() and DebugMode.get_config("log_initialization"):
            print(f"[DEBUG] Initializing {cls.__name__}")
            
        # Regular initialization
        super().initialize()
        
        if DebugMode.is_enabled() and DebugMode.get_config("validate_dependencies"):
            cls._validate_dependencies()
    
    @classmethod
    def _validate_dependencies(cls) -> None:
        """Validate all dependencies are initialized."""
        for dep in getattr(cls, '_dependencies', set()):
            if not getattr(dep, '_initialized', False):
                print(f"[WARNING] Dependency {dep.__name__} not initialized for {cls.__name__}")
```

## Best Practices for Debugging

1. **Use descriptive error messages** - Include context about what the service was trying to do
2. **Add debug logging** - But make it configurable to avoid noise in production
3. **Capture state at failure points** - Store service state when errors occur
4. **Use type hints** - They help catch issues during development
5. **Write reproducible tests** - Isolate issues in test cases
6. **Monitor initialization order** - Log service initialization sequence
7. **Track performance metrics** - Identify slow initializations
8. **Use debugging decorators** - Add debugging functionality without modifying core logic
9. **Implement health checks** - Make ping() methods informative
10. **Document known issues** - Keep track of common problems and solutions

By using these debugging techniques and tools, you can quickly identify and resolve issues in your singleton services.