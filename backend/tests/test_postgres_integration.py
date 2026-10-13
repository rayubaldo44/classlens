import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.config import AnalysisSettings, MaterialSettings
from app.database import Database
from app.providers.postgres import PostgresAnalysisStore, PostgresMaterialIndex, PostgresRemediationStore, PostgresResultsStore
from app.schemas.materials import MisconceptionRetrievalContext
from app.schemas.remediations import FollowUpQuestion, RemediationContent, RemediationRecord, RemediationSource
from app.schemas.results import FollowUpComparisonLink
from app.services.assessment_intake import parse_assessment_csv_full
from app.services.misconception_analysis import analyze_assessment
from app.services.material_ingestion import ingest_learning_material
from app.services.material_retrieval import retrieve_for_misconception
from app.services.results import create_follow_up_comparison


DATABASE_URL = os.getenv("CLASSLENS_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="CLASSLENS_TEST_DATABASE_URL is not configured")

HEADER = (
    "assessment_title,subject,grade_level,topic,student_id,question_id,question,answer,"
    "correct_answer,is_correct\n"
)
QUESTION = "Explain how plants make food during photosynthesis."
CORRECT = "Plants use light energy to make glucose."


class Embeddings:
    model_id = "test/postgres-embedding"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] if "sun-food" in text else [0.0, 1.0] for text in texts]


class MaterialEmbeddings:
    model_id = "test/material-persistence"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


def _row(student: str, answer: str, correct: bool) -> str:
    return f'Persistence,Science,7,Photosynthesis,{student},Q1,"{QUESTION}","{answer}","{CORRECT}",{str(correct).lower()}\n'


def _parsed(rows: list[str], filename: str):
    return parse_assessment_csv_full((HEADER + "".join(rows)).encode(), filename=filename, data_label="teacher_upload")


def test_postgres_workflow_survives_new_repository_instances() -> None:
    assert DATABASE_URL is not None
    database = Database(DATABASE_URL)
    analysis_store = PostgresAnalysisStore(database)
    remediation_store = PostgresRemediationStore(database)
    results_store = PostgresResultsStore(database)
    settings = AnalysisSettings(embedding_model=Embeddings.model_id, similarity_threshold=0.8, min_group_size=3)
    suffix = uuid4().hex[:8]
    students = [f"DB1-{suffix}", f"DB2-{suffix}", f"DB3-{suffix}", f"DB4-{suffix}"]

    baseline = _parsed([
        _row(students[0], "sun-food one", False), _row(students[1], "sun-food two", False),
        _row(students[2], "sun-food three", False), _row(students[3], "correct", True),
    ], "persistence-baseline.csv")
    baseline_result = analyze_assessment(baseline, Embeddings(), settings)
    analysis_store.save(baseline, baseline_result)
    analysis_store.save(baseline, baseline_result)  # A retry must not duplicate response or group evidence.
    group = baseline_result.groups[0]

    material_settings = MaterialSettings(
        chunk_size_chars=900, chunk_overlap_chars=120, retrieval_top_k=3, minimum_relevance_score=0.42
    )
    material_index = PostgresMaterialIndex(database)
    material = ingest_learning_material(
        b"Sunlight supplies energy that plants use to make glucose.",
        filename="persistence-lesson.txt", title="Persistence lesson", source_kind="teacher_upload",
        embedding_service=MaterialEmbeddings(), material_index=material_index, settings=material_settings,
    ).material
    reloaded_index = PostgresMaterialIndex(Database(DATABASE_URL))
    retrieval = retrieve_for_misconception(
        material.material_id,
        MisconceptionRetrievalContext(
            group_id=group.group_id, question_id=group.question_id, question=group.question,
            correct_answer=group.correct_answer,
            representative_answers=[item.answer for item in group.representative_responses],
        ),
        embedding_service=MaterialEmbeddings(), material_index=reloaded_index, settings=material_settings,
    )
    assert retrieval.status == "retrieved"

    content = RemediationContent(
        misconception_summary="Sunlight is treated as food.", learning_objective="Separate energy and matter.",
        teacher_explanation="Light supplies energy.", corrected_concept="Plants make glucose.",
        activity="Sort energy and matter cards.", analogy=None,
        follow_up_questions=[FollowUpQuestion(prompt="What does light provide?", expected_answer="Energy")],
        source_references=["chunk_001"],
    )
    now = datetime.now(UTC)
    remediation = RemediationRecord(
        remediation_id=f"rem_{baseline_result.analysis_id}", status="generated",
        analysis_id=baseline_result.analysis_id, group_id=group.group_id,
        provider="test", model="test", prompt_version="grounded_remediation_v1",
        generated_content=content, content=content.model_copy(deep=True),
        sources=[RemediationSource(
            material_id=material.material_id, material_title=material.title, filename=material.filename,
            chunk_id=item.chunk_id, chunk_index=item.chunk_index, text=item.text,
            similarity=item.similarity, start_char=item.start_char, end_char=item.end_char,
        ) for item in retrieval.results],
        created_at=now, updated_at=now,
    )
    remediation_store.save(remediation)
    remediation.status = "approved"
    remediation.updated_at = datetime.now(UTC)
    remediation_store.save(remediation)

    follow_up = _parsed([
        _row(students[0], "sun-food one later", False), _row(students[1], "sun-food two later", False),
        _row(students[2], "sun-food three later", False), _row(students[3], "correct later", True),
    ], "persistence-follow-up.csv")
    comparison = create_follow_up_comparison(
        FollowUpComparisonLink(
            baseline_analysis_id=baseline_result.analysis_id,
            group_id=group.group_id,
            remediation_id=remediation.remediation_id,
        ),
        follow_up,
        embedding_service=Embeddings(), settings=settings,
        analysis_store=analysis_store, remediation_store=remediation_store, results_store=results_store,
    )

    reloaded_analysis = PostgresAnalysisStore(Database(DATABASE_URL)).get(baseline_result.analysis_id)
    reloaded_remediation = PostgresRemediationStore(Database(DATABASE_URL)).get(remediation.remediation_id)
    reloaded_comparison = PostgresResultsStore(Database(DATABASE_URL)).get(comparison.comparison_id)
    assert reloaded_analysis is not None
    assert reloaded_analysis.parsed.responses[0].answer == "sun-food one"
    assert reloaded_remediation is not None and reloaded_remediation.status == "approved"
    assert reloaded_comparison is not None and reloaded_comparison.trace is not None
    assert reloaded_comparison.trace.baseline_assessment_id == baseline_result.assessment_id
