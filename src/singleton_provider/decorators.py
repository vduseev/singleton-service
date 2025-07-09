"""Decorators for singleton provider dependency management.

This module provides decorators that enable the core functionality of the
singleton-provider framework: dependency declaration and initialization
guarantees.

The module contains two main decorators:
- @requires: Declares dependencies between providers
- @guarded: Ensures providers are initialized before method execution

Example:
    Basic usage of both decorators:
    
    ```python
    from singleton_provider import BaseProvider, requires, guarded
    
    @requires(DatabaseProvider, CacheProvider)
    class UserProvider(BaseProvider):
        _users: ClassVar[Dict[int, User]] = {}
        
        @classmethod
        def initialize(cls) -> None:
            cls._users = DatabaseProvider.load_users()
            
        @guarded
        def get_user(cls, user_id: int) -> User | None:
            # DatabaseProvider and CacheProvider guaranteed to be initialized
            return cls._users.get(user_id)
    ```
"""
import inspect
import logging
from collections.abc import Awaitable, Callable, Coroutine
from functools import wraps
from typing import (
    Any,
    TypeVar,
    ParamSpec,
    Concatenate,
    overload,
    cast,
)

from .base_provider import BaseProvider
from .exceptions import (
    ProviderInitializationError,
    SelfDependencyError,
)


logger = logging.getLogger(__name__)

_P = ParamSpec("_P")
_R = TypeVar("_R")
_T = TypeVar("_T")
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
    def decorator(cls: _BaseProviderT) -> _BaseProviderT:
        cls._dependencies = set(dependencies)
        return cls

    return decorator



class Guarded(classmethod):
    """A `classmethod` subclass for the @guarded decorator return value.

    Providing `__call__` makes the object *also* usable as a callable, so that
    another `@classmethod` can safely wrap it.
    """

    __func__: Callable[..., Any]

    def __init__(self, func: Callable[..., Any], /) -> None:
        super().__init__(func)
        if inspect.iscoroutinefunction(func):
            self._is_coroutine = True

    def __call__(self, *args: Any, **kwargs: Any):
        return self.__func__(*args, **kwargs)


def guarded(
    func: Callable[Concatenate[type[_T], _P], _R] | classmethod,
    /,
) -> Guarded:
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

    def _validate(
        cls: type[_T],
        method: Callable[Concatenate[type[_T], _P], _R],
    ) -> type[BaseProvider]:
        """Get the class of the decorated method.

        Raises:
            `ValueError`: If the function is not a method of the class
            or the class is not a subclass of BaseProvider.
        """
        if not issubclass(cls, BaseProvider):
            raise ValueError(
                f"Class '{cls.__name__}' for the method "
                f"{method.__qualname__} is not a subclass of BaseProvider."
            ) 

        # Ensure the function is actually part of this class. This check is
        # important because __qualname__ could be misleading if a function
        # is defined inside another function within a class, though that's a
        # rare case for methods. We're assuming decorated functions are
        # direct attributes of the class or its instances.
        if not hasattr(cls, method.__name__):
            raise ValueError(
                f"Function {method.__qualname__} is not a method of "
                f"class {cls.__name__}."
            )

    def _raise_on_self_dependency(cls: type) -> None:
        frame = inspect.currentframe()
        try:
            while frame:
                if frame.f_code.co_qualname.endswith(
                    f"{cls.__name__}.initialize",
                ):
                    raise SelfDependencyError(
                        f"Guarded method {func.__qualname__} was invoked "
                        "inside the initialize() method of its class "
                        f"{cls.__name__}. Guarded methods cannot "
                        "be called from the initialize() method."
                    )
                frame = frame.f_back
        finally:
            del frame

    def _initialize_all(
        cls: _BaseProviderT,
        requested_for: str | None = None,
    ) -> None:
        logger.debug(
            f"Singleton {cls.__name__} requires initialization"
            f"{' for ' + requested_for if requested_for else ''}"
        )
        # Check for circular dependencies
        cls._raise_on_circular_dependencies()

        # Raise an error if the @guarded decorator function is called
        # from the initialize method of the provider.
        _raise_on_self_dependency(cls)

        # Make sure all dependencies of this provider are initialized
        init_order = cls._get_initialization_order()
        logger.debug(
            f"Initialization order for {cls.__name__} is "
            f"{', '.join(provider.__name__ for provider in init_order)}"
        )
        for dep in init_order:
            if dep._initialized:
                logger.debug(
                    f"Dependency {dep.__name__} of "
                    f"{cls.__name__} is already initialized"
                )
            else:
                try:
                    dep._initialize_impl()
                except Exception as e:
                    who = cls.__name__
                    why = dep.__name__
                    cause = f" because of {why}" if who != why else ""
                    raise ProviderInitializationError(
                        f"Failed to initialize {who}{cause}: {e}"
                    ) from e
                    
    def _wrap(
        f: Callable[Concatenate[type[_T], _P], _R]
    ) -> Callable[Concatenate[type[_T], _P], _R]:
        if inspect.iscoroutinefunction(f):
            @wraps(f)
            async def async_wrapper(
                cls: _BaseProviderT, *args: _P.args, **kwargs: _P.kwargs
            ) -> _R:  # type: ignore[override]
                _validate(cls, f)
                if not cls._initialized:
                    _initialize_all(cls)
                return await f(cls, *args, **kwargs)

            return async_wrapper  # type: ignore[return-value]

        @wraps(f)
        def sync_wrapper(
            cls: _BaseProviderT, *args: _P.args, **kwargs: _P.kwargs
        ) -> _R:  # type: ignore[override]
            _validate(cls, f)
            if not cls._initialized:
                _initialize_all(cls)
            return f(cls, *args, **kwargs)

        return sync_wrapper  # type: ignore[return-value]
    
    # Unwrap if we received an already decorated class method
    func_ = func.__func__ if isinstance(func, classmethod) else func  # type: ignore[arg-type]

    # Add guard logic
    guarded_func = _wrap(func_)  # type: ignore[arg-type]

    # Hand it back as a class method descriptor
    return Guarded(guarded_func)  # type: ignore[return-value]
