import pytest

from singleton_provider import BaseProvider, init, setup
from singleton_provider.provider import ProviderMetaclass
from singleton_provider.exceptions import ProviderDefinitionError


def test_setup_runs_once(clean_sys_modules):
    setup_counter = 0
    
    @setup
    def test_setup():
        nonlocal setup_counter
        setup_counter += 1

    assert ProviderMetaclass.__provider_setup_hook__ is test_setup
    
    class Provider1(BaseProvider):
        _sdata: str
        _init_counter = 0

        @classmethod
        def initialize(cls):
            cls._data = "data1"
            cls._init_counter += 1
        
        @init
        def set_data(cls, data: str):
            cls._data = data
    
    class Provider2(BaseProvider):
        data: str
        _init_counter = 0

        @classmethod
        def initialize(cls):
            cls.data = "data2"
            cls._init_counter += 1
    
    # Access first provider - should trigger setup
    Provider1.set_data("data1-modified")
    assert setup_counter == 1
    assert Provider1._init_counter == 1
    assert Provider2._init_counter == 0
    
    # Access second provider - setup should not run again
    assert Provider2.data == "data2"
    assert setup_counter == 1
    assert Provider1._init_counter == 1
    assert Provider2._init_counter == 1
    

def test_setup_raises_if_coroutine(clean_sys_modules):
    with pytest.raises(ProviderDefinitionError, match="is a coroutine and cannot be used as a setup function"):
        @setup
        async def test_setup():
            pass


def test_setup_raises_if_expects_arguments(clean_sys_modules):
    with pytest.raises(ProviderDefinitionError, match="is a function that expects arguments and cannot be used as a setup function"):
        @setup
        def test_setup(arg: str):
            pass
