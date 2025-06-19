from .base_service import BaseService

class BaseRunnable(BaseService):
    @classmethod
    def run_sync(cls) -> None:
        """Run the service synchronously."""
        raise NotImplementedError("run_sync must be implemented to call it")

    @classmethod
    async def run_async(cls) -> None:
        """Run the service asynchronously."""
        raise NotImplementedError("run_async must be implemented to call it")
