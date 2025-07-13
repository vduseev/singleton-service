import logging
from collections import defaultdict

from ..provider import BaseProvider
from ..exceptions import (
    CircularDependency,
    InitializationOrderMismatch,
    SetupError,
    ProviderInitializationError,
)
from ._meta import _ProviderMeta


logger = logging.getLogger("singleton_provider")
__all__ = ["_initialize_provider_chain"]


def _raise_on_circular_dependencies(
    cls: type[BaseProvider],
    visited: set[type[BaseProvider]] | None = None,
    recursion_stack: set[type[BaseProvider]] | None = None,
) -> None:
    """Check for circular dependencies using depth-first search.
    
    This method performs cycle detection in the dependency graph using DFS.
    If a circular dependency is found, it raises an exception with details
    about the providers involved in the cycle.
    
    Args:
        visited: Set of providers already visited during traversal.
        recursion_stack: Current path in the DFS traversal.
        
    Raises:
        CircularDependencyError: If a circular dependency is detected.
        
    Note:
        This is an internal method used by the framework before initialization.
        The algorithm uses DFS with a recursion stack to detect back edges,
        which indicate cycles in the dependency graph.
    """
    if visited is None:
        visited = set()
    if recursion_stack is None:
        recursion_stack = set()

    if cls in recursion_stack:
        raise CircularDependency(
            name=cls.__name__,
            recursion_stack=[d.__name__ for d in recursion_stack],
        )

    if cls in visited:
        return

    visited.add(cls)
    recursion_stack.add(cls)

    for dep in cls.__provider_dependencies__:
        _raise_on_circular_dependencies(dep, visited, recursion_stack)

    recursion_stack.remove(cls)
            

def _get_all_dependencies(cls: type[BaseProvider]) -> set[type[BaseProvider]]:
    """Get all dependencies recursively for this provider.
    
    This internal method traverses the dependency graph to find all providers
    that this provider depends on, directly or indirectly.
    
    Returns:
        set[type[BaseProvider]]: All providers in the dependency tree.
        
    Note:
        This is an internal method used by the framework for dependency resolution.
        It performs a depth-first traversal of the dependency graph.
    """
    deps = set(cls.__provider_dependencies__)
    for dep in cls.__provider_dependencies__:
        deps.update(_get_all_dependencies(dep))
    return deps


def _get_initialization_order(cls: type[BaseProvider]) -> list[type[BaseProvider]]:
    """Determine the correct initialization order using topological sort.
    
    This method analyzes the dependency graph and returns providers in the order
    they should be initialized, ensuring that dependencies are always initialized
    before the providers that depend on them.
    
    Returns:
        list[type[BaseProvider]]: Providers ordered for safe initialization.
        
    Raises:
        InitializationOrderMismatchError: If the initialization order cannot be determined.
        
    Note:
        This is an internal method that implements Kahn's algorithm for topological sorting.
        The algorithm builds a dependency graph and processes nodes with no incoming edges,
        ensuring a valid initialization order.
    """
    # Build dependency graph
    graph = defaultdict(set)
    in_degree = defaultdict(int)

    # Add all dependencies to the graph
    all_deps = _get_all_dependencies(cls)
    all_deps.add(cls)

    for provider in all_deps:
        for dep in provider.__provider_dependencies__:
            graph[dep].add(provider)
            in_degree[provider] += 1

    # Topological sort
    result = []
    queue = [p for p in all_deps if in_degree[p] == 0]

    while queue:
        provider = queue.pop(0)
        result.append(provider)

        for dependent in graph[provider]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    if len(result) != len(all_deps):
        raise InitializationOrderMismatch(
            name=cls.__name__,
            order=[p.__name__ for p in result],
            dependencies=[p.__name__ for p in all_deps],
        )

    return result


def _initialize_provider_chain(
    cls: type[BaseProvider],
    requested_for: str,
) -> None:
    """Initialize the provider chain.
    
    This method is responsible for initializing the provider chain. It runs
    the one-time setup hook, checks for circular dependencies, and initializes
    the providers in the correct order.
    
    Args:
        cls: The provider class to initialize.
        requested_for: The reason for initializing the provider.
        
    Raises:
        CircularDependencyError: If a circular dependency is detected.
        InitializationOrderMismatchError: If the initialization order cannot be determined.
        SetupError: If the setup hook fails.
        ProviderInitializationError: If a provider fails to initialize.
    """

    # Run the one-time setup hook if it is defined. This is only done once
    # per runtime. It is designed to configure logging, disable warnings,
    # or monkey-patch things before the rest of the application starts.
    if (
        not _ProviderMeta.__provider_configured__
        and _ProviderMeta.__provider_setup__ is not None
    ):
        try:
            _ProviderMeta.__provider_setup__()
            _ProviderMeta.__provider_configured__ = True
            logger.info("Setup hook executed successfully.")
        except Exception as e:
            raise SetupError(e) from e

    logger.debug(
        f"About to initialize provider {cls.__name__} "
        f"because of: {requested_for}"
    )

    # Check for circular dependencies.
    _raise_on_circular_dependencies(cls)

    # Make sure all dependencies of this provider are initialized
    order = _get_initialization_order(cls)
    order_status = [
        f"{p.__name__}{' (initialized)' if p.__provider_initialized__ else ''}"
        for p in order
    ]
    logger.debug(
        f"Initialization order for provider {cls.__name__} is: "
        f"{', '.join(order_status)}"
    )
    for p in order:
        if not p.__provider_initialized__:
            try:
                logger.debug(f"Initializing provider {p.__name__}...")
                p.initialize()
                p.__provider_initialized__ = True
                logger.info(f"Provider {p.__name__} initialized successfully")
            except Exception as e:
                who = cls.__name__
                why = p.__name__
                cause = f" because of {why}" if who != why else ""
                raise ProviderInitializationError(
                    f"Failed to initialize provider {who}{cause}: {e}"
                ) from e
