import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
from types import SimpleNamespace

import asyncio
import httpx
from app.api.routes.analysis import get_embedding_service
from app.main import app
from app.concurrency import MAX_SYNC_WORKERS
from app.database import Database
from app.providers.embeddings import sentence_transformer
from app.providers.analysis_store import InMemoryAnalysisStore, get_analysis_store


def test_embedding_load_and_encode_are_serialized(monkeypatch) -> None:
    workers = 8
    start = threading.Barrier(workers)
    load_calls = 0
    active_encodes = 0
    maximum_active_encodes = 0
    loaded_model = None
    counter_lock = threading.Lock()

    class FakeModel:
        def encode(self, texts, **_kwargs):
            nonlocal active_encodes, maximum_active_encodes
            with counter_lock:
                active_encodes += 1
                maximum_active_encodes = max(maximum_active_encodes, active_encodes)
            time.sleep(0.01)
            with counter_lock:
                active_encodes -= 1
            return FakeVectors([[1.0, 0.0] for _ in texts])

    class FakeVectors(list):
        def tolist(self):
            return list(self)

    def load_model(_model_id: str, _revision: str):
        nonlocal load_calls, loaded_model
        if loaded_model is not None:
            return loaded_model
        with counter_lock:
            load_calls += 1
        time.sleep(0.05)
        loaded_model = FakeModel()
        return loaded_model

    monkeypatch.setattr(sentence_transformer, "_load_model", load_model)
    service = sentence_transformer.SentenceTransformerEmbeddingService("test/model")

    def embed():
        start.wait()
        return service.embed(["answer"])

    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(lambda _index: embed(), range(workers)))

    assert results == [[[1.0, 0.0]]] * workers
    assert load_calls == 1
    assert maximum_active_encodes == 1


def test_database_pool_is_created_once_under_concurrency(monkeypatch) -> None:
    workers = 8
    start = threading.Barrier(workers)
    constructor_calls = 0
    calls_lock = threading.Lock()

    class FakePool:
        def __init__(self, *_args, **_kwargs):
            nonlocal constructor_calls
            with calls_lock:
                constructor_calls += 1
            time.sleep(0.05)

    monkeypatch.setitem(sys.modules, "psycopg_pool", SimpleNamespace(ConnectionPool=FakePool))
    database = Database("postgresql://example.invalid/test")

    def get_pool():
        start.wait()
        return database._get_pool()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        pools = list(executor.map(lambda _index: get_pool(), range(workers)))

    assert constructor_calls == 1
    assert all(pool is pools[0] for pool in pools)


class BlockingEmbeddingService:
    model_id = "test/blocking-model"

    def __init__(self, *, fail: bool = False) -> None:
        self.started = threading.Event()
        self.release = threading.Event()
        self.fail = fail

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.started.set()
        if not self.release.wait(timeout=3):
            raise TimeoutError("test did not release fake embedding")
        if self.fail:
            raise RuntimeError("controlled embedding failure")
        return [[1.0, 0.0] for _ in texts]


def _override_analysis_dependencies(embedding_service: BlockingEmbeddingService) -> None:
    async def get_embedding():
        return embedding_service

    async def get_store():
        return InMemoryAnalysisStore()

    app.dependency_overrides[get_embedding_service] = get_embedding
    app.dependency_overrides[get_analysis_store] = get_store


async def _keep_test_loop_awake() -> None:
    while True:
        await asyncio.sleep(0.01)


def test_health_and_read_remain_responsive_during_analysis() -> None:
    async def run_requests() -> None:
        embeddings = BlockingEmbeddingService()
        _override_analysis_dependencies(embeddings)
        heartbeat = asyncio.create_task(_keep_test_loop_awake())
        try:
            async with app.router.lifespan_context(app):
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url="http://test"
                ) as analysis_client, httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url="http://test"
                ) as probe_client:
                    release_timer = threading.Timer(0.6, embeddings.release.set)
                    release_timer.start()
                    analysis = asyncio.create_task(
                        analysis_client.get("/api/v1/assessments/demo/photosynthesis/analysis")
                    )
                    deadline = asyncio.get_running_loop().time() + 2
                    while not embeddings.started.is_set() and asyncio.get_running_loop().time() < deadline:
                        await asyncio.sleep(0.01)
                    assert embeddings.started.is_set()
                    started = perf_counter()
                    health = await asyncio.wait_for(probe_client.get("/health"), timeout=0.3)
                    preview = await asyncio.wait_for(
                        probe_client.get("/api/v1/assessments/demo/photosynthesis/preview"), timeout=0.3
                    )
                    assert perf_counter() - started < 0.3
                    assert health.status_code == preview.status_code == 200
                    assert (await asyncio.wait_for(analysis, timeout=4)).status_code == 200
                    release_timer.cancel()
        finally:
            embeddings.release.set()
            heartbeat.cancel()
            await asyncio.gather(heartbeat, return_exceptions=True)
            app.dependency_overrides.clear()

    asyncio.run(run_requests())


def test_offloaded_analysis_error_keeps_error_envelope() -> None:
    async def run_request() -> httpx.Response:
        embeddings = BlockingEmbeddingService(fail=True)
        embeddings.release.set()
        _override_analysis_dependencies(embeddings)
        heartbeat = asyncio.create_task(_keep_test_loop_awake())
        try:
            async with app.router.lifespan_context(app):
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url="http://test"
                ) as client:
                    return await client.get("/api/v1/assessments/demo/photosynthesis/analysis")
        finally:
            heartbeat.cancel()
            await asyncio.gather(heartbeat, return_exceptions=True)
            app.dependency_overrides.clear()

    response = asyncio.run(run_request())
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "embedding_failed"


def test_worker_pool_caps_concurrent_sync_work_at_five() -> None:
    """Keep sync request work aligned with the five-connection database pool."""
    assert MAX_SYNC_WORKERS == 5
