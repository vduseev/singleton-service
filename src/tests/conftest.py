import asyncio
import sys

import pytest

from singleton_provider import BaseProvider, init, requires
from singleton_provider._internal._metaclass import ProviderMetaclass


class UsersDatabase(BaseProvider):
    _init_counter = 0
    _users: dict[int, str] = {}

    @classmethod
    def initialize(cls):
        cls._users = {1: "john", 2: "jane"}
        cls._init_counter += 1
    
    @init
    def add(cls, id: int, name: str) -> None:
        cls._users[id] = name


@requires(UsersDatabase)
class UsersCacheProvider(BaseProvider):
    _init_counter = 0
    _refresh_counter = 0
    _access_counter = 0
    _access_limit = 2
    users: list[str]

    @classmethod
    def initialize(cls):
        cls._refresh()
        cls._init_counter += 1

    @classmethod
    def _refresh(cls):
        cls.users = UsersDatabase.fetch()
        cls._access_counter = 0
        cls._refresh_counter += 1

    @init
    def get(cls) -> str:
        cls._access_counter += 1
        if cls._access_counter > cls._access_limit:
            cls._refresh()
        return cls.users
    

class UsersService(BaseProvider):
    _init_counter = 0
    
    @classmethod
    def initialize(cls):
        cls._init_counter += 1
    
    @init
    async def fetch(cls) -> str:
        await asyncio.sleep(0)  # Yield control to event loop
        return "async_data"



@pytest.fixture
def clean_sys_modules():
    """Remove any test providers from sys.modules after each test."""
    yield
    # Clean up any dynamically created provider classes
    to_remove = []
    for module_name in sys.modules:
        if module_name.startswith("test_") or "conftest" in module_name:
            to_remove.append(module_name)
    
    for module_name in to_remove:
        if module_name in sys.modules:
            del sys.modules[module_name]
    
    # Reset metaclass state
    ProviderMetaclass.__provider_configured__ = False
    ProviderMetaclass.__provider_setup_hook_ = None
