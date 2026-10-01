from threading import RLock
from typing import Protocol

from app.schemas.remediations import RemediationRecord


class RemediationStore(Protocol):
    def save(self, record: RemediationRecord) -> None: ...

    def get(self, remediation_id: str) -> RemediationRecord | None: ...


class InMemoryRemediationStore:
    """Process-local demo store. Records are copied to prevent accidental mutation."""

    def __init__(self) -> None:
        self._records: dict[str, RemediationRecord] = {}
        self._lock = RLock()

    def save(self, record: RemediationRecord) -> None:
        with self._lock:
            self._records[record.remediation_id] = record.model_copy(deep=True)

    def get(self, remediation_id: str) -> RemediationRecord | None:
        with self._lock:
            record = self._records.get(remediation_id)
            return record.model_copy(deep=True) if record else None


_STORE = InMemoryRemediationStore()


async def get_remediation_store() -> RemediationStore:
    from app.providers.postgres import get_postgres_remediation_store

    return get_postgres_remediation_store()
