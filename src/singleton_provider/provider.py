import inspect
from abc import ABC
from collections.abc import Callable
from typing import TypeVar

from .exceptions import ProviderDefinitionError
from ._internal._metaclass import ProviderMetaclass


_T = TypeVar("_T", bound="BaseProvider")


__all__ = ["BaseProvider", "ProviderMetaclass"]


class BaseProvider(ABC, metaclass=ProviderMetaclass):
    """Provider class.
    
    This class implements the singleton pattern by preventing instantiation and providing
    a framework for dependency management and lazy initialization
    
    Providers inherit from this class and define their logic in class methods. The framework
    automatically handles initialization order based on declared dependencies.
    
    Note:
        Providers cannot be instantiated. Attempting to create an instance will raise a RuntimeError.
        All provider state must be stored in class variables.
    
    Example:
        Creating a provider with dependencies:
        
        ```python
        @requires(DatabaseProvider, CacheProvider)
        class UserCache(BaseProvider):
            users: dict[int, User]
            refresh_timestamp: datetime
            refresh_interval: timedelta = timedelta(minutes=10)
            
            def __init__(self) -> None:
                # Load initial data
                self.refresh()

            @init
            def get_user(cls, user_id: int) -> User | None:
                if cls.refresh_timestamp < datetime.now() - cls.refresh_interval:
                    cls.refresh()
                return cls.users.get(user_id)
                
            @classmethod
            def refresh(cls) -> None:
                cls.users = DatabaseProvider.load_all_users()
                cls.refresh_timestamp = datetime.now()
        ```
    """
    __provider_initialized__: bool = False
    __provider_dependencies__: set[type[_T]] = set()
    __provider_init__: Callable[..., bool | None] | None = None
    __provider_guarded_attrs__: set[str] = set()

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
            provider = MyProvider()
            
            # Use class methods instead
            MyProvider.some_method()
            ```
        """
        raise RuntimeError(
            f"{cls.__name__} is a singleton provider and cannot be instantiated. "
            "Use class methods directly instead."
        )
