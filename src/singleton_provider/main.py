from collections.abc import Callable
from typing import Any, Concatenate, ParamSpec, TypeVar

from .provider import BaseProvider
from ._internal._guarded import GuardedMethod, GuardedAttribute


_P = ParamSpec("_P")
_R = TypeVar("_R")
_T = TypeVar("_T")


__all__ = ["BaseProvider", "requires", "initialized", "Initialized"]


def requires(
    *dependencies: type[BaseProvider],
) -> Callable[[type[BaseProvider]], type[BaseProvider]]:
    """Declare dependencies between singleton providers.
    
    This decorator is used to specify which other providers a provider depends on.
    The framework uses this information to ensure dependencies are initialized
    in the correct order before the provider itself is initialized.
    
    Args:
        *dependencies: Variable number of provider classes that this provider
        depends on. Each must be a subclass of BaseProvider.
        
    Note:
        - Circular dependencies will be detected and raise CircularDependencyError
        - Dependencies are initialized recursively (dependencies of dependencies)
        - The order of dependencies in the decorator doesn't matter
    
    Example:

        Single dependency:
        ```python
        @requires(DatabaseProvider)
        class UserProvider(BaseProvider):
            pass
        ```
        
        Multiple dependencies:
        ```python
        @requires(DatabaseProvider, CacheProvider, AuthProvider)
        class UserProvider(BaseProvider):
            pass
        ```
        
        Chained dependencies:
        ```python
        # AuthProvider depends on DatabaseProvider
        @requires(DatabaseProvider)
        class AuthProvider(BaseProvider):
            pass
            
        # UserProvider depends on AuthProvider (and transitively on DatabaseProvider)
        @requires(AuthProvider)
        class UserProvider(BaseProvider):
            pass
        ```
    """
    def decorator(cls: type[BaseProvider]) -> type[BaseProvider]:
        cls.__provider_dependencies__ = set(dependencies)
        return cls
    return decorator


def initialized(
    func: Callable[Concatenate[type[_T], _P], _R] | classmethod,
    /,
) -> GuardedMethod:
    """Ensure provider and its dependencies are initialized before method execution.
    
    This decorator guarantees that when a method is called, the provider and all
    its dependencies (direct and transitive) are properly initialized. The
    initialization happens lazily on first access and follows the correct
    dependency order.
    
    Args:
        func: The method to be guarded. Must be a @classmethod of a BaseProvider subclass.
    
    Returns:
        Wrapped method that performs initialization before calling the original method.
        
    Raises:
        ProviderInitializationError: If any provider in the dependency chain fails to initialize.
        SelfDependencyError: If called from within the same provider's initialize() method.
        CircularDependencyError: If circular dependencies are detected.
        
    Note:
        - Works with both synchronous and asynchronous methods
        - Initialization is performed only once per provider
        - Already initialized providers are skipped for performance
        - Cannot be called from within the same provider's initialize() method
        - Thread-safe (though providers themselves need to ensure thread safety)
        - Can be used as a classmethod decorator or as a standalone decorator.
        
    Examples:

        Basic usage:
        ```python
        @requires(DatabaseProvider)
        class UserProvider(BaseProvider):
            @initialize
            def get_user(cls, user_id: int) -> User:
                # DatabaseProvider guaranteed to be initialized here
                return DatabaseProvider.fetch_user(user_id)
        ```
        
        Async method:
        ```python
        @requires(APIProvider)
        class WeatherProvider(BaseProvider):
            @initialize
            async def get_weather(cls, city: str) -> Weather:
                # APIProvider guaranteed to be initialized here
                return await APIProvider.fetch_weather(city)
        ```
        
        Multiple dependencies and context manager:
        ```python
        @requires(DatabaseProvider, CacheProvider, MetricsProvider)
        class UserProvider(BaseProvider):
            @initialize
            @asynccontextmanager
            async def get_user_with_metrics(cls, user_id: int) -> AsyncGenerator[User, None]:
                # All three providers
                
                cached = CacheProvider.get(f'user:{user_id}')
                if cached:
                    yield cached
                    
                user = DatabaseProvider.fetch_user(user_id)
                CacheProvider.set(f'user:{user_id}', user)
                yield user
        ```
    """
    # We perform all actions related to evaluation and initialization of
    # the dependencies at runtime, when the decorated method is called.
    # This is because we want to make sure that the developer had a chance
    # to declare everything before running and we know the full picture.
    
    # Unwrap if we received an already decorated class method
    func_ = func.__func__ if isinstance(func, classmethod) else func

    # Hand it back as a class method descriptor
    return GuardedMethod(func_)  # type: ignore[return-value]
