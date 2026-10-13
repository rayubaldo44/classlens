import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

_Result = TypeVar("_Result")


async def _heartbeat() -> None:
    while True:
        await asyncio.sleep(0.01)


def run_test_async(awaitable: Coroutine[Any, Any, _Result]) -> _Result:
    """Run async tests while periodically waking asyncio for executor callbacks."""
    async def run() -> _Result:
        heartbeat = asyncio.create_task(_heartbeat())
        try:
            return await awaitable
        finally:
            heartbeat.cancel()
            await asyncio.gather(heartbeat, return_exceptions=True)

    return asyncio.run(run())
