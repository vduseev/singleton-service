# Examples

This section provides comprehensive, real-world examples demonstrating different patterns and use cases with **singleton-service**. Each example is complete and runnable, showing you practical patterns for building production applications.

## 📋 Example Categories

### 🏗️ Infrastructure Examples
- **[Weather Service](weather-service.md)** - HTTP API client with caching and error handling
- **[Database Service](database-service.md)** - Connection pooling, transactions, and migrations
- **[Background Worker](background-worker.md)** - Task queues, scheduling, and resource management

### 🔐 Authentication & Security
- **[Auth Service](auth-service.md)** - JWT authentication, session management, and security
- **[User Service](user-service.md)** - User management with validation and authorization

### 🌐 Application Examples  
- **[Web Server](web-server.md)** - FastAPI integration with middleware and dependency injection
- **[CLI Application](cli-application.md)** - Command-line tool with configuration and logging

### 🧪 Development & Testing
- **[Testing Services](testing-services.md)** - Complete testing strategies and patterns
- **[Service Composition](service-composition.md)** - Complex service relationships and patterns

## 🎯 Learning Path

### Beginner
Start with these examples if you're new to **singleton-service**:

1. **[Weather Service](weather-service.md)** - Basic service with external API
2. **[Database Service](database-service.md)** - Infrastructure service patterns
3. **[User Service](user-service.md)** - Business logic with dependencies

### Intermediate  
Once comfortable with basics, explore these patterns:

4. **[Auth Service](auth-service.md)** - Security and session management
5. **[Web Server](web-server.md)** - Web framework integration
6. **[Background Worker](background-worker.md)** - Asynchronous processing

### Advanced
For complex scenarios and production patterns:

7. **[CLI Application](cli-application.md)** - Command-line application architecture
8. **[Testing Services](testing-services.md)** - Comprehensive testing strategies
9. **[Service Composition](service-composition.md)** - Advanced service relationships

## 🛠️ Running the Examples

Each example includes:

- **Complete source code** - Copy-paste ready implementations
- **Dependencies** - Required packages and setup instructions
- **Configuration** - Environment variables and settings
- **Usage examples** - How to run and test the code
- **Explanations** - Why design decisions were made

### Prerequisites

```bash
# Install singleton-service
pip install singleton-service

# Example-specific dependencies listed in each example
```

### Example Structure

Each example follows this structure:

```
example-name/
├── main.py           # Main application code
├── services/         # Service implementations
├── tests/           # Test cases
├── config/          # Configuration files
└── README.md        # Setup and usage instructions
```

## 🔍 Key Patterns Demonstrated

### Service Design Patterns
- **Single Responsibility** - Each service has one clear purpose
- **Dependency Injection** - Clean service relationships
- **Error Handling** - Robust failure management
- **Resource Management** - Proper cleanup and pooling

### Testing Patterns
- **Service Mocking** - How to mock dependencies
- **Test Isolation** - Clean test state management
- **Integration Testing** - Testing service interactions
- **Performance Testing** - Load and stress testing

### Production Patterns
- **Configuration Management** - Environment-based config
- **Logging and Monitoring** - Observability patterns
- **Health Checks** - Service health verification
- **Graceful Shutdown** - Clean resource cleanup

## 💡 Example Use Cases

### Web Applications
- REST APIs with database integration
- Authentication and authorization
- File upload and processing
- Real-time features with WebSockets

### Data Processing
- ETL pipelines with external APIs
- Batch processing with queues
- Data validation and transformation
- Scheduled data synchronization

### Command-Line Tools
- Configuration management utilities
- Data migration tools
- Development and deployment scripts
- System administration utilities

### Microservices
- Service-to-service communication
- Shared configuration services
- Health check endpoints
- Service discovery patterns

## 📚 Additional Resources

- **[Concepts](../concepts/)** - Understand the theory behind the patterns
- **[Tutorial](../tutorial/)** - Step-by-step learning guide
- **[API Reference](../api/)** - Complete framework documentation
- **[Best Practices](../concepts/best-practices.md)** - Production-ready guidelines

---

**Ready to explore?** Start with the [Weather Service](weather-service.md) example to see basic patterns in action.