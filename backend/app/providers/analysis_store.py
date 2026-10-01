from copy import deepcopy
from dataclasses import dataclass
from threading import RLock
from typing import Protocol

from app.schemas.analysis import AnalysisResponse
from app.services.assessment_intake import ParsedAssessment


@dataclass(frozen=True)
class AnalysisSnapshot:
    parsed: ParsedAssessment
    result: AnalysisResponse


class AnalysisStore(Protocol):
    def save(
        self,
        parsed: ParsedAssessment,
        result: AnalysisResponse,
        *,
        assessment_kind: str = "baseline",
        baseline_assessment_id: str | None = None,
    ) -> None: ...

    def get(self, analysis_id: str) -> AnalysisSnapshot | None: ...


class InMemoryAnalysisStore:
    """Process-local assessment snapshots used to link the hackathon demo flow."""

    def __init__(self) -> None:
        self._snapshots: dict[str, AnalysisSnapshot] = {}
        self._lock = RLock()

    def save(
        self,
        parsed: ParsedAssessment,
        result: AnalysisResponse,
        *,
        assessment_kind: str = "baseline",
        baseline_assessment_id: str | None = None,
    ) -> None:
        with self._lock:
            self._snapshots[result.analysis_id] = AnalysisSnapshot(
                parsed=deepcopy(parsed),
                result=result.model_copy(deep=True),
            )

    def get(self, analysis_id: str) -> AnalysisSnapshot | None:
        with self._lock:
            snapshot = self._snapshots.get(analysis_id)
            return deepcopy(snapshot) if snapshot else None


_STORE = InMemoryAnalysisStore()


async def get_analysis_store() -> AnalysisStore:
    from app.providers.postgres import get_postgres_analysis_store

    return get_postgres_analysis_store()
