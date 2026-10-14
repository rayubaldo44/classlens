from copy import deepcopy
from threading import RLock
from typing import Protocol

from app.schemas.group_reviews import GroupReviewEvent, GroupReviewState, StoredGroupReviews


class GroupReviewStore(Protocol):
    def get(self, analysis_id: str) -> StoredGroupReviews | None: ...

    def save(
        self,
        analysis_id: str,
        previous_state: GroupReviewState | None,
        next_state: GroupReviewState,
        event: GroupReviewEvent,
    ) -> None: ...


class InMemoryGroupReviewStore:
    def __init__(self) -> None:
        self._records: dict[str, StoredGroupReviews] = {}
        self._lock = RLock()

    def get(self, analysis_id: str) -> StoredGroupReviews | None:
        with self._lock:
            record = self._records.get(analysis_id)
            return deepcopy(record) if record else None

    def save(
        self,
        analysis_id: str,
        previous_state: GroupReviewState | None,
        next_state: GroupReviewState,
        event: GroupReviewEvent,
    ) -> None:
        with self._lock:
            current = self._records.get(analysis_id)
            current_state = current.state if current else None
            if current_state != previous_state:
                raise ValueError("The group review state is stale.")
            events = [*current.events, event] if current else [event]
            self._records[analysis_id] = StoredGroupReviews(
                state=next_state.model_copy(deep=True),
                events=[item.model_copy(deep=True) for item in sorted(events, key=lambda item: item.sequence)],
            )


_STORE = InMemoryGroupReviewStore()


async def get_group_review_store() -> GroupReviewStore:
    from app.providers.postgres import get_postgres_group_review_store

    return get_postgres_group_review_store()
