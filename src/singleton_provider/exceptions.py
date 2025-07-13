class ProviderError(Exception):
    """Base exception for all singleton provider framework errors.
    
    This is the root exception class for all errors that can occur within
    the singleton-provider framework. Catching this exception will catch
    any framework-specific error.
    
    Use this when you want to handle any provider-related error generically,
    or when implementing error handling that should catch all framework errors.
    
    Example:
        ```python
        try:
            MyProvider.do_something()
        except ProviderError as e:
            # Handle any framework error
            logger.error(f"Provider framework error: {e}")
        ```
    """
    
    message: str
    """Human-readable error message describing what went wrong."""
    
    def __init__(self, message: str = ""):
        self.message = message
        super().__init__(message)


class CircularDependency(ProviderError):
    """Raised when circular dependencies are detected in the provider graph.
    
    This error occurs when providers have dependencies that form a cycle,
    making it impossible to determine a valid initialization order.
    
    The framework detects circular dependencies before initialization
    and provides information about which providers are involved in the cycle.
    
    Example:
        ```python
        @requires(ProviderB)
        class ProviderA(BaseProvider):
            pass
            
        @requires(ProviderA)  # Creates a cycle: A -> B -> A
        class ProviderB(BaseProvider):
            pass
        ```
    """
    
    def __init__(
        self,
        name: str,
        recursion_stack: list[str],
    ):
        super().__init__(
            f"Circular dependency in provider {name} within "
            f"recursion stack: {', '.join(recursion_stack)}"
        )


class InitializationOrderMismatch(ProviderError):
    """Failed to determine a valid initialization order of providers.
    
    This error occurs when the framework is unable to determine a valid
    initialization order for the provider and its dependencies. The number
    of all dependencies within the initialization chain does not match the
    the initialization order length.
    """

    def __init__(self, name: str, order: list[str], dependencies: list[str]):
        super().__init__(
            f"Number of dependencies for provider {name} does not match "
            f"the initialization order. Order: {', '.join(order)}. "
            f"Dependencies: {', '.join(dependencies)}"
        )


class SetupError(ProviderError):
    """Raised when a provider fails to setup properly.
    
    This error occurs when the provider's setup() method raises an exception.
    """
    
    def __init__(self, exception: Exception):
        super().__init__(
            f"Error while invoking the setup function: {exception}"
        )


class DependencyNotInitialized(ProviderError):
    """Raised when a dependency provider is not properly initialized.
    
    This error occurs when a provider tries to access a dependency that
    has not been initialized yet. This should not happen when using
    @initialize methods properly, but may occur if providers are accessed
    directly without the decorator.
    
    Note:
        This error indicates a programming error in provider usage.
        Always use @initialize methods to access providers.
    """
    
    def __init__(self, provider_name: str, dependency_name: str):
        message = (
            f"Provider '{provider_name}' tried to access dependency '{dependency_name}' "
            "which is not initialized. Use @initialize methods to ensure proper initialization."
        )
        super().__init__(message)


class ProviderNotInitialized(ProviderError):
    """Raised when a provider is accessed before being initialized.
    
    This error occurs when trying to use a provider that hasn't been
    initialized yet. This should not happen when using @initialize methods
    properly.
    
    Note:
        This error indicates a programming error in provider usage.
        Always use @initialize methods to access providers.
    """
    
    def __init__(self, provider_name: str):
        message = (
            f"Provider '{provider_name}' is not initialized. "
            "Use @initialize methods to ensure proper initialization."
        )
        super().__init__(message)


class AttributeNotInitialized(ProviderError):
    """Raised when a provider attribute is accessed before being initialized.
    
    This error occurs when trying to use a provider attribute that hasn't been
    initialized yet.
    """

    def __init__(self, provider: type, attr: str):
        message = (
            f"Provider '{provider.__name__}' attribute '{attr}' was never "
            "set in initialize()."
        )
        super().__init__(message)


class GuardedAttributeAssignment(ProviderError):
    """Raised when value is assigned to a provider attribute outside of initialize()."""

    def __init__(self, provider: type, attr: str):
        message = (
            f"Provider '{provider.__name__}' attribute '{attr}' may be assigned "
            "only inside initialize()."
        )
        super().__init__(message)


class ProviderInitializationError(ProviderError):
    """Raised when a provider fails to initialize properly.
    
    This error occurs when the provider's initialize() method raises an exception.
    
    Example:
        ```python
        class DatabaseProvider(BaseProvider):
            @classmethod
            def initialize(cls) -> None:
                # This might raise an exception
                cls._connection = connect_to_database()
        ```
        
    Solutions:
        - Check that external dependencies (databases, APIs) are available
        - Verify configuration values are correct
        - Ensure required environment variables are set
        - Check network connectivity and permissions
    """
    
    def __init__(self, message: str):
        super().__init__(message)


class SelfDependency(ProviderError):
    """Raised when a provider tries to call its own @initialize methods during initialization.
    
    This error occurs when a provider's initialize() method tries to call
    other @initialize methods from the same provider. This is not allowed
    because it would create a dependency cycle within the provider itself.
    
    The framework detects this pattern by inspecting the call stack and
    raises this error to prevent infinite recursion.
    
    Example:
        This would cause a SelfDependencyError:
        ```python
        class UserProvider(BaseProvider):
            @classmethod
            def initialize(cls) -> None:
                # This is not allowed!
                cls.load_initial_data()  # Calls @initialize method
                
            @classmethod
            @initialize
            def load_initial_data(cls) -> None:
                # This method is @initialize and called from initialize()
                pass
        ```
        
    Solutions:
        - Move the logic from the @initialize method into initialize() directly
        - Create a private helper method without @initialize
        - Restructure the initialization logic to avoid self-calls
    """
    
    def __init__(self, message: str):
        super().__init__(message)
