# Singleton Provider

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/singleton-provider)
![PyPI - Status](https://img.shields.io/pypi/status/singleton-provider)
![PyPI - License](https://img.shields.io/pypi/l/singleton-provider)

Modern and type-safe abstraction for building singleton providers in Python.

* [Fantastic features](#fantastic-features)
  * [Providers can depend on each other](#provider-dependencies)
  * [Don't worry about creating instances](#no-instances)
  * [Force singletons to initialize before use](#initialized-before-use)
  * [Guarantee correct initialization order](#correct-initialization-order)
  * [Run quick health checks before launching everything](#health-checks)
* [Installation](#installation)
* [Usage](#usage)
  * [Inherit from `BaseProvider`](#inherit-from-baseprovider)
  * [Store state in `ClassVar` attributes](#use-class-attributes)
  * [`initialize` at runtime](#initialize-at-runtime)
  * [`ping` as a health check](#define-health-check)
  * [Define business logic in `@classmethod`s](#add-business-logic)
  * [List other singletons as dependencies using `@requires`](#specify-dependencies)
  * [Force everything to initialize with `@guarded`](#guard-methods)
  * [Full example](#full-example)

## Fantastic features

<a id="provider-dependencies"></a>
Providers can depend on each other.

```python
@requires(DatabaseProvider, AuthProvider)
class UsersProvider(BaseProvider):
    """Users provider that depends on DatabaseProvider and AuthProvider."""
```

<a id="no-instances"></a>
No need for instances. Just call the class methods directly **anywhere** in
your code.

```python
if __name__ == "__main__":
    print(UsersProvider.get_user(1)) # ← Just use the provider method directly
```

<a id="initialized-before-use"></a>
Ensure that all dependencies are initialized before the method is called.

```python
@requires(DatabaseProvider, AuthProvider)
class UsersProvider(BaseProvider):
    @guarded # ← Ensures that this provider and all its dependencies are
             #   initialized in the correct order before this method is called
    def get_user(cls, user_id: int) -> None:
        print(f"Getting user {user_id}")
```

<a id="correct-initialization-order"></a>
The framework guarantees the correct initialization order.

```python
@requires(DatabaseProvider, AuthProvider) # ← Needs Database and Auth providers
class UsersProvider(BaseProvider):
    @classmethod
    def initialize(cls) -> None:
        print("3. UsersProvider initialized")

    @guarded # ← Ensures that the provider and dependencies are initialized
    def get_user(cls, user_id: int) -> None:
        print(f"4. Getting user {user_id}")

@requires(DatabaseProvider) # ← Depends on DatabaseProvider only
class AuthProvider(BaseProvider):
    @classmethod
    def initialize(cls) -> None:
        print("2. AuthProvider initialized")

class DatabaseProvider(BaseProvider): # ← Doesn't depend on anything
    @classmethod
    def initialize(cls) -> None:
        print("1. DatabaseProvider initialized")

if __name__ == "__main__":
    UsersProvider.get_user(1)

# Running this will print:
# 1. DatabaseProvider initialized
# 2. AuthProvider initialized
# 3. UsersProvider initialized
# 4. Getting user 1
```

<a id="health-checks"></a>
Add a health check that will run after initialization to make sure that the
provider was initialized correctly.

```python
from aiohttp import ClientSession

@requires(DatabaseProvider) # ← Depends on DatabaseProvider only
class AuthProvider(BaseProvider):
    _session: ClientSession = None
    
    @classmethod
    def initialize(cls) -> None:
        cls._session = ClientSession()

    @classmethod
    def ping(cls) -> bool:
        # Any exception will be caught by BaseProvider and will prevent
        # the provider from being marked as initialized.
        async with cls._session.get("https://example.com/auth") as response:
            return response.status == 200
```

## Installation

The package is available on PyPI. It has no dependencies and is implemented
in pure Python. Compatible with Python 3.10 and higher.

```bash
pip install singleton-provider
```

## Usage

<a id="inherit-from-baseprovider"></a>
Create a class that inherits from `BaseProvider`

```python
from singleton_provider import BaseProvider

class WeatherProvider(BaseProvider):
    """Fetch weather data from the API."""
```

<a id="use-class-attributes"></a>
Use class attributes to store the state of the provider and to initialize
everything that can be initialized at class definition time.

Strictly speaking, you don't have to use `ClassVar` here, because it is
impossible to instantiate a class that inherits from `BaseProvider` and
therefore you'll never access the class attributes as instance attributes,
which is what would anger the type checker and why you'd want to use
`ClassVar` in the first place.

```python
from typing import ClassVar

class WeatherProvider(BaseProvider):
    _base_url: ClassVar[str] = "https://theweather.com/api"
```

<a id="initialize-at-runtime"></a>
If you need to initialize something at runtime, you can override the
`initialize` method. An example of this is when you need to initialize an
aiohttp session and the default asyncio loop should already be running by
the time you do it.

```python
from aiohttp import ClientSession
# ...

class WeatherProvider(BaseProvider):
    # ...
    _session: ClassVar[ClientSession] = None

    @classmethod
    def initialize(cls) -> None:
        cls._session = ClientSession()
```

<a id="define-health-check"></a>
Overriding the `ping` method will run a health check after the `initialize`
to make sure that the provider was initialized correctly.

```python
# ...
class WeatherProvider(BaseProvider):
    # ...
    @classmethod
    def ping(cls) -> bool:
        return cls._session.get(f"{cls._base_url}/health").status == 200
```

<a id="add-business-logic"></a>
Define the business logic of the provider using class methods.

```python
class WeatherProvider(BaseProvider):
    # ...
    @classmethod
    def get_url(cls, path: str) -> str:
        return f"{cls._base_url}/{path}"
```

<a id="specify-dependencies"></a>
Use the `@requires` decorator to list other providers that the
`WeatherProvider` depends on.

```python
@requires(GeoProvider)
class WeatherProvider(BaseProvider):
    # ...
```

<a id="guard-methods"></a>
Finally, guard the class methods that need everything to be initialized
before they are called with the `@guarded` decorator.

```python
@requires(GeoProvider)
class WeatherProvider(BaseProvider):
    # ...
    @guarded
    def get_weather(cls, city: str) -> dict:
        return cls._session.get(cls.get_url(f"weather?q={city}")).json()
```

<a id="full-example"></a>
And that's it! Here is what a complete example of a basic Weather provider
with a single dependency on a GeoProvider looks like.

```python
"""Basic example of a singleton provider."""
from aiohttp import ClientSession
from singleton_provider import BaseProvider, guarded, requires

class GeoProvider(BaseProvider):
    @classmethod
    @guarded
    def city_by_coordinates(cls, lat: float, lon: float) -> str:
        return "London"

@requires(GeoProvider)
class WeatherProvider(BaseProvider):
    # Here, we can't initialize the session in the class attribute because
    # aiohttp session requires an async loop to be running. Otherwise, it
    # will create its own loop which leads to all sorts of problems.
    _session: ClientSession = None
    # The base URL of the weather API is perfectly fine to store in the
    # class attribute.
    _base_url: str = "https://theweather.com/api"
    
    @classmethod
    def initialize(cls) -> None:
        # Properly initializing aiohttp session at runtime, when the default
        # asyncio loop is already running.
        cls._session = ClientSession()

    @classmethod
    def ping(cls) -> bool:
        # The "ping" method is called after "initialize" to check that
        # the provider was initialized correctly.
        return cls._session.get(f"{cls._base_url}/health").status == 200

    @guarded # ← Ensure that this provider and its dependencies are initialized
    def get_weather(cls, lat: float, lon: float) -> dict:
        # This is an example of the actual business logic of the provider.
        city = GeoProvider.city_by_coordinates(lat, lon)
        return cls._session.get(f"{cls._base_url}/weather?q={city}").json()

if __name__ == "__main__":
    # When the line below is executed, the WeatherProvider singleton will
    # be initialized and then the weather will be fetched. Let's try London.
    print(WeatherProvider.get_weather(51.5074, -0.1278))

    # Now try New York.
    print(WeatherProvider.get_weather(40.7128, -74.0060))
```

Let's just go through initialization order for this example. When the call
to `WeatherProvider.get_weather(51.5074, -0.1278)` is made, the following
will happen:

1. The `@guarded` decorator on the `get_weather` method will ensure that
   the `WeatherProvider` singleton and its dependency, the `GeoProvider`,
   are initialized in the correct order: `GeoProvider` then `WeatherProvider`.
2. The `GeoProvider` singleton will be initialized first. It has no runtime
   initialization logic and no `ping`, so it is quickly marked as
   initialized.
3. The `WeatherProvider` singleton will now be initialized. The `initialize`
   method will be called and will be followed by the call to `ping` to
   make sure that we can actually fetch the weather data.
4. Both singletons are now marked as initialized and `BaseProvider` will
   remember that.
5. Now, finally, the `WeatherProvider.get_weather` method can be called.
   It uses the functionality provided by the `GeoProvider` singleton and
   fetches the weather data from the API.

When the second call to `WeatherProvider.get_weather(40.7128, -74.0060)` is
made, both singletons are already initialized, and the `@guarded` decorator
quickly determines that. So the second call directly proceeds to the
`WeatherProvider.get_weather` logic and returns the weather data for New
York.
