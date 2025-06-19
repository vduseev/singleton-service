class ServiceError(Exception):
    pass


class CircularDependencyError(ServiceError):
    pass


class DependencyNotInitializedError(ServiceError):
    pass


class ServiceNotInitializedError(ServiceError):
    pass


class ServiceInitializationError(ServiceError):
    pass


class SelfDependencyError(ServiceError):
    pass
