from typing import (
    Callable,
    Concatenate,
    Generic,
    ParamSpec,
    TypeVar,
    overload,
)
from .base_provider import BaseProvider


_T = TypeVar("_T")
"""Type of the BaseProvider class"""
_P = ParamSpec("_P")
"""Parameters of the decorated method, except cls itself."""
_R_co = TypeVar("_R_co", covariant=True)
"""Return type of the decorated method (covariant).

Covariant, because the @guarded decorator only uses _R_co to define what
is being returned. It doesn't modify it or accept it as an argument.
"""
_BaseProviderT = TypeVar("_BaseProviderT", bound=BaseProvider)


def requires(
    *dependencies: _BaseProviderT,
) -> Callable[[_BaseProviderT], _BaseProviderT]:
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
    ...


class guarded(Generic[_T, _P, _R_co]):
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
            @guarded
            def get_user(cls, user_id: int) -> User:
                # DatabaseProvider guaranteed to be initialized here
                return DatabaseProvider.fetch_user(user_id)
        ```
        
        Async method:
        ```python
        @requires(APIProvider)
        class WeatherProvider(BaseProvider):
            @guarded
            async def get_weather(cls, city: str) -> Weather:
                # APIProvider guaranteed to be initialized here
                return await APIProvider.fetch_weather(city)
        ```
        
        Multiple dependencies and context manager:
        ```python
        @requires(DatabaseProvider, CacheProvider, MetricsProvider)
        class UserProvider(BaseProvider):
            @guarded
            @asynccontextmanager
            async def get_user_with_metrics(cls, user_id: int) -> AsyncGenerator[User, None]:
                # All three providers guaranteed to be initialized here
                MetricsProvider.increment('user_requests')
                
                cached = CacheProvider.get(f'user:{user_id}')
                if cached:
                    yield cached
                    
                user = DatabaseProvider.fetch_user(user_id)
                CacheProvider.set(f'user:{user_id}', user)
                yield user
        ```
    """

    # the decorated method itself
    @property
    def __func__(self) -> Callable[Concatenate[type[_T], _P], _R_co]: ...

    def __init__(
        self,
        f: Callable[Concatenate[type[_T], _P], _R_co],
        /,
    ) -> None: ...

    # remove the first `cls` parameter
    @overload
    def __get__(
        self,
        instance: _T,
        owner: type[_T] | None = None,
        /,
    ) -> Callable[_P, _R_co]: ...
    @overload
    def __get__(
        self,
        instance: None,
        owner: type[_T],
        /,
    ) -> Callable[_P, _R_co]: ...

    # helpers for `functools.wraps`
    __name__: str
    __qualname__: str
    @property
    def __wrapped__(self) -> Callable[Concatenate[type[_T], _P], _R_co]: ...

    # if guarded was decorated with @classmethod, this will be a callable
    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R_co: ...
    _is_coroutine: bool
