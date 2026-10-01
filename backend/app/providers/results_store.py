from threading import RLock
from typing import Protocol

from app.schemas.results import FollowUpComparisonRecord


class ResultsStore(Protocol):
    def save(self, record: FollowUpComparisonRecord) -> None: ...

    def get(self, comparison_id: str) -> FollowUpComparisonRecord | None: ...


class InMemoryResultsStore:
    """Process-local comparison store matching the current hackathon architecture."""

    def __init__(self) -> None:
        self._records: dict[str, FollowUpComparisonRecord] = {}
        self._lock = RLock()

    def save(self, record: FollowUpComparisonRecord) -> None:
        with self._lock:
            self._records[record.comparison_id] = record.model_copy(deep=True)

    def get(self, comparison_id: str) -> FollowUpComparisonRecord | None:
        with self._lock:
            record = self._records.get(comparison_id)
            return record.model_copy(deep=True) if record else None


_STORE = InMemoryResultsStore()


async def get_results_store() -> ResultsStore:
    from app.providers.postgres import get_postgres_results_store

    return get_postgres_results_store()
