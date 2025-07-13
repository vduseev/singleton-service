import inspect
import logging
from collections.abc import Callable
from functools import wraps
from typing import (
    Any,
    TypeVar,
    Generic,
    ParamSpec,
    Concatenate,
)

from ..provider import BaseProvider
from ..exceptions import (
    AttributeNotInitialized,
    GuardedAttributeAssignment,
    SelfDependency,
)
from ._provider import _initialize_provider_chain


_P = ParamSpec("_P")
_R = TypeVar("_R")
_T = TypeVar("_T")


logger = logging.getLogger("singleton_provider")
__all__ = ["GuardedMethod", "GuardedAttribute", "protected"]


def _validate_guarded_method(
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
    
    # Raise an error if the @initialize decorator function is called
    # from the initialize method of the provider.
    frame = inspect.currentframe()
    try:
        while frame:
            if frame.f_code.co_qualname.endswith(
                f"{cls.__name__}.initialize",
            ):
                raise SelfDependency(
                    f"Guarded method {method.__qualname__} was invoked "
                    "inside the initialize() method of its class "
                    f"{cls.__name__}. Guarded methods cannot "
                    "be called from the initialize() method."
                )
            frame = frame.f_back
    finally:
        del frame

                
def _wrap_guarded_method(
    f: Callable[Concatenate[type[_T], _P], _R]
) -> Callable[Concatenate[type[_T], _P], _R]:
    if inspect.iscoroutinefunction(f):
        @wraps(f)
        async def async_wrapper(
            cls: type[BaseProvider], *args: _P.args, **kwargs: _P.kwargs
        ) -> _R:  # type: ignore[override]
            if not cls.__provider_initialized__:
                _validate_guarded_method(cls, f)
                _initialize_provider_chain(cls)
            return await f(cls, *args, **kwargs)

        return async_wrapper  # type: ignore[return-value]

    @wraps(f)
    def sync_wrapper(
        cls: type[BaseProvider], *args: _P.args, **kwargs: _P.kwargs
    ) -> _R:  # type: ignore[override]
        if not cls.__provider_initialized__:
            _validate_guarded_method(cls, f)
            _initialize_provider_chain(cls)
        return f(cls, *args, **kwargs)

    return sync_wrapper  # type: ignore[return-value]


class protected(classmethod):
    """Allow the class method to be used without initializing the provider."""


class GuardedMethod(classmethod):
    """Require the class method to be initialized inside initialize()."""

    # TODO? explicit type hints?
    __func__: Callable[..., Any]

    def __init__(self, func: Callable[Concatenate[type[_T], _P], _R], /) -> None:
        guarded_func = _wrap_guarded_method(func)

        super().__init__(guarded_func)
        if inspect.iscoroutinefunction(guarded_func):
            self._is_coroutine = True

    def __call__(self, *args: Any, **kwargs: Any):
        return self.__func__(*args, **kwargs)
    

class GuardedAttribute(Generic[_T]):
    """Require the provider attribute to be initialized inside initialize()."""
    _UNSET = object()

    def __init__(self) -> None:
        self._slot_name: str | None = None

    def __set_name__(self, owner: type[BaseProvider], name: str) -> None:
        self._slot_name = f"__{owner.__name__}_{name}"

    def __get__(self, instance, owner: type[BaseProvider] | None = None) -> _T:
        cls = owner or type(instance)
        if not cls.__provider_initialized__:
            _initialize_provider_chain(cls, requested_for=self._slot_name or "<attr>")
        value = getattr(cls, self._slot_name, self._UNSET)
        if value is self._UNSET:
            raise AttributeNotInitialized(cls, self._slot_name[2:])
        return value

    def __set__(self, instance, value: _T) -> None:
        cls = instance if isinstance(instance, type) else type(instance)

        frame = inspect.currentframe().f_back
        inside_init = False
        try:
            while frame:
                if frame.f_code.co_qualname.endswith(f"{cls.__name__}.initialize"):
                    inside_init = True
                    break
                frame = frame.f_back
        finally:
            del frame

        if not inside_init:
            raise GuardedAttributeAssignment(cls, self._slot_name[2:])
        setattr(cls, self._slot_name, value)
