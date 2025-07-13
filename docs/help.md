# Getting Help

Need help with singleton-service? This page provides resources and guidance for getting support.

## Quick Links

- 📚 [Documentation](https://singleton-service.dev) - Comprehensive guides and API reference
- 💬 [GitHub Discussions](https://github.com/vduseev/singleton-service/discussions) - Community Q&A
- 🐛 [Issue Tracker](https://github.com/vduseev/singleton-service/issues) - Report bugs
- 📝 [Examples](examples/index.md) - Working code examples
- 🎓 [Tutorial](tutorial/index.md) - Step-by-step learning guide

## Common Issues

### Installation Problems

**Issue**: Package won't install with pip

```bash
# Solution 1: Upgrade pip
pip install --upgrade pip

# Solution 2: Install from source
git clone https://github.com/vduseev/singleton-service.git
cd singleton-service
pip install -e .
```

**Issue**: Import errors after installation

```python
# Make sure you're importing correctly
from singleton_service import BaseService, requires, guarded

# Not this:
# from singleton-service import BaseService  # Wrong!
```

### Service Initialization Issues

**Issue**: Service not initializing

```python
# Check 1: Ensure you're calling a @guarded method
MyService.some_method()  # This triggers initialization

# Check 2: Verify initialize() method exists
class MyService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        # Your initialization code
        pass

# Check 3: Check ping() returns True
if not MyService.ping():
    print("Service failed to initialize!")
```

**Issue**: Circular dependency error

```python
# Use the debugging tools to visualize dependencies
from singleton_service.exceptions import CircularDependencyError

try:
    MyService.some_method()
except CircularDependencyError as e:
    print(f"Circular dependency: {e}")
    # See advanced/circular-dependencies.md for solutions
```

### Common Error Messages

#### "Service not initialized"

This means the service's `initialize()` method hasn't been called yet. Solutions:

1. Call a `@guarded` method to trigger initialization
2. Check if `initialize()` is raising an exception
3. Verify all dependencies are properly initialized

#### "Circular dependency detected"

Services have a dependency loop. Solutions:

1. Review the [circular dependencies guide](advanced/circular-dependencies.md)
2. Refactor to use event-driven patterns
3. Extract shared functionality to a separate service

#### "Cannot call guarded method from initialize"

You're trying to call a `@guarded` method during initialization. Solutions:

1. Remove `@guarded` from internal helper methods
2. Move the logic directly into `initialize()`
3. Use lazy initialization patterns

## Debugging Tips

### 1. Enable Debug Logging

```python
import logging

# Enable debug logging for singleton_service
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('singleton_service')
logger.setLevel(logging.DEBUG)
```

### 2. Inspect Service State

```python
# Check if service is initialized
print(f"Initialized: {MyService._initialized}")

# Check dependencies
deps = getattr(MyService, '_dependencies', set())
print(f"Dependencies: {[d.__name__ for d in deps]}")

# Check initialization order
try:
    order = MyService._get_initialization_order()
    for i, svc in enumerate(order):
        print(f"{i+1}. {svc.__name__}")
except Exception as e:
    print(f"Error: {e}")
```

### 3. Use Print Debugging

```python
class DebugService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        print(f"[DEBUG] {cls.__name__} initializing...")
        # Your initialization code
        print(f"[DEBUG] {cls.__name__} initialized!")
    
    @classmethod
    def ping(cls) -> bool:
        result = True  # Your health check
        print(f"[DEBUG] {cls.__name__}.ping() = {result}")
        return result
```

## Getting Support

### 1. Search Existing Resources

Before asking for help:

1. **Search the documentation** - Use the search feature
2. **Check GitHub issues** - Someone may have had the same problem
3. **Review examples** - Working code often answers questions
4. **Read error messages** - They often contain the solution

### 2. Ask a Question

When asking for help, provide:

1. **Clear description** of what you're trying to do
2. **Minimal code example** that reproduces the issue
3. **Full error message** including stack trace
4. **Environment details** (Python version, OS, package version)

**Good question example:**

```markdown
**Title**: Service fails to initialize with async database connection

**Description**: 
I'm trying to use an async database connection in my service, but it fails during initialization.

**Code**:
```python
class DatabaseService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        cls._conn = await create_async_connection()  # SyntaxError!

# Error: SyntaxError: 'await' outside async function
```

**Environment**:
- Python 3.10
- singleton-service 0.1.0
- asyncpg 0.27.0

**What I've tried**:
- Making initialize() async (doesn't work)
- Using asyncio.run() (causes event loop issues)
```

### 3. Report a Bug

If you've found a bug:

1. **Check existing issues** first
2. **Create a minimal reproduction** case
3. **File a bug report** with all details
4. **Be patient** - maintainers are volunteers

### 4. Community Support

Join our community:

- **GitHub Discussions** - Best for Q&A and general help
- **Stack Overflow** - Tag questions with `singleton-service`
- **Discord** - Real-time chat with community members
- **Twitter** - Follow @singleton_service for updates

## Learning Resources

### Official Resources

1. **[Tutorial](tutorial/index.md)** - Start here if you're new
2. **[Concepts](concepts/index.md)** - Understand the design
3. **[Examples](examples/index.md)** - Learn from working code
4. **[API Reference](api/index.md)** - Detailed documentation

### Video Tutorials

- "Getting Started with Singleton Service" - 10 minute intro
- "Building a Web API with Singleton Service" - 45 minute tutorial
- "Advanced Patterns" - Deep dive into complex scenarios

### Blog Posts

- "Why We Built Singleton Service" - Design philosophy
- "Singleton Service vs Traditional DI" - Comparison guide
- "Real-world Case Studies" - How companies use it

### Example Projects

1. **Todo API** - REST API with database
2. **Chat Application** - WebSocket server
3. **Data Pipeline** - ETL with singleton services
4. **Microservice** - Complete microservice example

## FAQ

### General Questions

**Q: How is this different from regular singletons?**
A: singleton-service provides dependency management, initialization ordering, and error handling that traditional singletons lack.

**Q: Can I use this with async/await?**
A: Yes! See the [async services guide](advanced/async-services.md) for patterns and examples.

**Q: Is this thread-safe?**
A: The framework handles initialization thread-safely. Your service implementations should handle their own thread safety.

**Q: Can I use this with Django/Flask/FastAPI?**
A: Yes! singleton-service works great with web frameworks. See the examples for integration patterns.

### Technical Questions

**Q: How do I mock services for testing?**
A: See the [testing guide](tutorial/testing.md) for mocking strategies and fixtures.

**Q: Can services have configuration?**
A: Yes, typically through a ConfigService or environment variables. See examples for patterns.

**Q: How do I handle service cleanup/shutdown?**
A: Implement cleanup methods and call them during application shutdown. See the async guide for examples.

**Q: What about performance overhead?**
A: After initialization, the overhead is minimal (< 1 microsecond per method call). See the [performance guide](advanced/performance.md).

## Troubleshooting Checklist

When something goes wrong, check:

- [ ] **Python version** - Are you using Python 3.8+?
- [ ] **Import statements** - Are you importing from `singleton_service`?
- [ ] **Class inheritance** - Does your service inherit from `BaseService`?
- [ ] **Method decorators** - Are you using `@classmethod` on all methods?
- [ ] **Initialization** - Did you implement `initialize()` method?
- [ ] **Dependencies** - Are all dependencies listed in `@requires`?
- [ ] **Circular deps** - Do services depend on each other?
- [ ] **Error messages** - What exactly does the error say?
- [ ] **Debug output** - What do print statements show?
- [ ] **Documentation** - Have you checked relevant guides?

## Still Need Help?

If you've tried everything above and still need help:

1. **Prepare a minimal example** that shows the problem
2. **Document what you've tried** and what happened
3. **Post in GitHub Discussions** with all details
4. **Be patient and respectful** - we're here to help!

Remember: The more information you provide, the easier it is to help you!