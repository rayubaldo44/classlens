"""Bounded offloading for synchronous work used by async request handlers."""

from concurrent.futures import ThreadPoolExecutor
import asyncio
from threading import BoundedSemaphore, Event
from typing import Any, Callable, TypeVar

MAX_SYNC_WORKERS = 5
MAX_SYNC_JOBS = 10
_WORKERS = ThreadPoolExecutor(max_workers=MAX_SYNC_WORKERS, thread_name_prefix="classlens-worker")
_ADMISSION = BoundedSemaphore(MAX_SYNC_JOBS)
_Result = TypeVar("_Result")


class WorkCapacityError(RuntimeError):
    code = "work_capacity_exceeded"
    retryable = True

    def __init__(self) -> None:
        super().__init__("Processing capacity is full. Retry after the current requests finish.")


async def run_in_worker(function: Callable[..., _Result], *args: Any, **kwargs: Any) -> _Result:
    if not _ADMISSION.acquire(blocking=False):
        raise WorkCapacityError()
    cancelled = Event()

    def execute() -> _Result:
        if cancelled.is_set():
            raise asyncio.CancelledError
        return function(*args, **kwargs)

    try:
        future = _WORKERS.submit(execute)
    except BaseException:
        _ADMISSION.release()
        raise
    # Keep admission occupied until the worker consumes the queue item.
    future.add_done_callback(lambda _completed: _ADMISSION.release())
    wrapped = asyncio.wrap_future(future)
    try:
        return await asyncio.shield(wrapped)
    except asyncio.CancelledError:
        cancelled.set()
        wrapped.add_done_callback(lambda completed: completed.exception() if not completed.cancelled() else None)
        raise
