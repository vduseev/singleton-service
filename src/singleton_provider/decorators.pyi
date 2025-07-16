from typing import (
    Callable,
    Concatenate,
    Generic,
    ParamSpec,
    TypeVar,
    overload,
)

from .provider import BaseProvider


_PT = TypeVar("_PT", bound=BaseProvider)
"""Type of the BaseProvider class"""
_P = ParamSpec("_P")
"""Parameters of the decorated method, except cls itself."""
_T_co = TypeVar("_T_co", covariant=True)
_R_co = TypeVar("_R_co", covariant=True)
"""Return type of the decorated method (covariant).

Covariant, because the @init decorator only uses _R_co to define what
is being returned. It doesn't modify it or accept it as an argument.
"""

class init(Generic[_PT, _P, _R_co]):
    """Ensure provider and dependencies are initialized when this method is called.

    This decorator is equivalent to @classmethod, but it also ensures that
    the provider and its dependencies are initialized before the method is
    executed.
    
    Args:
        func: The method to be guarded.
        
    Note:
        - Works with both synchronous and asynchronous methods
        - Every provider is only ever initialized once
        - Cannot be called from within the same provider's __init__() method
        
    Examples:

        Basic usage:
        ```python
        @requires(DatabaseProvider)
        class UserProvider(BaseProvider):
            @init
            def get_user(cls, user_id: int) -> User:
                # DatabaseProvider guaranteed to be initialized here
                return DatabaseProvider.fetch_user(user_id)
        ```
        
        Async method:
        ```python
        @requires(APIProvider)
        class WeatherProvider(BaseProvider):
            @init
            async def get_weather(cls, city: str) -> Weather:
                # APIProvider guaranteed to be initialized here
                return await APIProvider.fetch_weather(city)
        ```
        
        Multiple dependencies and context manager:
        ```python
        @requires(DatabaseProvider, CacheProvider, MetricsProvider)
        class UserProvider(BaseProvider):
            @init
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
    @property
    def __func__(self) -> Callable[Concatenate[type[_PT], _P], _R_co]: ...
    @property
    def __isabstractmethod__(self) -> bool: ...
    def __init__(
        self,
        f: Callable[Concatenate[type[_PT], _P], _R_co],
        /,
    ) -> None: ...
    @overload
    def __get__(
        self,
        instance: _PT,
        owner: type[_PT] | None = None,
        /,
    ) -> Callable[_P, _R_co]: ...
    @overload
    def __get__(
        self,
        instance: None,
        owner: type[_PT],
        /,
    ) -> Callable[_P, _R_co]: ...

    # helpers for `functools.wraps`
    __name__: str
    __qualname__: str
    @property
    def __wrapped__(self) -> Callable[Concatenate[type[_PT], _P], _R_co]: ...

    # # if additionally decorated with @classmethod, this will be a callable
    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R_co: ...
    _is_coroutine: bool



def requires(
    *dependencies: type[BaseProvider],
) -> Callable[[type[_PT]], type[_PT]]:
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


def setup(func: Callable[[], None]) -> Callable[[], None]:
    """Decorator to mark a function as the provider setup function.
    
    The setup function is called exactly once at the start of the application,
    when the first call to any provider is made.
    
    Example:
        ```python
        @setup
        def configure():
            logging.basicConfig(level=logging.INFO)
            warnings.filterwarnings("ignore", module="some_module")
        ```
    """
    ...
