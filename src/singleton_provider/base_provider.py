"""Core singleton provider implementation.

This module provides the `BaseProvider` class, which is the foundation of the singleton-provider 
framework. It implements a singleton pattern where providers cannot be instantiated and all 
functionality is accessed through class methods.

The module handles dependency management, initialization ordering, and health checks 
automatically, ensuring that providers are initialized in the correct order and only when needed.

Example:
    Basic provider definition:
    
    ```python
    from singleton_provider import BaseProvider
    
    class DatabaseProvider(BaseProvider):
        _connection = None
        
        @classmethod
        def initialize(cls) -> None:
            cls._connection = create_connection()
            
        @classmethod
        def ping(cls) -> bool:
            return cls._connection is not None and cls._connection.is_alive()
            
        @classmethod
        @guarded
        def query(cls, sql: str) -> List[Dict]:
            return cls._connection.execute(sql)
    ```
"""
import logging
from abc import ABC
from collections import defaultdict

from .exceptions import (
    CircularDependencyError,
    ProviderInitializationError,
)


logger = logging.getLogger(__name__)


class BaseProvider(ABC):
    """Base class for all singleton providers.
    
    This class implements the singleton pattern by preventing instantiation and providing
    a framework for dependency management, lazy initialization, and health checks.
    
    Providers inherit from this class and define their logic in class methods. The framework
    automatically handles initialization order based on declared dependencies.
    
    Attributes:
        _initialized: Whether this provider has been successfully initialized.
        _dependencies: Set of other providers this provider depends on.
    
    Note:
        Providers cannot be instantiated. Attempting to create an instance will raise a RuntimeError.
        All provider state must be stored in class variables.
    
    Example:
        Creating a provider with dependencies:
        
        ```python
        @requires(DatabaseProvider, CacheProvider)
        class UserProvider(BaseProvider):
            _users: ClassVar[Dict[int, User]] = {}
            
            @classmethod
            def initialize(cls) -> None:
                # Load initial data
                cls._users = DatabaseProvider.load_all_users()
                
            @classmethod
            def ping(cls) -> bool:
                return len(cls._users) > 0
                
            @classmethod
            @guarded
            def get_user(cls, user_id: int) -> User | None:
                return cls._users.get(user_id)
        ```
    """
    _initialized: bool = False
    _dependencies: set[type["BaseProvider"]] = set()

    def __new__(cls, *args, **kwargs) -> "BaseProvider":
        """Prevent instantiation of singleton providers.
        
        This method is overridden to prevent creating instances of providers.
        The singleton pattern is enforced by making all functionality available
        through class methods only.
        
        Args:
            *args: Any positional arguments (ignored).
            **kwargs: Any keyword arguments (ignored).
            
        Raises:
            RuntimeError: Always raised to prevent instantiation.
            
        Example:
            ```python
            # This will raise RuntimeError
            provider = MyProvider()  # ❌ Don't do this
            
            # Use class methods instead
            MyProvider.some_method()  # ✅ Correct usage
            ```
        """
        raise RuntimeError(
            f"{cls.__name__} is a singleton provider and cannot be instantiated. "
            "Use class methods directly instead."
        )

    @classmethod
    def initialize(cls) -> None:
        """Initialize the provider's resources and state.
        
        This method is called automatically by the framework when the provider
        is first accessed. Override this method to set up any resources your
        provider needs, such
        
        The method should be idempotent and should not call other @guarded methods
        from the same provider, as this will raise a SelfDependencyError.
        
        Raises:
            Exception: Any exception to indicate initialization failure.
            The framework will wrap this in a ProviderInitializationError.
        
        Note:
            - This method is called exactly once per provider during the application lifecycle
            - Dependencies are guaranteed to be initialized before this method is called
            - If initialization fails, the provider will not be marked as initialized
            - Don't call @guarded methods from this provider within initialize()
        
        Example:
            ```python
            class DatabaseProvider(BaseProvider):
                _connection: ClassVar[Connection | None] = None
                _pool: ClassVar[ConnectionPool | None] = None
                
                @classmethod
                def initialize(cls) -> None:
                    # Set up database connection
                    cls._connection = create_connection(DATABASE_URL)
                    cls._pool = create_pool(DATABASE_URL, max_connections=10)
                    
                    # Run any setup queries
                    cls._connection.execute("SELECT 1")  # Test connection
            ```
        """

    @classmethod
    def ping(cls) -> bool:
        """Perform a health check to verify the provider is working correctly.
        
        This method is called automatically after initialize() to verify that
        the provider was set up correctly. Override this method to implement
        provider-specific health checks.
        
        Returns:
            bool: True if the provider is healthy and ready to use, False otherwise.
        
        Raises:
            Exception: Any exception indicates the provider is unhealthy.
            The framework will wrap this in a ProviderInitializationError.
        
        Note:
            - Called immediately after initialize() during provider startup
            - Should be fast and lightweight (avoid expensive operations)
            - Should test the core functionality without side effects
            - If this returns False or raises an exception, provider initialization fails
        
        Example:
            ```python
            class DatabaseProvider(BaseProvider):
                @classmethod
                def ping(cls) -> bool:
                    # Quick health check
                    if cls._connection is None:
                        return False
                    
                    try:
                        # Test basic connectivity
                        result = cls._connection.execute("SELECT 1")
                        return result is not None
                    except Exception:
                        return False
            
            class APIClientProvider(BaseProvider):
                @classmethod
                def ping(cls) -> bool:
                    # Check if we have valid credentials
                    return cls._api_key is not None and len(cls._api_key) > 0
            ```
        """
        return True

    @classmethod
    def _get_all_dependencies(cls) -> set[type["BaseProvider"]]:
        """Get all dependencies recursively for this provider.
        
        This internal method traverses the dependency graph to find all providers
        that this provider depends on, directly or indirectly.
        
        Returns:
            set[type[BaseProvider]]: All providers in the dependency tree.
            
        Note:
            This is an internal method used by the framework for dependency resolution.
            It performs a depth-first traversal of the dependency graph.
        """
        deps = set(cls._dependencies)
        for dep in cls._dependencies:
            deps.update(dep._get_all_dependencies())
        return deps

    @classmethod
    def _raise_on_circular_dependencies(
        cls,
        visited: set[type["BaseProvider"]] | None = None,
        recursion_stack: set[type["BaseProvider"]] | None = None,
    ) -> None:
        """Check for circular dependencies using depth-first search.
        
        This method performs cycle detection in the dependency graph using DFS.
        If a circular dependency is found, it raises an exception with details
        about the providers involved in the cycle.
        
        Args:
            visited: Set of providers already visited during traversal.
            recursion_stack: Current path in the DFS traversal.
            
        Raises:
            CircularDependencyError: If a circular dependency is detected.
            
        Note:
            This is an internal method used by the framework before initialization.
            The algorithm uses DFS with a recursion stack to detect back edges,
            which indicate cycles in the dependency graph.
        """
        if visited is None:
            visited = set()
        if recursion_stack is None:
            recursion_stack = set()

        if cls in recursion_stack:
            raise CircularDependencyError(
                f"Circular dependency in {cls.__name__}: "
                f"{', '.join([d.__name__ for d in recursion_stack])}"
            )

        if cls in visited:
            return

        visited.add(cls)
        recursion_stack.add(cls)

        for dep in cls._dependencies:
            dep._raise_on_circular_dependencies(visited, recursion_stack)

        recursion_stack.remove(cls)

    @classmethod
    def _get_initialization_order(cls) -> list[type["BaseProvider"]]:
        """Determine the correct initialization order using topological sort.
        
        This method analyzes the dependency graph and returns providers in the order
        they should be initialized, ensuring that dependencies are always initialized
        before the providers that depend on them.
        
        Returns:
            list[type[BaseProvider]]: Providers ordered for safe initialization.
            
        Raises:
            CircularDependencyError: If the dependency graph contains cycles.
            
        Note:
            This is an internal method that implements Kahn's algorithm for topological sorting.
            The algorithm builds a dependency graph and processes nodes with no incoming edges,
            ensuring a valid initialization order.
        """
        # Build dependency graph
        graph = defaultdict(set)
        in_degree = defaultdict(int)

        # Add all dependencies to the graph
        all_deps = cls._get_all_dependencies()
        all_deps.add(cls)

        for provider in all_deps:
            for dep in provider._dependencies:
                graph[dep].add(provider)
                in_degree[provider] += 1

        # Topological sort
        result = []
        queue = [p for p in all_deps if in_degree[p] == 0]

        while queue:
            provider = queue.pop(0)
            result.append(provider)

            for dependent in graph[provider]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(result) != len(all_deps):
            raise CircularDependencyError(
                "Circular dependency detected in the dependency graph"
            )

        return result

    @classmethod
    def _initialize_impl(cls) -> None:
        """Internal implementation of provider initialization workflow.
        
        This method orchestrates the complete initialization process for a provider:
        1. Calls the user-defined initialize() method
        2. Performs a health check using ping()
        3. Marks the provider as initialized if successful
        
        The method provides error handling and meaningful error messages for
        initialization failures.
        
        Raises:
            ProviderInitializationError: If initialize() raises an exception,
            ping() returns False, or ping() raises an exception.
            
        Note:
            This is an internal method called by the @guarded decorator.
            It should not be called directly by user code.
        """
        logger.debug(f"Initializing {cls.__name__} provider...")
        cls.initialize()
        logger.debug(f"Provider {cls.__name__} initialized")

        # Verify that the provider is correctly initialized
        logger.debug(f"Pinging {cls.__name__} provider...")
        try:
            ping_result = cls.ping()
        except Exception as e:
            raise ProviderInitializationError(
                f"Provider {cls.__name__} failed to initialize "
                f"because its ping method raised an exception: {e}"
            ) from e

        if not ping_result:
            raise ProviderInitializationError(
                f"Provider {cls.__name__} failed to initialize "
                "because its ping method did not return True"
            )
        
        # Mark the provider as initialized
        logger.info(f"Provider {cls.__name__} initialized successfully")
        cls._initialized = True
