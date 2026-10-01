import asyncio
from collections.abc import Sequence

import httpx
import pytest

from app.api.routes.analysis import get_embedding_service
from app.config import AnalysisSettings
from app.main import app
from app.providers.analysis_store import InMemoryAnalysisStore, get_analysis_store
from app.services.assessment_intake import parse_assessment_csv_full
from app.services.misconception_analysis import AnalysisError, analyze_assessment

HEADER = (
    "assessment_title,subject,grade_level,topic,student_id,question_id,question,answer,"
    "correct_answer,is_correct\n"
)


class FakeEmbeddingService:
    model_id = "test/semantic-fixture"

    def __init__(self, vectors: Sequence[Sequence[float]]) -> None:
        self.vectors = [list(vector) for vector in vectors]
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return self.vectors


def csv_row(student: str, question_id: str, question: str, answer: str) -> str:
    return (
        f'Demo,Science,7,Photosynthesis,{student},{question_id},{question},"{answer}",'
        "Reference answer,false\n"
    )


def parsed_assessment(rows: list[str]):
    return parse_assessment_csv_full(
        (HEADER + "".join(rows)).encode(),
        filename="responses.csv",
        data_label="teacher_upload",
    )


def settings(minimum_support: int = 3) -> AnalysisSettings:
    return AnalysisSettings(
        embedding_model="test/semantic-fixture",
        similarity_threshold=0.8,
        min_group_size=minimum_support,
    )


def test_groups_similar_answers_per_question_and_preserves_evidence() -> None:
    rows = [
        csv_row("S1", "Q1", "How do plants make food?", "Plants eat sunlight."),
        csv_row("S2", "Q1", "How do plants make food?", "Sunlight is plant food."),
        csv_row("S3", "Q1", "How do plants make food?", "Plants consume rays to grow."),
        csv_row("S4", "Q1", "How do plants make food?", "Food comes from soil."),
        csv_row("S5", "Q2", "What enters a leaf?", "Plants eat sunlight."),
        csv_row("S6", "Q2", "What enters a leaf?", "Sunlight is plant food."),
    ]
    vectors = [
        [1.0, 0.0],
        [0.99, 0.1],
        [0.98, -0.1],
        [0.0, 1.0],
        [1.0, 0.0],
        [0.99, 0.1],
    ]

    result = analyze_assessment(parsed_assessment(rows), FakeEmbeddingService(vectors), settings())

    assert result.status == "completed"
    assert result.summary.group_count == 1
    assert result.summary.grouped_response_count == 3
    assert result.summary.outlier_count == 3
    group = result.groups[0]
    assert group.question_id == "Q1"
    assert group.member_student_ids == ["S1", "S2", "S3"]
    assert {item.answer for item in group.representative_responses}.issubset(
        {"Plants eat sunlight.", "Sunlight is plant food.", "Plants consume rays to grow."}
    )
    assert group.provisional_label == "Potential misconception pattern 1"
    assert group.interpretation_status == "not_requested"


def test_insufficient_evidence_returns_empty_without_embedding() -> None:
    rows = [
        csv_row("S1", "Q1", "Question", "First answer"),
        csv_row("S2", "Q1", "Question", "Second answer"),
    ]
    embeddings = FakeEmbeddingService([])

    result = analyze_assessment(parsed_assessment(rows), embeddings, settings())

    assert result.status == "insufficient_data"
    assert result.groups == []
    assert result.summary.group_count == 0
    assert embeddings.calls == []


def test_unrelated_vectors_are_not_forced_into_a_group() -> None:
    rows = [csv_row(f"S{i}", "Q1", "Question", f"Answer {i}") for i in range(1, 4)]
    embeddings = FakeEmbeddingService([[1, 0, 0], [0, 1, 0], [0, 0, 1]])

    result = analyze_assessment(parsed_assessment(rows), embeddings, settings())

    assert result.status == "insufficient_data"
    assert result.groups == []
    assert result.summary.outlier_count == 3


def test_invalid_embedding_response_fails_safely() -> None:
    rows = [csv_row(f"S{i}", "Q1", "Question", f"Answer {i}") for i in range(1, 4)]

    with pytest.raises(AnalysisError) as caught:
        analyze_assessment(parsed_assessment(rows), FakeEmbeddingService([[1, 0]]), settings())

    assert caught.value.code == "embedding_invalid_response"
    assert caught.value.retryable is True


def test_embedding_provider_failure_is_sanitized() -> None:
    rows = [csv_row(f"S{i}", "Q1", "Question", f"Answer {i}") for i in range(1, 4)]

    class FailingEmbeddingService(FakeEmbeddingService):
        def embed(self, texts: list[str]) -> list[list[float]]:
            raise RuntimeError("sensitive provider detail")

    with pytest.raises(AnalysisError) as caught:
        analyze_assessment(parsed_assessment(rows), FailingEmbeddingService([]), settings())

    assert caught.value.code == "embedding_failed"
    assert caught.value.message == "Response embeddings could not be generated."
    assert "sensitive provider detail" not in caught.value.message


def test_analysis_api_returns_typed_result_with_dependency_override() -> None:
    rows = [csv_row(f"S{i}", "Q1", "Question", f"Similar answer {i}") for i in range(1, 4)]
    fake = FakeEmbeddingService([[1, 0], [0.99, 0.02], [0.98, -0.02]])
    store = InMemoryAnalysisStore()
    async def override_embedding_service() -> FakeEmbeddingService:
        return fake

    async def override_analysis_store() -> InMemoryAnalysisStore:
        return store

    app.dependency_overrides[get_embedding_service] = override_embedding_service
    app.dependency_overrides[get_analysis_store] = override_analysis_store

    async def send() -> tuple[httpx.Response, httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/api/v1/assessments/analyze",
                files={"file": ("responses.csv", (HEADER + "".join(rows)).encode(), "text/csv")},
            )
            fetched = await client.get(f"/api/v1/assessments/analyses/{created.json()['analysis_id']}")
            return created, fetched

    try:
        response, fetched = asyncio.run(send())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["embedding"]["model_id"] == "test/semantic-fixture"
    assert body["groups"][0]["support_count"] == 3
    assert fetched.status_code == 200
    assert fetched.json() == body


def test_analysis_api_rejects_malformed_assessment_before_embedding() -> None:
    fake = FakeEmbeddingService([])

    async def override_embedding_service() -> FakeEmbeddingService:
        return fake

    app.dependency_overrides[get_embedding_service] = override_embedding_service

    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/api/v1/assessments/analyze",
                files={"file": ("responses.csv", b"student_id,answer\nS1,Answer\n", "text/csv")},
            )

    try:
        response = asyncio.run(send())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "csv_missing_columns"
    assert fake.calls == []
