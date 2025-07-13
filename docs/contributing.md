# Contributing to Singleton Service

Thank you for your interest in contributing to singleton-service! This guide will help you get started with contributing to the project.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct:

- **Be respectful** - Treat everyone with respect and kindness
- **Be inclusive** - Welcome people of all backgrounds and experience levels
- **Be constructive** - Provide helpful feedback and suggestions
- **Be professional** - Keep discussions focused on the project

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When creating a bug report, please include:

1. **Clear title and description** - What went wrong?
2. **Steps to reproduce** - How can we recreate the issue?
3. **Expected behavior** - What should have happened?
4. **Actual behavior** - What actually happened?
5. **Environment details** - Python version, OS, package versions
6. **Code samples** - Minimal reproducible example

**Example bug report:**

```markdown
**Description**
The `@guarded` decorator raises an unexpected error when used with async methods.

**Steps to Reproduce**
1. Create a service with an async method
2. Apply the `@guarded` decorator
3. Call the method

**Code Example**
```python
class MyService(BaseService):
    @classmethod
    @guarded
    async def my_method(cls):
        return "test"

# This raises an error
await MyService.my_method()
```

**Expected**: Method executes successfully
**Actual**: TypeError: object NoneType can't be used in 'await' expression

**Environment**
- Python 3.10.5
- singleton-service 0.1.0
- macOS 12.4
```

### Suggesting Features

Feature requests are welcome! Please provide:

1. **Use case** - What problem does this solve?
2. **Proposed solution** - How would it work?
3. **Alternatives considered** - What other approaches did you think about?
4. **Additional context** - Examples, mockups, or references

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Follow the coding style** - Use the project's conventions
3. **Write tests** - Ensure your changes are tested
4. **Update documentation** - Keep docs in sync with code
5. **Create focused PRs** - One feature/fix per pull request
6. **Write clear commit messages** - Explain what and why

## Development Setup

### Prerequisites

- Python 3.8 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- Git

### Setting Up Your Environment

1. **Clone your fork:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/singleton-service.git
   cd singleton-service
   ```

2. **Install dependencies:**
   ```bash
   uv sync --all-groups
   ```

3. **Run tests:**
   ```bash
   uv run pytest
   ```

4. **Run linting:**
   ```bash
   uv run ruff check src tests
   uv run mypy src
   ```

5. **Build documentation:**
   ```bash
   uv run --group docs mkdocs serve
   ```

### Project Structure

```
singleton-service/
├── src/
│   └── singleton_service/
│       ├── __init__.py
│       ├── base_service.py      # Core service implementation
│       ├── decorators.py        # @requires and @guarded decorators
│       ├── exceptions.py        # Custom exceptions
│       └── base_runnable.py     # Runnable service base class
├── tests/
│   ├── test_base_service.py
│   ├── test_decorators.py
│   └── test_integration.py
├── docs/                        # Documentation source
├── examples/                    # Example implementations
├── pyproject.toml              # Project configuration
└── README.md
```

## Coding Standards

### Style Guide

We follow PEP 8 with these additions:

- **Line length**: 88 characters (Black default)
- **Imports**: Sorted with `isort`
- **Type hints**: Required for all public APIs
- **Docstrings**: Google style format

### Example Code Style

```python
from typing import ClassVar, Optional

from singleton_service import BaseService, guarded, requires


@requires(ConfigService)
class ExampleService(BaseService):
    """Example service demonstrating coding standards.
    
    This service shows how to properly format code according
    to our project standards.
    
    Attributes:
        _data: Internal storage for service data.
        _cache_ttl: Cache time-to-live in seconds.
    """
    
    _data: ClassVar[Optional[dict]] = None
    _cache_ttl: ClassVar[int] = 300
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize the service with configuration.
        
        Loads configuration from ConfigService and sets up
        internal data structures.
        
        Raises:
            ServiceInitializationError: If configuration is invalid.
        """
        config = ConfigService.get_config("example")
        if not cls._validate_config(config):
            raise ServiceInitializationError("Invalid configuration")
        
        cls._data = {"config": config}
    
    @classmethod
    def ping(cls) -> bool:
        """Check if service is healthy.
        
        Returns:
            True if service is initialized and ready.
        """
        return cls._data is not None
    
    @classmethod
    @guarded
    def process_data(cls, input_data: str) -> dict:
        """Process input data according to configuration.
        
        Args:
            input_data: The data to process.
            
        Returns:
            Processed data as a dictionary.
            
        Raises:
            ValueError: If input_data is invalid.
        """
        if not input_data:
            raise ValueError("Input data cannot be empty")
        
        return {
            "processed": input_data.upper(),
            "timestamp": time.time(),
        }
    
    @classmethod
    def _validate_config(cls, config: dict) -> bool:
        """Validate service configuration.
        
        Args:
            config: Configuration dictionary to validate.
            
        Returns:
            True if configuration is valid.
        """
        return isinstance(config, dict) and "enabled" in config
```

### Testing Standards

- **Test coverage**: Aim for >90% coverage
- **Test naming**: `test_should_<expected_behavior>_when_<condition>`
- **Test structure**: Arrange-Act-Assert pattern
- **Fixtures**: Use pytest fixtures for setup

```python
import pytest
from singleton_service.exceptions import CircularDependencyError


class TestServiceDependencies:
    """Test service dependency management."""
    
    def test_should_detect_circular_dependency_when_services_depend_on_each_other(self):
        """Test that circular dependencies are detected."""
        # Arrange
        @requires(ServiceB)
        class ServiceA(BaseService):
            pass
        
        @requires(ServiceA)
        class ServiceB(BaseService):
            pass
        
        # Act & Assert
        with pytest.raises(CircularDependencyError):
            ServiceA.some_method()
    
    @pytest.fixture
    def mock_config(self):
        """Provide mock configuration for tests."""
        return {
            "database": {"host": "localhost", "port": 5432},
            "cache": {"ttl": 300},
        }
```

## Documentation

### Docstring Format

Use Google style docstrings:

```python
def complex_function(param1: str, param2: int = 0) -> dict:
    """Short description of function.
    
    Longer description explaining the function's behavior,
    assumptions, and any important details.
    
    Args:
        param1: Description of param1.
        param2: Description of param2. Defaults to 0.
        
    Returns:
        Description of return value.
        
    Raises:
        ValueError: When param1 is empty.
        TypeError: When param2 is not an integer.
        
    Example:
        >>> result = complex_function("test", 42)
        >>> print(result)
        {'status': 'success', 'value': 42}
    """
    pass
```

### Documentation Updates

When adding features or fixing bugs:

1. Update relevant documentation files
2. Add/update code examples
3. Update API reference if needed
4. Add entry to changelog

## Review Process

### Before Submitting

- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] PR description explains changes

### Review Timeline

- Initial response: Within 48 hours
- Full review: Within 1 week
- Follow-up reviews: Within 3 days

### What to Expect

1. **Automated checks** - CI runs tests and linting
2. **Code review** - Maintainers review changes
3. **Feedback** - Suggestions for improvements
4. **Approval** - Once all feedback is addressed
5. **Merge** - Maintainers merge the PR

## Release Process

1. **Version bump** - Update version in `pyproject.toml`
2. **Changelog** - Update `CHANGELOG.md`
3. **Tag release** - Create git tag
4. **Build package** - `uv build`
5. **Publish** - Upload to PyPI
6. **Documentation** - Deploy updated docs

## Getting Help

- **Discord**: Join our community server
- **Discussions**: Use GitHub Discussions for questions
- **Issues**: Report bugs or request features
- **Email**: maintainers@singleton-service.dev

## Recognition

Contributors are recognized in:

- `CONTRIBUTORS.md` file
- Release notes
- Documentation credits
- GitHub contributors page

Thank you for contributing to singleton-service!