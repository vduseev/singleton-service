# Changelog

All notable changes to singleton-service will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of singleton-service framework
- `BaseService` class for creating singleton services
- `@requires` decorator for declaring service dependencies
- `@guarded` decorator for ensuring initialization before method execution
- Automatic dependency resolution with topological sorting
- Circular dependency detection with helpful error messages
- Service health checks via `ping()` method
- Comprehensive error handling with custom exceptions
- `BaseRunnable` class for creating executable services
- Type-safe implementation with full typing support

### Documentation
- Complete documentation website with MkDocs
- Comprehensive tutorial series covering all features
- Detailed concept documentation explaining design patterns
- 9 real-world examples demonstrating various use cases
- API reference with auto-generated documentation
- Advanced topics including async patterns and performance
- Migration guide from other frameworks

## [0.1.0] - Coming Soon

### Planned Features
- Async service initialization support
- Service lifecycle hooks (pre_init, post_init, shutdown)
- Configuration integration helpers
- Service discovery and registration
- Metrics and monitoring integration
- Plugin system for extending functionality
- CLI tools for service inspection
- Performance profiling tools

## Future Roadmap

### Version 0.2.0
- **Async-first design** - Native async/await support throughout
- **Service orchestration** - Tools for managing service groups
- **Hot reloading** - Development mode with automatic reinitialization
- **Service versioning** - Support for multiple service versions

### Version 0.3.0
- **Distributed services** - Support for services across processes/machines
- **Service mesh integration** - Native support for service mesh patterns
- **Advanced monitoring** - Built-in observability features
- **GraphQL integration** - Automatic GraphQL schema generation

### Version 1.0.0
- **Stable API** - Long-term support guarantee
- **Production-ready** - Battle-tested in production environments
- **Performance optimized** - Minimal overhead and maximum efficiency
- **Enterprise features** - Advanced security and compliance features

## How to Contribute

We welcome contributions! Please see our [Contributing Guide](contributing.md) for details on:

- Reporting bugs
- Suggesting features
- Submitting pull requests
- Development setup

## Version Support

| Version | Supported | Python Versions |
|---------|-----------|-----------------|
| 0.1.x   | ✅ Active  | 3.8+           |

## Deprecation Policy

- Features will be deprecated with at least one minor version warning
- Deprecated features will be removed in the next major version
- Security fixes will be backported to supported versions

## Links

- [GitHub Repository](https://github.com/vduseev/singleton-service)
- [PyPI Package](https://pypi.org/project/singleton-service/)
- [Documentation](https://singleton-service.dev)
- [Issue Tracker](https://github.com/vduseev/singleton-service/issues)