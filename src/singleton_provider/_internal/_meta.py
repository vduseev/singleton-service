from __future__ import annotations
from types import FunctionType
from typing import Any, Callable, Self

from ._guarded import GuardedAttribute, GuardedMethod, protected


__all__ = ["_ProviderMeta", "setup"]


def setup(func: Callable) -> Callable:
    """Decorator to mark a function as the provider setup function."""
    _ProviderMeta.__provider_setup__ = func  # type: ignore[attr-defined]
    return func


class _ProviderMeta(type):
    __provider_configured__: bool = False
    __provider_setup__: Callable | None = None

    def __new__(
        mcls: type[Self],
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        /,
        **kwds: Any,
    ) -> Self:
        # All providers must define an initialize() class method.
        if "initialize" not in namespace:
            raise TypeError(f"{name} must define an initialize() class method")
        
        if not isinstance(namespace["initialize"], classmethod):
            raise TypeError(
                f"{name}.initialize() method must be decorated with "
                "@classmethod to comply with the provider protocol"
            )

        # All other methods must be decorated with @classmethod or
        # @staticmethod.
        for attr, value in namespace.items():
            if isinstance(value, FunctionType):
                raise TypeError(
                    f"{name}.{attr} must be decorated with @classmethod "
                    "or @staticmethod to comply with the provider protocol"
                )

        annotations: dict[str, Any] = namespace.get("__annotations__", {})
        new_ns: dict[str, Any] = {}

        def _initialize_plug(*args: Any, **kwargs: Any) -> None:
            """Prevent users from calling initialize() directly.
            
            The initialize() method is only meant to be called by the provider
            initialization process.
            """
            raise RuntimeError("initialize() method cannot be called directly.")

        for attr, value in namespace.items():
            if attr == "initialize":
                # The mandatory initialize() method is hijacked and hidden
                # from the user.
                new_ns["__provider_initialize__"] = value
                new_ns["initialize"] = classmethod(_initialize_plug)
            elif isinstance(value, protected):
                # Protected methods are passed as is, even though they are
                # simply class methods.
                new_ns[attr] = value
            elif isinstance(value, classmethod):
                # All other methods are wrapped with a guard which also
                # turns them into class methods.
                new_ns[attr] = GuardedMethod(value)
            else:
                # Non-function attributes and static methods are passed as is.
                new_ns[attr] = value

        # Every non-function attribute that only has a type hint and has no
        # value is turned into a GuardedAttribute, which means accessing that
        # attribute will force the provider to be initialized.
        for attr, hint in annotations.items():
            if attr not in new_ns:
                new_ns[attr] = GuardedAttribute()

        cls = super().__new__(mcls, name, bases, new_ns)
        return cls
