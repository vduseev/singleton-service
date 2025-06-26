# Singleton Service

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/singleton-service)
![PyPI - Status](https://img.shields.io/pypi/status/singleton-service)
![PyPI - License](https://img.shields.io/pypi/l/singleton-service)

Modern and type-safe abstraction for building singleton services in Python.

* [Fantastic features](#fantastic-features)
  * [Singletons can depend on each other](#service-dependencies)
  * [Don't worry about creating instances](#no-instances)
  * [Force singletons to initialize before use](#initialized-before-use)
  * [Guarantee correct initialization order](#correct-initialization-order)
  * [Run quick health checks before launching everything](#health-checks)
  * [Create runnable singletons for CLI apps, web servers, etc.](#runnable-services)
* [Installation](#installation)
* [Usage](#usage)
  * [Inherit from `BaseService`](#inherit-from-baseservice)
  * [Store state in `ClassVar` attributes](#use-class-attributes)
  * [`initialize` at runtime](#initialize-at-runtime)
  * [`ping` as a health check](#define-health-check)
  * [Define business logic in `@classmethod`s](#add-business-logic)
  * [List other singletons as dependencies using `@requires`](#specify-dependencies)
  * [Force everything to initialize with `@guarded`](#guard-methods)
  * [Full example](#full-example)
* [Example: Database Service](#example-database-service)
* [Example: User Service](#example-user-service)
* [Example: Background Worker](#example-background-worker)

## Fantastic features

<a id="service-dependencies"></a>
Services can depend on each other.

```python
@requires(DatabaseService, AuthService)
class UserService(BaseService):
    """User service that depends on DatabaseService and AuthService."""
```

<a id="no-instances"></a>
No need for instances. Just call the class methods directly **anywhere** in
your code.

```python
if __name__ == "__main__":
    print(UserService.get_user(1)) # ← Just use the singleton method directly
```

<a id="initialized-before-use"></a>
Ensure that all dependencies are initialized before the method is called.

```python
@requires(DatabaseService, AuthService)
class UserService(BaseService):
    @classmethod
    @guarded # ← Ensures that this singleton and all its dependencies are
             #   initialized in the correct order before this method is called
    def get_user(cls, user_id: int) -> None:
        print(f"Getting user {user_id}")
```

<a id="correct-initialization-order"></a>
The framework guarantees the correct initialization order.

```python
@requires(DatabaseService, AuthService) # ← Needs Database and Auth singletons
class UserService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        print("3. UserService initialized")

    @classmethod
    @guarded # ← Ensures that the service and dependencies are initialized
    def get_user(cls, user_id: int) -> None:
        print(f"4. Getting user {user_id}")

@requires(DatabaseService) # ← Depends on DatabaseService only
class AuthService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        print("2. AuthService initialized")

class DatabaseService(BaseService): # ← Doesn't depend on anything
    @classmethod
    def initialize(cls) -> None:
        print("1. DatabaseService initialized")

if __name__ == "__main__":
    UserService.get_user(1)

# Running this will print:
# 1. DatabaseService initialized
# 2. AuthService initialized
# 3. UserService initialized
# 4. Getting user 1
```

<a id="health-checks"></a>
Add a health check that will run after initialization to make sure that the
service was initialized correctly.

```python
from aiohttp import ClientSession

@requires(DatabaseService)
class AuthService(BaseService):
    _session: ClientSession = None
    
    @classmethod
    def initialize(cls) -> None:
        cls._session = ClientSession()

    @classmethod
    def ping(cls) -> bool:
        # Any exception will be caught by BaseService and will prevent
        # the service from being marked as initialized.
        async with cls._session.get("https://example.com/auth") as response:
            return response.status == 200
```

<a id="runnable-services"></a>
You can also create a runnable singleton for things like CLI apps, web
servers, background workers, etc.

```python
from singleton_service import BaseRunnable, requires, guarded

@requires(DatabaseService, UsersService)
class WorkerRunnable(BaseRunnable):
    @classmethod
    async def run_async(cls) -> None:
        while True:
            print("Worker is running")
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(WorkerRunnable.run_async())
```

## Installation

The package is available on PyPI. It has no dependencies and is implemented
in pure Python. Compatible with Python 3.10 and higher.

```bash
pip install singleton-service
```

## Usage

<a id="inherit-from-baseservice"></a>
Create a class that inherits from `BaseService`

```python
from singleton_service import BaseService

class WeatherService(BaseService):
    """Fetch weather data from the API."""
```

<a id="use-class-attributes"></a>
Use class attributes to store the state of the singleton and to initialize
everything that can be initialized at class definition time.

Strictly speaking, you don't have to use `ClassVar` here, because it is
impossible to instantiate a class that inherits from `BaseService` and
therefore you'll never access the class attributes as instance attributes,
which is what would anger the type checker and why you'd want to use
`ClassVar` in the first place.

```python
from typing import ClassVar

class WeatherService(BaseService):
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

class WeatherService(BaseService):
    # ...
    _session: ClassVar[ClientSession] = None

    @classmethod
    def initialize(cls) -> None:
        cls._session = ClientSession()
```

<a id="define-health-check"></a>
Overriding the `ping` method will run a health check after the `initialize`
to make sure that the initialization was successful.

```python
# ...
class WeatherService(BaseService):
    # ...
    @classmethod
    def ping(cls) -> bool:
        return cls._session.get(f"{cls._base_url}/health").status == 200
```

<a id="add-business-logic"></a>
Define the business logic of the service using class methods.

```python
class WeatherService(BaseService):
    # ...
    @classmethod
    def get_url(cls, path: str) -> str:
        return f"{cls._base_url}/{path}"
```

<a id="specify-dependencies"></a>
Use the `@requires` decorator to list other singletons that the
`WeatherService` depends on.

```python
@requires(GeoService)
class WeatherService(BaseService):
    # ...
```

<a id="guard-methods"></a>
Finally, guard the class methods that need everything to be initialized
before they are called with the `@guarded` decorator.

```python
@requires(GeoService)
class WeatherService(BaseService):
    # ...
    @classmethod
    @guarded
    def get_weather(cls, city: str) -> dict:
        return cls._session.get(cls.get_url(f"weather?q={city}")).json()
```

<a id="full-example"></a>
And that's it! Here is what a complete example of a basic Weather service
with a single dependency on a GeoService looks like.

```python
"""Basic example of a singleton service."""
from aiohttp import ClientSession
from singleton_service import BaseService, guarded, requires

class GeoService(BaseService):
    @classmethod
    @guarded
    def city_by_coordinates(cls, lat: float, lon: float) -> str:
        return "London"

@requires(GeoService)
class WeatherService(BaseService):
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
        # the service was initialized correctly.
        return cls._session.get(f"{cls._base_url}/health").status == 200

    @classmethod
    @guarded # ← Ensure that this service and its dependencies are initialized
    def get_weather(cls, lat: float, lon: float) -> dict:
        # This is an example of the actual business logic of the service.
        city = GeoService.city_by_coordinates(lat, lon)
        return cls._session.get(f"{cls._base_url}/weather?q={city}").json()

if __name__ == "__main__":
    # When the line below is executed, the WeatherService singleton will
    # be initialized and then the weather will be fetched. Let's try London.
    print(WeatherService.get_weather(51.5074, -0.1278))

    # Now try New York.
    print(WeatherService.get_weather(40.7128, -74.0060))
```

Let's just go through initialization order for this example. When the call
to `WeatherService.get_weather(51.5074, -0.1278)` is made, the following
will happen:

1. The `@guarded` decorator on the `get_weather` method will ensure that
   the `WeatherService` singleton and its dependency, the `GeoService`,
   are initialized in the correct order: `GeoService` then `WeatherService`.
2. The `GeoService` singleton will be initialized first. It has no runtime
   initialization logic and no `ping`, so it is quickly marked as
   initialized.
3. The `WeatherService` singleton will now be initialized. The `initialize`
   method will be called and will be followed by the call to `ping` to
   make sure that we can actually fetch the weather data.
4. Both singletons are now marked as initialized and `BaseService` will
   remember that.
5. Now, finally, the `WeatherService.get_weather` method can be called.
   It uses the functionality provided by the `GeoService` singleton and
   fetches the weather data from the API.

When the second call to `WeatherService.get_weather(40.7128, -74.0060)` is
made, both singletons are already initialized, and the `@guarded` decorator
quickly determines that. So the second call directly proceeds to the
`WeatherService.get_weather` logic and returns the weather data for New
York.

### Example: Database Service

A singleton service for working with a database is a very common use case.
It nicely abstracts the connection and session handling logic.
It also provides a way to initialize and health check the service.
Many other services can depend on it. So let's start with it as a basis for
this example.

```python
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from singleton_service import BaseService, use, guarded
from sqlalchemy import create_engine, text
from sqlalchemy.engine.base import Engine
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
    AsyncSession,
    AsyncEngine,
)


# These should come from something like pydantic-settings or similar.
sync_dsn = "postgresql://user:password@localhost:5432/database"
async_dsn = "postgresql+asyncpg://user:password@localhost:5432/database"


class DatabaseService(BaseService):
    # At class definition time, none of these attributes are initialized.
    # They are simply declared along with their types.
    _async_engine: AsyncEngine = None
    _async_session_factory: async_sessionmaker = None
    _sync_engine: Engine = None

    @classmethod
    def initialize(cls) -> None:
        # The code below will be executed just once. Either when a call is
        # made to one of the @guarded methods in this class or when another
        # service that depends on the DatabaseService is being initialized.
        cls._async_engine = create_async_engine(async_dsn)
        cls._async_session_factory = async_sessionmaker(
            bind=cls._async_engine, expire_on_commit=False
        )
        cls._sync_engine = create_engine(sync_dsn)

    @classmethod
    def ping(cls) -> bool:
        # The logic below is called right after the initialize() to
        # make sure that the DatabaseService was initialized correctly.
        with cls._sync_engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            if result.fetchone() is None:
                print("Database ping failed")
                return False
        return True

    @classmethod
    @guarded
    def async_engine(cls) -> AsyncEngine:
        # This is a convenience method that returns the async engine. It is
        # decorated with @guarded. So, making a call to it will ensure that
        # the initialize() method was already called or force it to be called
        # before returning the engine.
        return cls._async_engine

    @classmethod
    @guarded
    def async_session_factory(cls) -> async_sessionmaker:
        # Same as above.
        return cls._async_session_factory

    @classmethod
    @guarded
    def sync_engine(cls) -> Engine:
        # Same as above.
        return cls._sync_engine

    @classmethod
    @asynccontextmanager
    @guarded
    async def session(cls) -> AsyncGenerator[AsyncSession, None]:
        # Similar to the above but we also decorate this method with
        # @asynccontextmanager to use it as a proper async context manager.
        async with cls._async_session_factory() as session:
            yield session
```

Here, we have added several convenience methods that are decorated with
`@guarded`. This decorator ensures that whenever any of them are
called, the `DatabaseService` is initialized first, if it wasn't already.

### Example: User Service

Now, let's define a User service that depends on the `DatabaseService`.
It's going to work with a simple ORM definition for a user.

```python
from singleton_service import BaseService, requires, guarded
from sqlmodel import (
    SQLModel,
    Field,
    select,
    func,
)

from .database import DatabaseService


class User(SQLModel, table=True):
    id: int = Field(..., primary_key=True)
    username: str = Field(...)
    full_name: str | None = Field(None)
    
    __tablename__ = "users"


@requires(DatabaseService)
class UsersService(BaseService):
    @classmethod
    def ping(cls) -> bool:
        # Check that the users table is present and has a correct schema.
        with DatabaseService.sync_engine().connect() as c:
            c.execute(select(User).limit(1))
        return True

    @classmethod
    @guarded
    async def get(cls, user_id: int) -> User | None:
        # This method is decorated with @guarded. So, it will ensure that
        # both the UsersService and the DatabaseService are initialized
        # in the correct order before it is called.
        async with DatabaseService.session() as s:
            query = select(User).where(User.id == user_id)
            result = await s.execute(query)
            return result.scalars().first()

    @classmethod
    @guarded
    async def save(cls, user: User) -> int:
        # Same as above.
        async with DatabaseService.session() as s:
            query = select(User).where(User.id == user.id)
            result = await s.execute(query)
            record = result.scalars().first()
            if record:
                # Update existing user
                record.username = user.username
                record.full_name = user.full_name
            else:
                # Create new user
                record = user
            s.add(record)
            await s.commit()
            return user.id
            
    @classmethod
    @guarded
    async def count(cls) -> int:
        # Same as above.
        async with DatabaseService.session() as s:
            query = select(func.count(User.id))
            result = await s.execute(query)
            return result.scalar_one()
```

Let's imagine that we want to call the `get` method of the `UsersService`
somewhere in our application to retrieve a user by their ID.

```python
from .users import UsersService

user = UsersService.get(1)
```

When we make a call to `UsersService.get(1)`, the `@guarded` decorator
ensures that the `UsersService` itself as well as all other services it
depends on are initialized in the correct order. It also runs a `ping`
health check for each service that was just initialized to make sure that
everything is working correctly.

The initialization and health check for each singleton service only happens
once. So, if we call `UsersService.get(1)` again, the method will return
the user immediately, assuming that the service was already initialized.

### Example: Background Worker

Imagine we have a background worker that can consume tasks from a queue and
execute them in the background. We will use the
[raquel](http://github.com/vduseev/raquel) library to implement the
worker itself.

```python
import asyncio
import socket
from typing import override

from raquel import AsyncRaquel, Job
from raquel.models.job import RawJob
from singleton_service import BaseRunnable, requires, guarded
from sqlmodel import select

from .database import DatabaseService
from .users import UsersService


async_dsn = "postgresql+asyncpg://user:password@localhost:5432/database"


@requires(DatabaseService, UsersService)
class BackgroundWorker(BaseRunnable):
    hostname: str = socket.gethostname()
    _rq: AsyncRaquel = AsyncRaquel(async_dsn)

    @classmethod
    def initialize(cls) -> None:
        # Subscribe the user count check method to the "check_user_count"
        # queue
        cls._rq.add_subscription(
            cls.check_user_count,
            queues="check_user_count",
            claim_as=cls.hostname,
        )

    @classmethod
    def ping(cls) -> bool:
        # Check that the jobs table is present and has the correct schema
        with DatabaseService.sync_engine().connect() as c:
            c.execute(select(RawJob).limit(1))
        return True

    @classmethod
    @guarded
    async def run_async(cls) -> None:
        # Runnable singletons can have a special run_async() or run_sync()
        # method that will be called when the service is run.
        # This is a good place to run the main loop of the service.
        #
        # In this specific example, the raquel library already implements
        # a while loop that will execute background jobs as they come. We
        # are simply calling it here.
        await cls._rq.run_subscriptions()

    @classmethod
    @guarded
    async def check_user_count(cls) -> None:
        user_count = await UsersService.count()
        if user_count > 1000:
            print("This project is too popular!")


if __name__ == "__main__":
    asyncio.run(BackgroundWorker.run_async())
```

When you run this `BackgroundWorker` singleton, it will first initialize
the `DatabaseService` and the `UsersService` services. Then it will
subscribe to the `check_user_count` queue and start consuming tasks from
it. It will also run a `ping` health check for each service to make sure
that everything is working correctly before executing any of the actual
business logic.
