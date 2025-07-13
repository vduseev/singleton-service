# Async Services

Working with asynchronous services requires special consideration for initialization, dependency management, and lifecycle. This guide covers patterns and best practices for building async-aware services.

## Understanding Async in Services

### Current Framework Limitations

The singleton-service framework currently uses synchronous initialization patterns. However, you can still work with async functionality by:

1. **Initializing async resources synchronously** in `initialize()`
2. **Using async methods** in your service operations
3. **Managing async lifecycles** properly in cleanup

### Async vs Sync Boundaries

```python
import asyncio
from typing import ClassVar
from singleton_service import BaseService, requires, guarded

class AsyncDatabaseService(BaseService):
    _connection_pool: ClassVar[asyncio.Queue | None] = None
    _loop: ClassVar[asyncio.AbstractEventLoop | None] = None
    
    @classmethod
    def initialize(cls) -> None:
        """Synchronous initialization - set up async resources."""
        # Get or create event loop
        try:
            cls._loop = asyncio.get_event_loop()
        except RuntimeError:
            cls._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(cls._loop)
        
        # Initialize connection pool (sync setup)
        cls._connection_pool = asyncio.Queue(maxsize=10)
        
        # Pre-populate pool if needed
        cls._loop.run_until_complete(cls._setup_connections())
    
    @classmethod
    async def _setup_connections(cls) -> None:
        """Async helper for connection setup."""
        for _ in range(5):
            # Create mock connections
            await cls._connection_pool.put("connection")
    
    @classmethod
    @guarded
    async def execute_query(cls, query: str) -> dict:
        """Async method for database operations."""
        connection = await cls._connection_pool.get()
        try:
            # Simulate async database operation
            await asyncio.sleep(0.1)
            return {"result": f"Executed: {query}", "rows": 42}
        finally:
            await cls._connection_pool.put(connection)
```

## Patterns for Async Services

### 1. Async Resource Management

```python
import aiofiles
import aiohttp
from typing import ClassVar
from singleton_service import BaseService, requires, guarded

class AsyncFileService(BaseService):
    _session: ClassVar[aiohttp.ClientSession | None] = None
    _temp_dir: ClassVar[str] = "/tmp/async_files"
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize async resources synchronously."""
        import os
        os.makedirs(cls._temp_dir, exist_ok=True)
        
        # Note: Session creation is deferred to first use
        # to avoid event loop issues during initialization
    
    @classmethod
    def ping(cls) -> bool:
        """Health check - verify temp directory exists."""
        import os
        return os.path.exists(cls._temp_dir)
    
    @classmethod
    async def _get_session(cls) -> aiohttp.ClientSession:
        """Lazy session creation."""
        if cls._session is None or cls._session.closed:
            cls._session = aiohttp.ClientSession()
        return cls._session
    
    @classmethod
    @guarded
    async def download_file(cls, url: str, filename: str) -> str:
        """Download file asynchronously."""
        session = await cls._get_session()
        file_path = f"{cls._temp_dir}/{filename}"
        
        async with session.get(url) as response:
            async with aiofiles.open(file_path, 'wb') as file:
                async for chunk in response.content.iter_chunked(8192):
                    await file.write(chunk)
        
        return file_path
    
    @classmethod
    @guarded
    async def read_file_async(cls, filename: str) -> str:
        """Read file content asynchronously."""
        file_path = f"{cls._temp_dir}/{filename}"
        async with aiofiles.open(file_path, 'r') as file:
            return await file.read()
    
    @classmethod
    async def cleanup(cls) -> None:
        """Cleanup async resources."""
        if cls._session and not cls._session.closed:
            await cls._session.close()
```

### 2. Async Event Processing

```python
import asyncio
from typing import ClassVar, Dict, List, Callable, Awaitable
from singleton_service import BaseService, requires, guarded

class AsyncEventBus(BaseService):
    _listeners: ClassVar[Dict[str, List[Callable[[dict], Awaitable[None]]]]] = {}
    _event_queue: ClassVar[asyncio.Queue | None] = None
    _processor_task: ClassVar[asyncio.Task | None] = None
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize async event system."""
        cls._listeners = {}
        cls._event_queue = asyncio.Queue()
        
        # Start background event processor
        loop = asyncio.get_event_loop()
        cls._processor_task = loop.create_task(cls._process_events())
    
    @classmethod
    async def _process_events(cls) -> None:
        """Background task to process events."""
        while True:
            try:
                event_name, event_data = await cls._event_queue.get()
                
                # Process all listeners for this event
                listeners = cls._listeners.get(event_name, [])
                if listeners:
                    await asyncio.gather(
                        *[listener(event_data) for listener in listeners],
                        return_exceptions=True
                    )
                
                cls._event_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error processing event: {e}")
    
    @classmethod
    @guarded
    def listen(cls, event: str, callback: Callable[[dict], Awaitable[None]]) -> None:
        """Register async event listener."""
        if event not in cls._listeners:
            cls._listeners[event] = []
        cls._listeners[event].append(callback)
    
    @classmethod
    @guarded
    async def emit(cls, event: str, data: dict) -> None:
        """Emit async event."""
        await cls._event_queue.put((event, data))
    
    @classmethod
    @guarded
    def emit_nowait(cls, event: str, data: dict) -> None:
        """Emit event without waiting."""
        try:
            cls._event_queue.put_nowait((event, data))
        except asyncio.QueueFull:
            print(f"Event queue full, dropping event: {event}")
    
    @classmethod
    async def shutdown(cls) -> None:
        """Graceful shutdown of event processing."""
        if cls._processor_task:
            cls._processor_task.cancel()
            try:
                await cls._processor_task
            except asyncio.CancelledError:
                pass
        
        if cls._event_queue:
            await cls._event_queue.join()

# Example usage
@requires(AsyncEventBus)
class AsyncNotificationService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        """Register for events."""
        AsyncEventBus.listen("user_registered", cls._send_welcome_email)
        AsyncEventBus.listen("order_placed", cls._send_order_confirmation)
    
    @classmethod
    async def _send_welcome_email(cls, data: dict) -> None:
        """Send welcome email asynchronously."""
        await asyncio.sleep(0.5)  # Simulate email sending
        print(f"Welcome email sent to {data['email']}")
    
    @classmethod
    async def _send_order_confirmation(cls, data: dict) -> None:
        """Send order confirmation asynchronously."""
        await asyncio.sleep(0.3)  # Simulate email sending
        print(f"Order confirmation sent for order {data['order_id']}")
```

### 3. Async Background Tasks

```python
import asyncio
from datetime import datetime, timedelta
from typing import ClassVar, Dict, Any
from singleton_service import BaseService, requires, guarded

class AsyncBackgroundWorker(BaseService):
    _tasks: ClassVar[Dict[str, asyncio.Task]] = {}
    _running: ClassVar[bool] = False
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize background worker."""
        cls._tasks = {}
        cls._running = True
    
    @classmethod
    @guarded
    def schedule_periodic(cls, name: str, coro, interval: float) -> None:
        """Schedule a periodic async task."""
        if name in cls._tasks:
            cls._tasks[name].cancel()
        
        cls._tasks[name] = asyncio.create_task(
            cls._run_periodic(coro, interval)
        )
    
    @classmethod
    async def _run_periodic(cls, coro, interval: float) -> None:
        """Run a coroutine periodically."""
        while cls._running:
            try:
                await coro()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in periodic task: {e}")
                await asyncio.sleep(interval)
    
    @classmethod
    @guarded
    def schedule_delayed(cls, name: str, coro, delay: float) -> None:
        """Schedule a delayed async task."""
        if name in cls._tasks:
            cls._tasks[name].cancel()
        
        cls._tasks[name] = asyncio.create_task(
            cls._run_delayed(coro, delay)
        )
    
    @classmethod
    async def _run_delayed(cls, coro, delay: float) -> None:
        """Run a coroutine after a delay."""
        await asyncio.sleep(delay)
        await coro()
    
    @classmethod
    @guarded
    def cancel_task(cls, name: str) -> bool:
        """Cancel a scheduled task."""
        if name in cls._tasks:
            cls._tasks[name].cancel()
            del cls._tasks[name]
            return True
        return False
    
    @classmethod
    async def shutdown(cls) -> None:
        """Shutdown all background tasks."""
        cls._running = False
        
        for task in cls._tasks.values():
            task.cancel()
        
        # Wait for all tasks to complete
        if cls._tasks:
            await asyncio.gather(*cls._tasks.values(), return_exceptions=True)
        
        cls._tasks.clear()

# Example usage
@requires(AsyncBackgroundWorker)
class AsyncHealthMonitor(BaseService):
    _last_check: ClassVar[datetime | None] = None
    
    @classmethod
    def initialize(cls) -> None:
        """Start health monitoring."""
        AsyncBackgroundWorker.schedule_periodic(
            "health_check", 
            cls._check_health, 
            interval=30.0  # Every 30 seconds
        )
    
    @classmethod
    async def _check_health(cls) -> None:
        """Perform health check."""
        cls._last_check = datetime.now()
        
        # Simulate health check operations
        await asyncio.sleep(0.1)
        print(f"Health check completed at {cls._last_check}")
    
    @classmethod
    @guarded
    def get_last_check(cls) -> datetime | None:
        """Get last health check time."""
        return cls._last_check
```

## Async Service Lifecycle

### Initialization Order with Async

```python
import asyncio
from singleton_service import BaseService, requires, guarded

class AsyncCacheService(BaseService):
    _redis_pool: ClassVar[Any] = None
    
    @classmethod
    def initialize(cls) -> None:
        """Sync initialization - setup connection pool."""
        # Initialize connection pool synchronously
        # Actual connections created on first use
        cls._redis_pool = "connection_pool_placeholder"
    
    @classmethod
    @guarded
    async def get(cls, key: str) -> str | None:
        """Async cache get operation."""
        await asyncio.sleep(0.01)  # Simulate Redis operation
        return f"cached_value_for_{key}"

@requires(AsyncCacheService)
class AsyncUserService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        """Standard sync initialization."""
        print("UserService initialized")
    
    @classmethod
    @guarded
    async def get_user(cls, user_id: str) -> dict:
        """Get user with caching."""
        # Try cache first
        cached = await AsyncCacheService.get(f"user:{user_id}")
        if cached:
            return {"id": user_id, "source": "cache"}
        
        # Simulate database lookup
        await asyncio.sleep(0.1)
        user = {"id": user_id, "name": f"User {user_id}", "source": "database"}
        
        return user

# Usage example
async def main():
    # Services initialize in dependency order (sync)
    user = await AsyncUserService.get_user("123")
    print(user)

# Run the async application
if __name__ == "__main__":
    asyncio.run(main())
```

### Graceful Shutdown

```python
import asyncio
import signal
from typing import ClassVar, List
from singleton_service import BaseService

class AsyncServiceManager(BaseService):
    _shutdown_handlers: ClassVar[List[Callable[[], Awaitable[None]]]] = []
    _shutdown_event: ClassVar[asyncio.Event | None] = None
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize shutdown manager."""
        cls._shutdown_handlers = []
        cls._shutdown_event = asyncio.Event()
        
        # Register signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, cls._signal_handler)
    
    @classmethod
    def _signal_handler(cls) -> None:
        """Handle shutdown signals."""
        print("Shutdown signal received")
        if cls._shutdown_event:
            cls._shutdown_event.set()
    
    @classmethod
    @guarded
    def register_shutdown_handler(cls, handler: Callable[[], Awaitable[None]]) -> None:
        """Register async shutdown handler."""
        cls._shutdown_handlers.append(handler)
    
    @classmethod
    @guarded
    async def wait_for_shutdown(cls) -> None:
        """Wait for shutdown signal."""
        if cls._shutdown_event:
            await cls._shutdown_event.wait()
    
    @classmethod
    @guarded
    async def shutdown(cls) -> None:
        """Execute all shutdown handlers."""
        print("Starting graceful shutdown...")
        
        # Run all shutdown handlers
        for handler in cls._shutdown_handlers:
            try:
                await handler()
            except Exception as e:
                print(f"Error in shutdown handler: {e}")
        
        print("Graceful shutdown completed")

# Application example
@requires(AsyncServiceManager, AsyncEventBus, AsyncBackgroundWorker)
class AsyncApplication(BaseService):
    @classmethod
    def initialize(cls) -> None:
        """Initialize application with shutdown handling."""
        # Register cleanup handlers
        AsyncServiceManager.register_shutdown_handler(AsyncEventBus.shutdown)
        AsyncServiceManager.register_shutdown_handler(AsyncBackgroundWorker.shutdown)
    
    @classmethod
    @guarded
    async def run(cls) -> None:
        """Run the application."""
        print("Application starting...")
        
        # Start background tasks
        AsyncBackgroundWorker.schedule_periodic(
            "heartbeat", 
            cls._heartbeat, 
            interval=5.0
        )
        
        # Wait for shutdown signal
        await AsyncServiceManager.wait_for_shutdown()
        
        # Graceful shutdown
        await AsyncServiceManager.shutdown()
    
    @classmethod
    async def _heartbeat(cls) -> None:
        """Application heartbeat."""
        print(f"Application heartbeat: {datetime.now()}")

# Main application entry point
async def main():
    app = AsyncApplication()
    await app.run()

if __name__ == "__main__":
    asyncio.run(main())
```

## Testing Async Services

### Async Test Patterns

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_async_service_method():
    """Test async service methods."""
    # Reset service state
    AsyncDatabaseService._connection_pool = None
    
    # Test async method
    result = await AsyncDatabaseService.execute_query("SELECT * FROM users")
    
    assert result["result"] == "Executed: SELECT * FROM users"
    assert result["rows"] == 42

@pytest.mark.asyncio
async def test_async_event_processing():
    """Test async event handling."""
    # Track received events
    received_events = []
    
    async def test_listener(data: dict) -> None:
        received_events.append(data)
    
    # Register listener and emit event
    AsyncEventBus.listen("test_event", test_listener)
    await AsyncEventBus.emit("test_event", {"message": "test"})
    
    # Wait for event processing
    await asyncio.sleep(0.1)
    
    assert len(received_events) == 1
    assert received_events[0]["message"] == "test"

@pytest.fixture
async def async_services():
    """Fixture for async service testing."""
    # Setup
    yield
    
    # Cleanup
    await AsyncEventBus.shutdown()
    await AsyncBackgroundWorker.shutdown()
```

## Best Practices

1. **Initialize async resources carefully** - Set up pools and connections in `initialize()`
2. **Use lazy initialization** - Create expensive async resources on first use
3. **Handle event loops properly** - Be aware of event loop context in initialization
4. **Implement proper cleanup** - Always clean up async resources in shutdown handlers
5. **Use asyncio.gather()** - Process multiple async operations concurrently
6. **Handle exceptions gracefully** - Wrap async operations in try/except blocks
7. **Test with pytest-asyncio** - Use proper async testing frameworks
8. **Monitor resource usage** - Track connection pools and background tasks
9. **Use timeouts** - Add timeouts to prevent hanging operations
10. **Document async boundaries** - Clearly indicate which methods are async

By following these patterns, you can successfully integrate asynchronous functionality into your singleton services while maintaining the framework's dependency management and initialization guarantees.