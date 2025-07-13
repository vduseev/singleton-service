# Installation

## Requirements

**singleton-service** requires Python 3.10 or later and has zero runtime dependencies.

### Supported Python Versions

- Python 3.10+
- Python 3.11
- Python 3.12  
- Python 3.13
- Python 3.14 (when available)
- Python 3.15 (when available)

### Supported Platforms

- Linux (all distributions)
- macOS (10.14+)
- Windows (10+)
- Any platform where Python 3.10+ runs

## Basic Installation

Install singleton-service using your preferred package manager:

```bash
pip install singleton-service
```

```bash
uv add singleton-service
```

```bash
poetry add singleton-service
```

```bash
pipenv install singleton-service
```

## Development Installation

If you plan to contribute to singleton-service or run the examples:

### Clone the Repository

```bash
git clone https://github.com/vduseev/singleton-service.git
cd singleton-service
```

### Install with Development Dependencies

=== "uv (recommended)"

    ```bash
    # Install the package in development mode with all dependencies
    uv sync --all-groups
    
    # Or just specific dependency groups
    uv sync --group dev --group docs --group examples
    ```

=== "pip"

    ```bash
    # Install in development mode
    pip install -e .
    
    # Install development dependencies
    pip install -e ".[dev,docs,examples]"
    ```

=== "poetry"

    ```bash
    # Install with all dependencies
    poetry install --with dev,docs,examples
    ```

### Development Dependencies

The development installation includes:

- **Testing**: pytest, pytest-asyncio, pytest-cov
- **Type Checking**: mypy  
- **Code Quality**: ruff (linting and formatting)
- **Documentation**: mkdocs, mkdocs-material, mkdocstrings
- **Examples**: FastAPI, Click, SQLModel, and other example dependencies

## Verify Installation

Check that singleton-service is properly installed:

```python
# test_install.py
from singleton_service import BaseService, requires, guarded

@requires()  # No dependencies
class TestService(BaseService):
    @classmethod  
    def initialize(cls) -> None:
        print("✅ singleton-service is working!")
    
    @classmethod
    @guarded
    def test(cls) -> str:
        return "Installation successful!"

# Test it
result = TestService.test()
print(result)
```

Run the test:

```bash
python test_install.py
```

You should see:
```
✅ singleton-service is working!
Installation successful!
```

## Installing from Source

### Latest Development Version

Install the latest development version directly from GitHub:

```bash
pip install git+https://github.com/vduseev/singleton-service.git
```

### Specific Version/Branch

```bash
# Install a specific tag
pip install git+https://github.com/vduseev/singleton-service.git@v0.1.0

# Install from a specific branch  
pip install git+https://github.com/vduseev/singleton-service.git@main
```

### Local Development

If you've made local changes and want to test them:

```bash
cd singleton-service
pip install -e .
```

The `-e` flag installs in "editable" mode, so changes to the source code are immediately reflected.

## Virtual Environments

It's recommended to install singleton-service in a virtual environment:

=== "venv"

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install singleton-service
    ```

=== "conda"

    ```bash
    conda create -n myproject python=3.11
    conda activate myproject  
    pip install singleton-service
    ```

=== "pyenv + virtualenv"

    ```bash
    pyenv virtualenv 3.11.0 myproject
    pyenv activate myproject
    pip install singleton-service
    ```

## Troubleshooting

### ImportError: No module named 'singleton_service'

This usually means the package isn't installed in the current Python environment:

1. Check your Python version: `python --version`
2. Check if the package is installed: `pip list | grep singleton-service`
3. Make sure you're in the right virtual environment
4. Try reinstalling: `pip install --force-reinstall singleton-service`

### TypeError: 'type' object is not subscriptable

This error occurs when using Python < 3.10:

```python
# This fails on Python < 3.10
from typing import List
def func() -> List[str]:  # ❌ Error on old Python
    pass
```

**Solution**: Upgrade to Python 3.10 or later. singleton-service uses modern type hints that require Python 3.10+.

### Module conflicts

If you have conflicts with other packages:

1. Check for conflicting packages: `pip check`
2. Create a fresh virtual environment
3. Install only singleton-service to isolate the issue

### Permission errors

On some systems you might get permission errors:

```bash
# Use --user flag to install for current user only
pip install --user singleton-service

# Or use a virtual environment (recommended)
python -m venv venv
source venv/bin/activate
pip install singleton-service
```

## IDE Integration

### VS Code

Add these settings to `.vscode/settings.json` for the best experience:

```json
{
    "python.analysis.typeCheckingMode": "strict",
    "python.linting.enabled": true,
    "python.linting.mypyEnabled": true
}
```

### PyCharm

1. Enable type checking: **Settings → Editor → Inspections → Python → Type checker**
2. Configure interpreter to use your virtual environment
3. Mark `src/` as Sources Root if working on singleton-service itself

### Type Checking

Run mypy to verify type safety:

```bash
mypy your_project.py
```

singleton-service is fully typed and works well with static type checkers.

## Next Steps

- **New to singleton-service?** → [Quick Start Guide](quickstart.md)
- **Want to learn step by step?** → [Tutorial](tutorial/)
- **Need examples?** → [Examples](examples/)
- **Found an issue?** → [GitHub Issues](https://github.com/vduseev/singleton-service/issues)