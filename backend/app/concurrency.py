"""Bounded offloading for synchronous work used by async request handlers."""

from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any, Callable, TypeVar

MAX_SYNC_WORKERS = 5
_WORKERS = ThreadPoolExecutor(max_workers=MAX_SYNC_WORKERS, thread_name_prefix="classlens-worker")
_Result = TypeVar("_Result")


async def run_in_worker(function: Callable[..., _Result], *args: Any, **kwargs: Any) -> _Result:
    import asyncio

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_WORKERS, partial(function, *args, **kwargs))
