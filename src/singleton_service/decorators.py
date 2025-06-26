import inspect
from functools import wraps
from typing import (
    Any,
    Type,
    Callable,
    Coroutine,
    TypeVar,
    ParamSpec,
    Concatenate,
    overload,
    cast,
)

from .base_service import BaseService
from .exceptions import (
    ServiceInitializationError,
    SelfDependencyError,
)


P = ParamSpec("P")
R = TypeVar("R")

# DecoratedServiceT represents the specific class type
# (e.g., Type[MyService]) that the decorator @requires is applied to.
DecoratedServiceT = TypeVar(
    "DecoratedServiceT", bound=Type["BaseService"]
)

# DecoratedServiceOfMethodT represents the specific class type
# (e.g., Type[MyService]) that the method decorated with @guarded belongs to.
DecoratedServiceOfMethodT = TypeVar(
    "DecoratedServiceOfMethodT", bound=Type["BaseService"]
)


def requires(
    *dependencies: Type[BaseService],
) -> Callable[[DecoratedServiceT], DecoratedServiceT]:
    """List other singleton services that this service depends on.

    Decorate the service class with it:
        @requires(ServiceA, ServiceB)
        class MyService(BaseService):
            pass

    """
    def decorator(cls: DecoratedServiceT) -> DecoratedServiceT:
        cls._dependencies = set(dependencies)
        return cls

    return decorator


def _get_service_of_method(
    func: Callable[..., Any],
) -> Type[BaseService]:
    """Get the class of the decorated method.

    Returns:
        The class of the decorated method.

    Raises:
        ValueError: If the function is not a method or if the class can't be
        determined.
    """
    # Example: func.__qualname__ could be 'MyService.my_method' or
    # 'Outer.Inner.method'
    qualname_parts = func.__qualname__.split(".")

    if len(qualname_parts) < 2:  # Must be at least 'ClassName.method_name'
        raise ValueError(
            f"Function {func.__name__} has a qualname '{func.__qualname__}' "
            "that is too short to be a method."
        )

    potential_class_name_parts = qualname_parts[:-1]
    method_name = qualname_parts[-1]

    # Resolve the class from globals
    current_obj: Any = func.__globals__.get(potential_class_name_parts[0])
    if current_obj is None:
        raise ValueError(
            f"Could not find top-level class/module "
            f"'{potential_class_name_parts[0]}' for "
            f"the method {func.__qualname__} in globals."
        )

    for i in range(1, len(potential_class_name_parts)):
        part = potential_class_name_parts[i]
        if not hasattr(current_obj, part):
            potential_name = ".".join(potential_class_name_parts[: i + 1])
            raise ValueError(
                f"Could not resolve potential class/module name "
                f"'{potential_name}' for the method {func.__qualname__}."
            )
        current_obj = getattr(current_obj, part)

    if not inspect.isclass(current_obj):
        raise ValueError(
            f"Resolved object '{'.'.join(potential_class_name_parts)}' for "
            f"the method {func.__qualname__} is not a class."
        )

    if not issubclass(current_obj, BaseService):
        raise ValueError(
            f"Class '{current_obj.__name__}' for the method "
            f"{func.__qualname__} is not a subclass of BaseService."
        )

    # Ensure the function is actually part of this class. This check is
    # important because __qualname__ could be misleading if a function
    # is defined inside another function within a class, though that's a
    # rare case for methods. We're assuming decorated functions are
    # direct attributes of the class or its instances.
    if not hasattr(current_obj, method_name):
        raise ValueError(
            f"Function {func.__qualname__} is not an attribute of "
            f"resolved class {current_obj.__name__}."
        )

    return cast(Type[BaseService], current_obj)


@overload
def guarded(
    func: Callable[
        Concatenate[DecoratedServiceOfMethodT, P], Coroutine[Any, Any, R]
    ],
) -> Callable[P, Coroutine[Any, Any, R]]: ...


@overload
def guarded(
    func: Callable[Concatenate[DecoratedServiceOfMethodT, P], R],
) -> Callable[P, R]: ...


def guarded(func: Callable[..., Any]) -> Callable[..., Any]:
    """Ensure the singleton and its dependencies are initialized before
    this method is called.

    Initialization is performed at runtime and involves the whole graph
    of dependencies. If the singleton and all dependencies are already
    initialized, this decorator does nothing.

    Example:
        @requires(ServiceA, ServiceB)
        class MyService(BaseService):

            @classmethod
            @guarded
            def my_method(cls):
                pass
    """
    # We perform all actions related to evaluation and initialization of
    # the dependencies at runtime, when the decorated method is called.
    # This is because we want to make sure that the developer had a chance
    # to declare everything before running and we know the full picture.

    def raise_on_self_dependency(current_cls: Type[BaseService]) -> None:
        frame = inspect.currentframe()
        try:
            while frame:
                if frame.f_code.co_name == "initialize":
                    raise SelfDependencyError(
                        f"Guarded method {func.__qualname__} was invoked "
                        "inside the initialize() method of its class "
                        f"{current_cls.__name__}. Guarded methods cannot "
                        "be called from the initialize() method."
                    )
                frame = frame.f_back
        finally:
            del frame

    def initialize_if_not_initialized(current_cls: Type[BaseService]) -> None:
        if not current_cls._initialized:
            # Check for circular dependencies
            current_cls._raise_on_circular_dependencies()

            # Raise an error if the @guarded decorator function is called
            # from the initialize method of the service.
            raise_on_self_dependency(current_cls)

            # Make sure all dependencies of this service are initialized
            init_order = current_cls._get_initialization_order()
            for service_in_order in init_order:
                if not service_in_order._initialized:
                    try:
                        service_in_order._initialize_impl()
                    except Exception as e:
                        who = current_cls.__name__
                        why = service_in_order.__name__
                        cause = f" because of {why}" if who != why else ""
                        raise ServiceInitializationError(
                            f"Failed to initialize {who}{cause}: {e}"
                        )

    if inspect.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(
            *args: P.args, **kwargs: P.kwargs
        ) -> Coroutine[Any, Any, R]:
            service_class_obj = _get_service_of_method(func)
            initialize_if_not_initialized(service_class_obj)

            # Cast func to its specific expected async signature for the call
            async_func = cast(
                Callable[
                    Concatenate[Type[BaseService], P], Coroutine[Any, Any, R]
                ],
                func,
            )
            return await async_func(*args, **kwargs)

        return async_wrapper

    else:
        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            service_class_obj = _get_service_of_method(func)
            initialize_if_not_initialized(service_class_obj)

            # Cast func to its specific expected sync signature for the call
            sync_func = cast(
                Callable[Concatenate[Type[BaseService], P], R], func
            )
            return sync_func(*args, **kwargs)

        return sync_wrapper
