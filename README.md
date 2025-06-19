# Singleton Service

A framework for building singleton services in Python.

## Usage

To define a singleton service, you need to inherit from `BaseService` and
implement the `initialize` and `ping` methods.

* `initialize` is synchronous only and is called once whenever the service
  needs to be initialized.
* `ping` is called once after initialization and is used to check if the
  service is correctly initialized. It can also be called afterwards as
  a health check.

```python
from singleton_service import BaseService

class DatabaseService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        pass

    @classmethod
    def ping(cls) -> bool:
        return True
```

### Example: Database Service

A singleton service for working with a database is a very common use case.
It nicely abstracts the connection and session handling logic.
It also provides a way to initialize and health check the service.
Many other services can depend on it. So let's start with it as a basis for
a full example.

```python
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from singleton_service import BaseService, use, guard
from sqlalchemy import create_engine, text
from sqlalchemy.engine.base import Engine
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
    AsyncSession,
    AsyncEngine,
)

sync_dsn = "postgresql://user:password@localhost:5432/database"
async_dsn = "postgresql+asyncpg://user:password@localhost:5432/database"


class DatabaseService(BaseService):
    _async_engine: AsyncEngine = None
    _async_session_factory: async_sessionmaker = None
    _sync_engine: Engine = None

    @classmethod
    def initialize(cls) -> None:
        cls._async_engine = create_async_engine(async_dsn)
        cls._async_session_factory = async_sessionmaker(
            bind=cls._async_engine, expire_on_commit=False
        )
        cls._sync_engine = create_engine(sync_dsn)

    @classmethod
    def ping(cls) -> bool:
        try:
            with cls._sync_engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                if result.fetchone() is None:
                    logfire.warning("Database ping failed")
                    return False
            return True
        except Exception as e:
            logfire.error(f"Failed to ping database: {e}")
            return False

    @classmethod
    @guard
    def async_engine(cls) -> AsyncEngine:
        return cls._async_engine

    @classmethod
    @guard
    def async_session_factory(cls) -> async_sessionmaker:
        return cls._async_session_factory

    @classmethod
    @guard
    def sync_engine(cls) -> Engine:
        return cls._sync_engine

    @classmethod
    @asynccontextmanager
    @guard
    async def session(cls) -> AsyncGenerator[AsyncSession, None]:
        async with cls._async_session_factory() as session:
            yield session
```

Here we have added several convenience methods that are decorated with
`@guard`. This decorator ensures that whenever any of these methods are
called, the service is initialized first, if it isn't already.

### Example: User Service

Now let's define a User service that depends on the database service. It's
going to work with an ORM definition of a user.

```python
from singleton_service import BaseService, use, guard
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


@use(DatabaseService)
class UsersService(BaseService):
    @classmethod
    def initialize(cls) -> None:
        # Users service has no real initialization logic. So we leave
        # it empty.
        pass

    @classmethod
    def ping(cls) -> bool:
        # Check that the users table is present and has the correct schema
        try:
            with DatabaseService.sync_engine().connect() as c:
                c.execute(select(User).limit(1))
        except Exception as e:
            print(f"Failed to ping {cls.__name__}: {e}")
            return False
        return True

    @classmethod
    @guard
    async def get(cls, user_id: int) -> User | None:
        async with DatabaseService.session() as s:
            query = select(User).where(User.id == user_id)
            result = await s.execute(query)
            return result.scalars().first()

    @classmethod
    @guard
    async def save(cls, user: User) -> int:
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
    @guard
    async def count(cls) -> int:
        async with DatabaseService.session() as s:
            query = select(func.count(User.id))
            result = await s.execute(query)
            return result.scalar_one()
```

Now, imagine that we want to call the `get` method of the `UsersService`
somewhere in our application to retrieve a user by their ID.

```python
from .users import UsersService

user = UsersService.get(1)
```

**This is the most amazing part!** When you call `UsersService.get(1)`,
the `@guard` decorator ensures that the `UsersService` itself as well as
all other services it uses are initialized in the correct order. It also
runs a `ping` method for each service that was just initialized to make
sure that everything is working correctly.

### Example: Runnable Service

Now, imagine we have a background worker that can consume tasks from a
queue and execute them in the background. We will use the
[raquel](http://github.com/vduseev/raquel) library to implement the
worker itself.

```python
import asyncio
import socket
from typing import override

from raquel import AsyncRaquel, Job
from raquel.models.job import RawJob
from singleton_service import BaseRunnable, use, guard
from sqlmodel import select

from .database import DatabaseService
from .users import UsersService


async_dsn = "postgresql+asyncpg://user:password@localhost:5432/database"


@use(DatabaseService, UsersService)
class WorkerRunnable(BaseRunnable):
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
        try:
            with DatabaseService.sync_engine().connect() as c:
                c.execute(select(RawJob).limit(1))
        except Exception as e:
            print(f"Failed to ping {cls.__name__}: {e}")
            return False
        return True

    @classmethod
    @guard
    async def run_async(cls) -> None:
        try:
            await cls._rq.run_subscriptions()
        finally:
            pass

    @classmethod
    @guard
    async def check_user_count(cls) -> None:
        user_count = await UsersService.count()
        if user_count > 1000:
            print("The project is too popular!")


if __name__ == "__main__":
    asyncio.run(WorkerRunnable.run_async())
```

When you run the worker, it will first initialize the `DatabaseService` and
the `UsersService` services. Then it will subscribe to the `check_user_count`
queue and start consuming tasks from it. It will also run a `ping` method
for each service to make sure that everything is working correctly.
