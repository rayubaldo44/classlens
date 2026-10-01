import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from app.config import AnalysisSettings
from app.main import app
from app.providers.analysis_store import InMemoryAnalysisStore, get_analysis_store
from app.providers.embeddings import get_embedding_service
from app.providers.remediation_store import InMemoryRemediationStore, get_remediation_store
from app.providers.results_store import InMemoryResultsStore, get_results_store
from app.schemas.remediations import FollowUpQuestion, RemediationContent, RemediationRecord
from app.schemas.results import FollowUpComparisonLink
from app.services.assessment_intake import parse_assessment_csv_full
from app.services.misconception_analysis import AnalysisError, analyze_assessment
from app.services.results import ResultsError, create_follow_up_comparison, get_follow_up_comparison

HEADER = (
    "assessment_title,subject,grade_level,topic,student_id,question_id,question,answer,"
    "correct_answer,is_correct\n"
)
QUESTION = "Explain how plants make food during photosynthesis."
CORRECT = "Plants use light energy to convert carbon dioxide and water into glucose and oxygen."
DEMO_FOLLOW_UP = Path(__file__).resolve().parents[2] / "data" / "demo" / "photosynthesis_follow_up_responses.csv"


class KeywordEmbeddingService:
    model_id = "test/keyword-embedding"

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            lowered = text.lower()
            if "sun-food" in lowered:
                vectors.append([1.0, 0.0, 0.0])
            elif "soil-food" in lowered:
                vectors.append([0.0, 1.0, 0.0])
            else:
                vectors.append([0.0, 0.0, 1.0])
        return vectors


def row(student_id: str, answer: str, is_correct: bool, *, question: str = QUESTION) -> str:
    return (
        f'Assessment,Science,7,Photosynthesis,{student_id},Q1,{question},"{answer}",'
        f'"{CORRECT}",{str(is_correct).lower()}\n'
    )


def parsed(rows: Sequence[str], *, filename: str = "assessment.csv"):
    return parse_assessment_csv_full(
        (HEADER + "".join(rows)).encode(),
        filename=filename,
        data_label="teacher_upload",
    )


def analysis_settings() -> AnalysisSettings:
    return AnalysisSettings(
        embedding_model="test/keyword-embedding",
        similarity_threshold=0.8,
        min_group_size=3,
    )


def baseline_rows() -> list[str]:
    return [
        row("S1", "sun-food one", False),
        row("S2", "sun-food two", False),
        row("S3", "sun-food three", False),
        row("S4", "sun-food four", False),
        row("S5", "correct response", True),
        row("S6", "correct response", True),
    ]


def follow_up_rows() -> list[str]:
    return [
        row("S1", "correct response", True),
        row("S2", "sun-food still two", False),
        row("S3", "sun-food still three", False),
        row("S4", "carbon confusion", False),
        row("S5", "sun-food newly grouped", False),
    ]


def content() -> RemediationContent:
    return RemediationContent(
        misconception_summary="Sunlight is treated as food.",
        learning_objective="Distinguish light energy from glucose.",
        teacher_explanation="Light supplies energy used to make glucose.",
        corrected_concept="Plants make glucose from carbon dioxide and water.",
        activity="Sort energy, matter, and product cards.",
        analogy=None,
        follow_up_questions=[FollowUpQuestion(prompt="What does light provide?", expected_answer="Energy.")],
        source_references=["chunk_001"],
    )


def remediation(group_id: str, *, analysis_id: str = "analysis_test", status: str = "approved") -> RemediationRecord:
    now = datetime.now(UTC)
    draft = content()
    return RemediationRecord(
        remediation_id="rem_test",
        status=status,
        analysis_id=analysis_id,
        group_id=group_id,
        provider="fake",
        model="fake-model",
        prompt_version="grounded_remediation_v1",
        generated_content=draft.model_copy(deep=True),
        content=draft.model_copy(deep=True),
        sources=[],
        created_at=now,
        updated_at=now,
    )


def setup_context(*, remediation_status: str = "approved"):
    embedding = KeywordEmbeddingService()
    settings = analysis_settings()
    baseline = parsed(baseline_rows(), filename="baseline.csv")
    baseline_analysis = analyze_assessment(baseline, embedding, settings)
    group = baseline_analysis.groups[0]
    analysis_store = InMemoryAnalysisStore()
    analysis_store.save(baseline, baseline_analysis)
    remediation_store = InMemoryRemediationStore()
    remediation_store.save(remediation(group.group_id, analysis_id=baseline_analysis.analysis_id, status=remediation_status))
    results_store = InMemoryResultsStore()
    link = FollowUpComparisonLink(
        baseline_analysis_id=baseline_analysis.analysis_id,
        group_id=group.group_id,
        remediation_id="rem_test",
    )
    return embedding, settings, analysis_store, remediation_store, results_store, link


def test_comparison_calculates_prevalence_and_student_transitions_from_data() -> None:
    embedding, settings, analysis_store, remediation_store, results_store, link = setup_context()

    result = create_follow_up_comparison(
        link,
        parsed(follow_up_rows(), filename="follow-up.csv"),
        embedding_service=embedding,
        settings=settings,
        analysis_store=analysis_store,
        remediation_store=remediation_store,
        results_store=results_store,
    )

    assert result.status == "completed"
    assert result.metrics is not None
    assert result.metrics.before.affected_students == 4
    assert result.metrics.before.answered_students == 6
    assert result.metrics.before.misconception_prevalence_percent == 66.7
    assert result.metrics.after.affected_students == 3
    assert result.metrics.after.answered_students == 5
    assert result.metrics.after.misconception_prevalence_percent == 60.0
    assert result.metrics.percentage_point_reduction == 6.7
    assert result.metrics.missing_follow_up_students == 1
    assert result.metrics.transitions.model_dump() == {
        "baseline_affected_students": 4,
        "resolved_correct": 1,
        "changed_but_still_incorrect": 1,
        "still_struggling": 2,
        "missing_from_baseline_group": 0,
        "new_affected_students": 1,
    }
    assert result.trace is not None
    assert result.trace.remediation_status == "approved"
    assert results_store.get(result.comparison_id) is not None


def test_demo_follow_up_fixture_uses_existing_parser_and_expected_counts() -> None:
    fixture = parse_assessment_csv_full(
        DEMO_FOLLOW_UP.read_bytes(),
        filename=DEMO_FOLLOW_UP.name,
        data_label="synthetic_demo",
    )

    assert fixture.preview.summary.model_dump() == {
        "response_count": 44,
        "answered_count": 43,
        "blank_count": 1,
        "student_count": 44,
        "question_count": 1,
        "correct_count": 33,
        "incorrect_count": 10,
    }


def test_unapproved_intervention_blocks_comparison() -> None:
    embedding, settings, analysis_store, remediation_store, results_store, link = setup_context(
        remediation_status="generated"
    )

    with pytest.raises(ResultsError) as caught:
        create_follow_up_comparison(
            link,
            parsed(follow_up_rows()),
            embedding_service=embedding,
            settings=settings,
            analysis_store=analysis_store,
            remediation_store=remediation_store,
            results_store=results_store,
        )

    assert caught.value.code == "intervention_not_approved"


def test_missing_initial_analysis_is_actionable() -> None:
    embedding, settings, _analysis_store, remediation_store, results_store, link = setup_context()

    with pytest.raises(ResultsError) as caught:
        create_follow_up_comparison(
            link,
            parsed(follow_up_rows()),
            embedding_service=embedding,
            settings=settings,
            analysis_store=InMemoryAnalysisStore(),
            remediation_store=remediation_store,
            results_store=results_store,
        )

    assert caught.value.code == "initial_assessment_not_found"


def test_mismatched_follow_up_question_is_rejected() -> None:
    embedding, settings, analysis_store, remediation_store, results_store, link = setup_context()
    mismatched = [row("S1", "correct response", True, question="What enters a leaf?")]

    with pytest.raises(ResultsError) as caught:
        create_follow_up_comparison(
            link,
            parsed(mismatched),
            embedding_service=embedding,
            settings=settings,
            analysis_store=analysis_store,
            remediation_store=remediation_store,
            results_store=results_store,
        )

    assert caught.value.code == "follow_up_question_mismatch"


def test_unknown_follow_up_student_is_rejected() -> None:
    embedding, settings, analysis_store, remediation_store, results_store, link = setup_context()
    unknown = follow_up_rows() + [row("S99", "correct response", True)]

    with pytest.raises(ResultsError) as caught:
        create_follow_up_comparison(
            link,
            parsed(unknown),
            embedding_service=embedding,
            settings=settings,
            analysis_store=analysis_store,
            remediation_store=remediation_store,
            results_store=results_store,
        )

    assert caught.value.code == "follow_up_student_mismatch"
    assert caught.value.details == {"unknown_student_ids": ["S99"]}


def test_insufficient_reidentification_returns_no_fake_metrics() -> None:
    embedding, settings, analysis_store, remediation_store, results_store, link = setup_context()
    no_recurring_target = [
        row("S1", "correct response", True),
        row("S2", "correct response", True),
        row("S3", "correct response", True),
        row("S4", "carbon one", False),
        row("S5", "soil-food one", False),
        row("S6", "other error", False),
    ]

    result = create_follow_up_comparison(
        link,
        parsed(no_recurring_target),
        embedding_service=embedding,
        settings=settings,
        analysis_store=analysis_store,
        remediation_store=remediation_store,
        results_store=results_store,
    )

    assert result.status == "insufficient_data"
    assert result.metrics is None
    assert result.trace is not None
    assert result.trace.follow_up_group_id is None
    assert "No improvement percentage" in result.message


def test_follow_up_analysis_failure_propagates_without_saving_results() -> None:
    _embedding, settings, analysis_store, remediation_store, results_store, link = setup_context()

    class FailingEmbeddingService(KeywordEmbeddingService):
        def embed(self, texts: list[str]) -> list[list[float]]:
            raise RuntimeError("provider unavailable")

    with pytest.raises(AnalysisError) as caught:
        create_follow_up_comparison(
            link,
            parsed(follow_up_rows()),
            embedding_service=FailingEmbeddingService(),
            settings=settings,
            analysis_store=analysis_store,
            remediation_store=remediation_store,
            results_store=results_store,
        )

    assert caught.value.code == "embedding_failed"


def test_results_api_is_typed_reuses_csv_validation_and_supports_get() -> None:
    embedding, _settings, analysis_store, remediation_store, results_store, link = setup_context()

    async def override_embedding_service() -> KeywordEmbeddingService:
        return embedding

    async def override_analysis_store() -> InMemoryAnalysisStore:
        return analysis_store

    async def override_remediation_store() -> InMemoryRemediationStore:
        return remediation_store

    async def override_results_store() -> InMemoryResultsStore:
        return results_store

    app.dependency_overrides[get_embedding_service] = override_embedding_service
    app.dependency_overrides[get_analysis_store] = override_analysis_store
    app.dependency_overrides[get_remediation_store] = override_remediation_store
    app.dependency_overrides[get_results_store] = override_results_store

    async def send() -> tuple[httpx.Response, httpx.Response, httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/api/v1/results",
                data=link.model_dump(),
                files={"file": ("follow-up.csv", (HEADER + "".join(follow_up_rows())).encode(), "text/csv")},
            )
            comparison_id = created.json()["comparison_id"]
            fetched = await client.get(f"/api/v1/results/{comparison_id}")
            invalid = await client.post(
                "/api/v1/results",
                data=link.model_dump(),
                files={"file": ("follow-up.csv", b"student_id,answer\nS1,answer\n", "text/csv")},
            )
            return created, fetched, invalid

    try:
        created, fetched, invalid = asyncio.run(send())
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 200
    assert created.json()["status"] == "completed"
    assert fetched.status_code == 200
    assert fetched.json() == created.json()
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "csv_missing_columns"


def test_missing_comparison_returns_typed_404() -> None:
    with pytest.raises(ResultsError) as caught:
        get_follow_up_comparison("comparison_missing", results_store=InMemoryResultsStore())

    assert caught.value.code == "results_not_found"
