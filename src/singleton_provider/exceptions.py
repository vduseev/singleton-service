"""Exception classes for singleton provider framework.

This module defines the exception hierarchy used throughout the singleton-provider
framework. All exceptions inherit from ProviderError, providing a common base
for catching any framework-related errors.

The exceptions are designed to provide clear error messages and help developers
understand and fix issues with their provider configurations and usage.

Example:
    Catching all provider-related errors:
    ```python
    try:
        UserProvider.get_user(123)
    except ProviderError as e:
        logger.error(f"Provider error occurred: {e}")
        # Handle any provider framework error
    ```
"""


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


class CircularDependencyError(ProviderError):
    """Raised when circular dependencies are detected in the provider graph.
    
    This error occurs when providers have dependencies that form a cycle,
    making it impossible to determine a valid initialization order.
    
    The framework detects circular dependencies before initialization
    and provides information about which providers are involved in the cycle.
    
    Attributes:
        message: Description of the circular dependency with provider names.
    
    Example:
        This would cause a CircularDependencyError:
        ```python
        @requires(ProviderB)
        class ProviderA(BaseProvider):
            pass
            
        @requires(ProviderA)  # Creates a cycle: A -> B -> A
        class ProviderB(BaseProvider):
            pass
        ```
        
    Solutions:
        - Remove one of the dependencies
        - Introduce a third provider that both can depend on
        - Refactor to eliminate the circular relationship
    """
    
    def __init__(self, message: str):
        super().__init__(message)


class DependencyNotInitializedError(ProviderError):
    """Raised when a dependency provider is not properly initialized.
    
    This error occurs when a provider tries to access a dependency that
    has not been initialized yet. This should not happen when using
    @guarded methods properly, but may occur if providers are accessed
    directly without the decorator.
    
    Note:
        This error indicates a programming error in provider usage.
        Always use @guarded methods to access providers.
    """
    
    def __init__(self, provider_name: str, dependency_name: str):
        message = (
            f"Provider '{provider_name}' tried to access dependency '{dependency_name}' "
            "which is not initialized. Use @guarded methods to ensure proper initialization."
        )
        super().__init__(message)


class ProviderNotInitializedError(ProviderError):
    """Raised when a provider is accessed before being initialized.
    
    This error occurs when trying to use a provider that hasn't been
    initialized yet. This should not happen when using @guarded methods
    properly.
    
    Note:
        This error indicates a programming error in provider usage.
        Always use @guarded methods to access providers.
    """
    
    def __init__(self, provider_name: str):
        message = (
            f"Provider '{provider_name}' is not initialized. "
            "Use @guarded methods to ensure proper initialization."
        )
        super().__init__(message)


class ProviderInitializationError(ProviderError):
    """Raised when a provider fails to initialize properly.
    
    This error occurs when:
    - The provider's initialize() method raises an exception
    - The provider's ping() method returns False
    - The provider's ping() method raises an exception
    
    The original error is typically wrapped and included in the message
    to help with debugging initialization issues.
    
    Attributes:
        message: Description of the initialization failure including the original error.
    
    Example:
        ```python
        class DatabaseProvider(BaseProvider):
            @classmethod
            def initialize(cls) -> None:
                # This might raise an exception
                cls._connection = connect_to_database()
                
            @classmethod
            def ping(cls) -> bool:
                # This might return False or raise an exception
                return cls._connection.is_alive()
        ```
        
    Solutions:
        - Check that external dependencies (databases, APIs) are available
        - Verify configuration values are correct
        - Ensure required environment variables are set
        - Check network connectivity and permissions
    """
    
    def __init__(self, message: str):
        super().__init__(message)


class SelfDependencyError(ProviderError):
    """Raised when a provider tries to call its own @guarded methods during initialization.
    
    This error occurs when a provider's initialize() method tries to call
    other @guarded methods from the same provider. This is not allowed
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
                cls.load_initial_data()  # Calls @guarded method
                
            @classmethod
            @guarded
            def load_initial_data(cls) -> None:
                # This method is @guarded and called from initialize()
                pass
        ```
        
    Solutions:
        - Move the logic from the @guarded method into initialize() directly
        - Create a private helper method without @guarded
        - Restructure the initialization logic to avoid self-calls
    """
    
    def __init__(self, message: str):
        super().__init__(message)
