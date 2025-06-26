from abc import ABC
from collections import defaultdict
from typing import (
    Set,
    Type,
    List,
    Optional,
)

from .exceptions import (
    CircularDependencyError,
    ServiceInitializationError,
)


class BaseService(ABC):
    _initialized: bool = False
    _dependencies: Set[Type["BaseService"]] = set()

    def __new__(cls, *args, **kwargs) -> "BaseService":
        # Prevent BaseService or anyone who inherits from it from being
        # instantiated.
        raise RuntimeError("BaseService is not instantiable")

    @classmethod
    def initialize(cls) -> None:
        """Initialization logic for this service.

        If you can't initialize the service, raise an exception.
        """

    @classmethod
    def ping(cls) -> bool:
        """Check if the service is correctly initialized.

        Implement this so that the framework can check whether the service
        was correctly initialized.
        """
        return True

    @classmethod
    def _get_all_dependencies(cls) -> Set[Type["BaseService"]]:
        """Get all dependencies recursively."""
        deps = set(cls._dependencies)
        for dep in cls._dependencies:
            deps.update(dep._get_all_dependencies())
        return deps

    @classmethod
    def _raise_on_circular_dependencies(
        cls,
        visited: Optional[Set[Type["BaseService"]]] = None,
        recursion_stack: Optional[Set[Type["BaseService"]]] = None,
    ) -> None:
        """Check for circular dependencies using DFS.

        Raise CircularDependencyError if circular dependency is detected.
        """
        if visited is None:
            visited = set()
        if recursion_stack is None:
            recursion_stack = set()

        if cls in recursion_stack:
            raise CircularDependencyError(
                f"Circular dependency in {cls.__name__}: "
                f"{', '.join([d.__name__ for d in recursion_stack])}"
            )

        if cls in visited:
            return

        visited.add(cls)
        recursion_stack.add(cls)

        for dep in cls._dependencies:
            dep._raise_on_circular_dependencies(visited, recursion_stack)

        recursion_stack.remove(cls)

    @classmethod
    def _get_initialization_order(cls) -> List[Type["BaseService"]]:
        """Get the correct initialization order using topological sort."""
        # Build dependency graph
        graph = defaultdict(set)
        in_degree = defaultdict(int)

        # Add all dependencies to the graph
        all_deps = cls._get_all_dependencies()
        all_deps.add(cls)

        for service in all_deps:
            for dep in service._dependencies:
                graph[dep].add(service)
                in_degree[service] += 1

        # Topological sort
        result = []
        queue = [s for s in all_deps if in_degree[s] == 0]

        while queue:
            service = queue.pop(0)
            result.append(service)

            for dependent in graph[service]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(result) != len(all_deps):
            raise CircularDependencyError(
                "Circular dependency detected in the dependency graph"
            )

        return result

    @classmethod
    def _initialize_impl(cls) -> None:
        """Internal implementation of the initialization logic.

        This method is called by the framework automatically and uses the
        `initialize()` and `ping()` methods defined by the developer.
        """
        cls.initialize()

        # Verify that the service is correctly initialized
        try:
            ping_result = cls.ping()
        except Exception as e:
            raise ServiceInitializationError(
                f"Service {cls.__name__} failed to initialize "
                f"because its ping method raised an exception: {e}"
            )

        if not ping_result:
            raise ServiceInitializationError(
                f"Service {cls.__name__} failed to initialize "
                "because its ping method returned False"
            )

        # Mark the service as initialized
        cls._initialized = True
