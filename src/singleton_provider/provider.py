from abc import ABC

from ._internal._meta import _ProviderMeta


__all__ = ["BaseProvider"]


class BaseProvider(ABC, metaclass=_ProviderMeta):

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
            @initialize
            def get_user(cls, user_id: int) -> User | None:
                return cls._users.get(user_id)
        ```
    """
    __provider_initialized__: bool = False
    __provider_dependencies__: set[type["BaseProvider"]] = set()

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
    def initialize(cls) -> bool | None:
        """Initialize the provider's resources and state.
        
        This method is called automatically by the framework when the provider
        is first accessed. Override this method to set up any resources your
        provider needs, such as database connections, API clients, or other
        external resources.
        
        The method should be idempotent and should not call other @initialize methods
        from the same provider, as this will raise a SelfDependencyError.
        
        Returns:
            bool | None: False if initialization failed. Can optionally return
            True if initialization was successful. If None is returned, the
            provider is also considered initialized.

        Raises:
            SelfDependencyError: If 
        
        Note:
            - This method is called exactly once per provider during the application lifecycle
            - Don't call this method directly anywhere.
        
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
