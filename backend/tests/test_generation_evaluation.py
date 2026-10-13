from conftest import run_test_async

from evaluation.generation_evaluation import _claim_review_complete, _close_service


def test_evaluator_closes_async_and_sync_google_clients() -> None:
    calls: list[str] = []

    class AsyncClient:
        async def aclose(self) -> None:
            calls.append("async")

    class Client:
        aio = AsyncClient()

        def close(self) -> None:
            calls.append("sync")

    service = type("Service", (), {"_client": Client()})()

    run_test_async(_close_service(service))

    assert calls == ["async", "sync"]


def test_claim_review_is_incomplete_when_no_case_generated() -> None:
    assert _claim_review_complete([], expected_count=2) is False
