# Performance Optimization

Understanding and optimizing the performance of your singleton services is crucial for building efficient applications. This guide covers performance characteristics, optimization techniques, and best practices.

## Framework Overhead

### Initialization Performance

The singleton-service framework adds minimal overhead during initialization:

```python
import time
from singleton_service import BaseService, requires, guarded

# Measure initialization time
start_time = time.time()

class PerformanceTestService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        # Simulate some initialization work
        time.sleep(0.001)  # 1ms initialization

# First call triggers initialization
PerformanceTestService.some_guarded_method()
initialization_time = time.time() - start_time

print(f"Initialization took: {initialization_time:.4f} seconds")
# Typical overhead: < 0.001 seconds for dependency resolution
```

### Method Call Overhead

```python
import timeit
from singleton_service import BaseService, guarded

class BenchmarkService(BaseService):
    _data: ClassVar[list] = []
    
    @classmethod
    def initialize(cls) -> None:
        cls._data = list(range(1000))
    
    @classmethod
    @guarded
    def guarded_method(cls) -> int:
        return sum(cls._data)
    
    @classmethod
    def non_guarded_method(cls) -> int:
        return sum(cls._data)

# Initialize service
BenchmarkService.guarded_method()

# Benchmark guarded vs non-guarded
guarded_time = timeit.timeit(
    'BenchmarkService.guarded_method()',
    globals=globals(),
    number=100000
)

non_guarded_time = timeit.timeit(
    'BenchmarkService.non_guarded_method()',
    globals=globals(),
    number=100000
)

print(f"Guarded method: {guarded_time:.4f} seconds")
print(f"Non-guarded method: {non_guarded_time:.4f} seconds")
print(f"Overhead per call: {(guarded_time - non_guarded_time) / 100000 * 1e6:.2f} microseconds")
# Typical overhead: < 1 microsecond per call after initialization
```

## Optimization Techniques

### 1. Lazy Resource Loading

```python
from typing import ClassVar, Dict, Any
from singleton_service import BaseService, guarded

class OptimizedDataService(BaseService):
    _config: ClassVar[Dict[str, Any] | None] = None
    _heavy_data: ClassVar[Dict[str, Any] | None] = None
    _data_loaded: ClassVar[bool] = False
    
    @classmethod
    def initialize(cls) -> None:
        """Load only essential configuration."""
        # Load minimal config during initialization
        cls._config = {"api_key": "secret", "endpoint": "https://api.example.com"}
        # Don't load heavy data until needed
    
    @classmethod
    def _ensure_data_loaded(cls) -> None:
        """Lazy load heavy data on first use."""
        if not cls._data_loaded:
            # Simulate loading large dataset
            cls._heavy_data = {f"item_{i}": i * 2 for i in range(10000)}
            cls._data_loaded = True
    
    @classmethod
    @guarded
    def get_item(cls, key: str) -> Any:
        """Get item with lazy loading."""
        cls._ensure_data_loaded()
        return cls._heavy_data.get(key)
    
    @classmethod
    @guarded
    def get_config(cls, key: str) -> Any:
        """Get config without loading heavy data."""
        # This method doesn't trigger heavy data loading
        return cls._config.get(key)
```

### 2. Caching and Memoization

```python
import functools
import time
from typing import ClassVar, Dict, Any, Tuple
from singleton_service import BaseService, guarded

class CachedComputeService(BaseService):
    _cache: ClassVar[Dict[Tuple, Any]] = {}
    _cache_stats: ClassVar[Dict[str, int]] = {"hits": 0, "misses": 0}
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize cache."""
        cls._cache = {}
        cls._cache_stats = {"hits": 0, "misses": 0}
    
    @classmethod
    @guarded
    def expensive_computation(cls, x: int, y: int) -> int:
        """Cached expensive computation."""
        cache_key = (x, y)
        
        if cache_key in cls._cache:
            cls._cache_stats["hits"] += 1
            return cls._cache[cache_key]
        
        cls._cache_stats["misses"] += 1
        
        # Simulate expensive computation
        time.sleep(0.1)
        result = x ** y
        
        cls._cache[cache_key] = result
        return result
    
    @classmethod
    @guarded
    def get_cache_stats(cls) -> Dict[str, int]:
        """Get cache performance statistics."""
        total = cls._cache_stats["hits"] + cls._cache_stats["misses"]
        if total > 0:
            hit_rate = cls._cache_stats["hits"] / total * 100
            return {
                **cls._cache_stats,
                "hit_rate": f"{hit_rate:.1f}%",
                "cache_size": len(cls._cache)
            }
        return cls._cache_stats
    
    @classmethod
    @guarded
    def clear_cache(cls) -> None:
        """Clear computation cache."""
        cls._cache.clear()
        cls._cache_stats = {"hits": 0, "misses": 0}

# Using functools.lru_cache for method-level caching
class LRUCachedService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        """Initialize service."""
        pass
    
    @classmethod
    @guarded
    @functools.lru_cache(maxsize=128)
    def compute_fibonacci(cls, n: int) -> int:
        """Compute Fibonacci with LRU cache."""
        if n <= 1:
            return n
        return cls.compute_fibonacci(n - 1) + cls.compute_fibonacci(n - 2)
    
    @classmethod
    @guarded
    def get_cache_info(cls) -> Dict[str, Any]:
        """Get LRU cache statistics."""
        info = cls.compute_fibonacci.cache_info()
        return {
            "hits": info.hits,
            "misses": info.misses,
            "maxsize": info.maxsize,
            "currsize": info.currsize
        }
```

### 3. Connection Pooling

```python
import queue
import threading
from typing import ClassVar, Any
from singleton_service import BaseService, guarded

class PooledDatabaseService(BaseService):
    _connection_pool: ClassVar[queue.Queue | None] = None
    _pool_size: ClassVar[int] = 10
    _active_connections: ClassVar[int] = 0
    _pool_lock: ClassVar[threading.Lock | None] = None
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize connection pool."""
        cls._connection_pool = queue.Queue(maxsize=cls._pool_size)
        cls._pool_lock = threading.Lock()
        
        # Pre-create connections
        for i in range(cls._pool_size):
            conn = cls._create_connection(i)
            cls._connection_pool.put(conn)
    
    @classmethod
    def _create_connection(cls, conn_id: int) -> Dict[str, Any]:
        """Create a mock database connection."""
        return {
            "id": conn_id,
            "created_at": time.time(),
            "query_count": 0
        }
    
    @classmethod
    @guarded
    def execute_query(cls, query: str, timeout: float = 5.0) -> Any:
        """Execute query using pooled connection."""
        connection = None
        try:
            # Get connection from pool
            connection = cls._connection_pool.get(timeout=timeout)
            
            with cls._pool_lock:
                cls._active_connections += 1
            
            # Simulate query execution
            connection["query_count"] += 1
            time.sleep(0.01)  # 10ms query
            
            return {"result": f"Executed: {query}", "connection_id": connection["id"]}
            
        except queue.Empty:
            raise TimeoutError("No available connections in pool")
        finally:
            # Return connection to pool
            if connection:
                cls._connection_pool.put(connection)
                with cls._pool_lock:
                    cls._active_connections -= 1
    
    @classmethod
    @guarded
    def get_pool_stats(cls) -> Dict[str, Any]:
        """Get connection pool statistics."""
        return {
            "pool_size": cls._pool_size,
            "available_connections": cls._connection_pool.qsize(),
            "active_connections": cls._active_connections,
            "utilization": f"{(cls._active_connections / cls._pool_size) * 100:.1f}%"
        }
```

### 4. Batch Processing

```python
import asyncio
from typing import ClassVar, List, Dict, Any
from singleton_service import BaseService, guarded

class BatchProcessingService(BaseService):
    _batch_queue: ClassVar[List[Dict[str, Any]]] = []
    _batch_size: ClassVar[int] = 100
    _batch_timeout: ClassVar[float] = 1.0  # seconds
    _last_batch_time: ClassVar[float] = 0
    _processing_lock: ClassVar[threading.Lock | None] = None
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize batch processor."""
        cls._batch_queue = []
        cls._last_batch_time = time.time()
        cls._processing_lock = threading.Lock()
    
    @classmethod
    @guarded
    def add_item(cls, item: Dict[str, Any]) -> None:
        """Add item to batch queue."""
        with cls._processing_lock:
            cls._batch_queue.append(item)
            
            # Process if batch is full or timeout reached
            if (len(cls._batch_queue) >= cls._batch_size or 
                time.time() - cls._last_batch_time >= cls._batch_timeout):
                cls._process_batch()
    
    @classmethod
    def _process_batch(cls) -> None:
        """Process current batch."""
        if not cls._batch_queue:
            return
        
        batch = cls._batch_queue[:]
        cls._batch_queue.clear()
        cls._last_batch_time = time.time()
        
        # Simulate batch processing
        print(f"Processing batch of {len(batch)} items")
        time.sleep(0.01 * len(batch))  # Faster than individual processing
    
    @classmethod
    @guarded
    def flush(cls) -> None:
        """Force process any pending items."""
        with cls._processing_lock:
            cls._process_batch()
```

## Memory Management

### 1. Resource Cleanup

```python
import weakref
import gc
from typing import ClassVar, Set, Any
from singleton_service import BaseService, guarded

class MemoryManagedService(BaseService):
    _resources: ClassVar[Set[weakref.ref]] = set()
    _cache: ClassVar[Dict[str, Any]] = {}
    _cache_size_limit: ClassVar[int] = 1000
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize with memory management."""
        cls._resources = set()
        cls._cache = {}
    
    @classmethod
    @guarded
    def create_resource(cls, name: str) -> Dict[str, Any]:
        """Create a tracked resource."""
        resource = {"name": name, "data": [0] * 1000}  # Some memory usage
        
        # Track resource with weak reference
        cls._resources.add(weakref.ref(resource, cls._on_resource_deleted))
        
        # Add to cache with size limit
        cls._cache[name] = resource
        if len(cls._cache) > cls._cache_size_limit:
            # Remove oldest entries
            oldest_key = next(iter(cls._cache))
            del cls._cache[oldest_key]
        
        return resource
    
    @classmethod
    def _on_resource_deleted(cls, ref: weakref.ref) -> None:
        """Callback when resource is garbage collected."""
        cls._resources.discard(ref)
    
    @classmethod
    @guarded
    def cleanup_resources(cls) -> Dict[str, int]:
        """Force cleanup of unused resources."""
        initial_count = len(cls._resources)
        
        # Remove dead references
        dead_refs = [ref for ref in cls._resources if ref() is None]
        for ref in dead_refs:
            cls._resources.discard(ref)
        
        # Force garbage collection
        gc.collect()
        
        return {
            "initial_resources": initial_count,
            "cleaned_up": len(dead_refs),
            "remaining": len(cls._resources),
            "cache_size": len(cls._cache)
        }
```

### 2. Memory Profiling

```python
import psutil
import os
from typing import ClassVar, Dict, Any
from singleton_service import BaseService, guarded

class MemoryProfilerService(BaseService):
    _baseline_memory: ClassVar[float] = 0
    _process: ClassVar[psutil.Process | None] = None
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize memory profiler."""
        cls._process = psutil.Process(os.getpid())
        cls._baseline_memory = cls._process.memory_info().rss / 1024 / 1024  # MB
    
    @classmethod
    @guarded
    def get_memory_usage(cls) -> Dict[str, Any]:
        """Get current memory usage statistics."""
        memory_info = cls._process.memory_info()
        current_memory = memory_info.rss / 1024 / 1024  # MB
        
        return {
            "current_mb": f"{current_memory:.2f}",
            "baseline_mb": f"{cls._baseline_memory:.2f}",
            "increase_mb": f"{current_memory - cls._baseline_memory:.2f}",
            "percent_increase": f"{((current_memory / cls._baseline_memory) - 1) * 100:.1f}%"
        }
    
    @classmethod
    @guarded
    def profile_operation(cls, operation_name: str, func, *args, **kwargs) -> Dict[str, Any]:
        """Profile memory usage of an operation."""
        gc.collect()  # Clean up before measurement
        
        before = cls._process.memory_info().rss / 1024 / 1024
        start_time = time.time()
        
        result = func(*args, **kwargs)
        
        end_time = time.time()
        after = cls._process.memory_info().rss / 1024 / 1024
        
        return {
            "operation": operation_name,
            "duration_ms": f"{(end_time - start_time) * 1000:.2f}",
            "memory_before_mb": f"{before:.2f}",
            "memory_after_mb": f"{after:.2f}",
            "memory_used_mb": f"{after - before:.2f}",
            "result": result
        }
```

## Performance Best Practices

### 1. Service Design

```python
# GOOD: Minimal initialization, lazy loading
class OptimalService(BaseService):
    _config: ClassVar[Dict[str, Any] | None] = None
    _heavy_data: ClassVar[Any] = None
    
    @classmethod
    def initialize(cls) -> None:
        # Only load essential config
        cls._config = {"setting": "value"}
    
    @classmethod
    def _load_heavy_data(cls) -> None:
        if cls._heavy_data is None:
            cls._heavy_data = expensive_operation()
    
    @classmethod
    @guarded
    def process(cls, item: str) -> Any:
        cls._load_heavy_data()
        return cls._heavy_data.process(item)

# AVOID: Heavy initialization
class SuboptimalService(BaseService):
    _all_data: ClassVar[Dict[str, Any]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        # Loading everything upfront
        cls._all_data = load_entire_database()  # Bad!
```

### 2. Dependency Management

```python
# GOOD: Minimal dependencies, clear hierarchy
@requires(ConfigService)
class LightweightService(BaseService):
    pass

# AVOID: Too many dependencies
@requires(Service1, Service2, Service3, Service4, Service5)
class HeavyService(BaseService):
    pass
```

### 3. Method Design

```python
# GOOD: Efficient methods
class EfficientService(BaseService):
    @classmethod
    @guarded
    def get_items(cls, ids: List[int]) -> List[Dict]:
        # Batch fetch
        return cls._fetch_batch(ids)
    
    @classmethod
    @guarded 
    def process_stream(cls, items: Iterator[Any]) -> Iterator[Any]:
        # Stream processing
        for item in items:
            yield cls._process_single(item)

# AVOID: Inefficient patterns
class InefficientService(BaseService):
    @classmethod
    @guarded
    def get_items(cls, ids: List[int]) -> List[Dict]:
        # N+1 query problem
        return [cls._fetch_single(id) for id in ids]
```

## Performance Monitoring

### Service Metrics

```python
import time
from functools import wraps
from typing import ClassVar, Dict, List, Callable
from singleton_service import BaseService, guarded

class PerformanceMonitor(BaseService):
    _metrics: ClassVar[Dict[str, List[float]]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize metrics storage."""
        cls._metrics = {}
    
    @classmethod
    def monitor(cls, service_name: str):
        """Decorator to monitor method performance."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    cls._record_metric(f"{service_name}.{func.__name__}", duration)
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    cls._record_metric(f"{service_name}.{func.__name__}.error", duration)
                    raise
            return wrapper
        return decorator
    
    @classmethod
    def _record_metric(cls, metric_name: str, value: float) -> None:
        """Record a metric value."""
        if metric_name not in cls._metrics:
            cls._metrics[metric_name] = []
        cls._metrics[metric_name].append(value)
        
        # Keep only last 1000 measurements
        if len(cls._metrics[metric_name]) > 1000:
            cls._metrics[metric_name] = cls._metrics[metric_name][-1000:]
    
    @classmethod
    @guarded
    def get_statistics(cls, metric_name: str) -> Dict[str, float]:
        """Get performance statistics for a metric."""
        if metric_name not in cls._metrics:
            return {"error": "Metric not found"}
        
        values = cls._metrics[metric_name]
        if not values:
            return {"error": "No data"}
        
        return {
            "count": len(values),
            "min_ms": min(values) * 1000,
            "max_ms": max(values) * 1000,
            "avg_ms": sum(values) / len(values) * 1000,
            "p50_ms": sorted(values)[len(values) // 2] * 1000,
            "p95_ms": sorted(values)[int(len(values) * 0.95)] * 1000,
            "p99_ms": sorted(values)[int(len(values) * 0.99)] * 1000
        }

# Usage example
@requires(PerformanceMonitor)
class MonitoredService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        pass
    
    @classmethod
    @guarded
    @PerformanceMonitor.monitor("MonitoredService")
    def slow_operation(cls) -> str:
        """Operation with performance monitoring."""
        time.sleep(0.1)  # Simulate work
        return "completed"
```

By following these performance optimization techniques and best practices, you can build efficient singleton services that scale well with your application's needs.