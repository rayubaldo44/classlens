import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

import pytest

from conftest import run_test_async
from app.concurrency import run_in_worker
from app.providers.postgres import PostgresMaterialIndex
from app.services import group_reviews


async def wait_until_started(started, count):
    deadline = asyncio.get_running_loop().time() + 2
    while len(started) < count and asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(0.01)
    assert len(started) == count


def test_running_and_queued_work_has_a_ten_job_fail_fast_limit():
    async def check():
        release = threading.Event()
        started = []
        guard = threading.Lock()

        def hold(index):
            with guard:
                started.append(index)
            assert release.wait(3), "test worker was not released"
            return index

        tasks = [asyncio.create_task(run_in_worker(hold, index)) for index in range(10)]
        try:
            await wait_until_started(started, 5)
            with pytest.raises(RuntimeError, match="capacity"):
                await asyncio.wait_for(run_in_worker(lambda: "excess"), timeout=0.1)
        finally:
            release.set()
            await asyncio.gather(*tasks, return_exceptions=True)
        assert await run_in_worker(lambda: "recovered") == "recovered"

    run_test_async(check())


def test_cancelling_running_work_does_not_release_capacity_before_its_thread_finishes():
    async def check():
        release = threading.Event()
        started = []
        guard = threading.Lock()

        def hold(index):
            with guard:
                started.append(index)
            assert release.wait(3)

        tasks = [asyncio.create_task(run_in_worker(hold, index)) for index in range(10)]
        try:
            await wait_until_started(started, 5)
            tasks[0].cancel()
            await asyncio.gather(tasks[0], return_exceptions=True)
            with pytest.raises(RuntimeError, match="capacity"):
                await asyncio.wait_for(run_in_worker(lambda: "premature slot"), timeout=0.1)
        finally:
            release.set()
            await asyncio.gather(*tasks, return_exceptions=True)
        assert await run_in_worker(lambda: "recovered") == "recovered"

    run_test_async(check())


def test_cancelled_queue_item_holds_capacity_until_dequeued_without_executing():
    async def check():
        release = threading.Event()
        started = []

        def hold(index):
            started.append(index)
            assert release.wait(3)

        tasks = [asyncio.create_task(run_in_worker(hold, index)) for index in range(10)]
        try:
            await wait_until_started(started, 5)
            tasks[-1].cancel()
            await asyncio.gather(tasks[-1], return_exceptions=True)
            with pytest.raises(RuntimeError, match="capacity"):
                await asyncio.wait_for(run_in_worker(lambda: "excess"), timeout=0.1)
        finally:
            release.set()
            await asyncio.gather(*tasks, return_exceptions=True)
        assert await run_in_worker(lambda: "recovered") == "recovered"
        assert 9 not in started

    run_test_async(check())


def test_worker_exception_does_not_leak_admission_capacity():
    async def check():
        def fail():
            raise ValueError("controlled worker failure")

        for _ in range(15):
            with pytest.raises(ValueError, match="controlled"):
                await run_in_worker(fail)
        assert await run_in_worker(lambda: 42) == 42

    run_test_async(check())


def test_review_locks_are_removed_after_the_last_holder_and_waiter():
    before = len(group_reviews._analysis_locks)
    acquired = threading.Event()
    release = threading.Event()

    def first():
        with group_reviews.group_review_lock("test-lock-lifecycle-shared"):
            acquired.set()
            assert release.wait(2)

    def second():
        assert acquired.wait(2)
        with group_reviews.group_review_lock("test-lock-lifecycle-shared"):
            return "serialized"

    with ThreadPoolExecutor(max_workers=2) as executor:
        holder = executor.submit(first)
        waiter = executor.submit(second)
        try:
            assert acquired.wait(2)
            assert not waiter.done()
        finally:
            release.set()
        holder.result()
        assert waiter.result() == "serialized"
    for index in range(25):
        with group_reviews.group_review_lock(f"test-lock-lifecycle-{index}"):
            pass
    assert len(group_reviews._analysis_locks) == before


def test_review_lock_remains_reentrant_and_has_no_idle_entry():
    before = len(group_reviews._analysis_locks)
    with group_reviews.group_review_lock("nested-review"):
        with group_reviews.group_review_lock("nested-review"):
            assert len(group_reviews._analysis_locks) == before + 1
    assert len(group_reviews._analysis_locks) == before


def test_async_keyed_lock_cancelled_waiter_does_not_break_serialization_or_retain_keys():
    from app.locks import AsyncKeyedLocks

    registry = AsyncKeyedLocks()

    async def check():
        entered = asyncio.Event()
        release = asyncio.Event()

        async def holder():
            async with registry.hold("same-id"):
                entered.set()
                await release.wait()

        async def waiter():
            async with registry.hold("same-id"):
                return "serialized"

        first = asyncio.create_task(holder())
        await entered.wait()
        cancelled = asyncio.create_task(waiter())
        remaining = asyncio.create_task(waiter())
        await asyncio.sleep(0)
        cancelled.cancel()
        await asyncio.gather(cancelled, return_exceptions=True)
        assert len(registry) == 1
        assert not remaining.done()
        release.set()
        await first
        assert await remaining == "serialized"
        assert len(registry) == 0
        for index in range(25):
            async with registry.hold(str(index)):
                pass
        assert len(registry) == 0

    # An idle registry must retain neither keys nor event-loop-bound locks.
    for _ in range(3):
        run_test_async(check())


class MaterialMetadataDatabase:
    @contextmanager
    def connection(self):
        yield self

    def execute(self, query, parameters):
        material_id = parameters[0]
        if "from learning_materials" in query:
            row = (material_id, "Synthetic notes", "notes.txt", "synthetic_demo", "hash",
                   1, 900, 120, "test/embedding", 2)
            return type("Cursor", (), {"fetchone": lambda self: row})()
        rows = [(material_id + "-chunk", 0, "Exact synthetic source text.", 0, 28)]
        return type("Cursor", (), {"fetchall": lambda self: rows})()


def test_vector_cache_bounds_memory_and_keeps_recent_materials_without_losing_sources():
    index = PostgresMaterialIndex(MaterialMetadataDatabase())
    for number in range(16):
        index.set_embeddings(f"material-{number}", ((float(number), 1.0),))
    assert index.get("material-0").embeddings == ((0.0, 1.0),)
    index.set_embeddings("material-16", ((16.0, 1.0),))
    assert len(index._vectors) == 16
    evicted = index.get("material-1")
    assert evicted.embeddings == ()
    assert evicted.chunks[0].text == "Exact synthetic source text."
    assert index.get("material-0").embeddings == ((0.0, 1.0),)
    index.set_embeddings("material-1", ((1.0, 1.0),))
    assert index.get("material-1").embeddings == ((1.0, 1.0),)
    assert len(index._vectors) == 16
