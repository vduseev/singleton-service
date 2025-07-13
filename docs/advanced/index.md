# Advanced Topics

This section covers advanced concepts and techniques for working with singleton services. These topics are designed for developers who want to leverage the full power of the framework and handle complex scenarios.

## Overview

The advanced topics in this section include:

1. **[Circular Dependencies](circular-dependencies.md)** - Detecting, preventing, and resolving circular dependencies between services
2. **[Async Services](async-services.md)** - Working with asynchronous services and handling async initialization
3. **[Performance](performance.md)** - Optimizing service performance and understanding framework overhead
4. **[Debugging](debugging.md)** - Debugging techniques, logging, and troubleshooting common issues
5. **[Migration Guide](migration-guide.md)** - Migrating from other frameworks and design patterns

## When to Read These Topics

- **If you're building complex applications** with many interdependent services
- **If you're encountering performance bottlenecks** or initialization issues
- **If you're working with async/await patterns** in your services
- **If you're debugging dependency-related problems** in your application
- **If you're migrating** from other dependency injection frameworks

## Prerequisites

Before diving into these advanced topics, you should be familiar with:

- Basic service creation and dependency declaration
- The `@requires` and `@guarded` decorators
- Service initialization patterns
- Error handling concepts

If you haven't already, we recommend reading through the [Tutorial](../tutorial/index.md) and [Concepts](../concepts/index.md) sections first.

## Getting Help

If you encounter issues while implementing advanced patterns:

1. Check the [debugging guide](debugging.md) for common solutions
2. Review the [examples](../examples/index.md) for similar use cases
3. Consult the [API reference](../api/index.md) for detailed method documentation
4. Visit our [GitHub issues](https://github.com/vduseev/singleton-service/issues) for community support