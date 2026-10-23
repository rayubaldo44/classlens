from pathlib import Path

import pytest

from app.database import Database, DatabaseError
from app.providers.postgres import PostgresAnalysisStore
from app.services.misconception_analysis import analyze_assessment
from app.providers.material_index.protocol import MaterialRecord
from app.providers.material_index.memory import InMemoryMaterialIndex
from app.schemas.materials import LearningMaterial, MaterialChunk
from app.services.material_retrieval import retrieve_for_misconception
from test_material_retrieval import FakeEmbeddingService, context, review_stores, settings
from test_misconception_analysis import (
    FakeEmbeddingService as AnalysisEmbeddings,
    csv_row,
    parsed_assessment,
    settings as analysis_settings,
)


MIGRATION = Path(__file__).resolve().parents[2] / "database" / "migrations" / "001_golden_path_persistence.sql"


def test_migration_contains_only_implemented_golden_path_tables() -> None:
    sql = MIGRATION.read_text()
    expected = {
        "assessments", "questions", "student_responses", "analysis_runs",
        "misconception_groups", "misconception_members", "learning_materials",
        "document_chunks", "interventions", "intervention_sources",
        "assessment_comparisons",
    }
    for table in expected:
        assert f"create table if not exists {table}" in sql
        assert f"alter table {table} enable row level security" in sql
    assert "create table if not exists classes" not in sql
    assert "create table if not exists follow_up_results" not in sql
    assert " vector(" not in sql.lower()


def test_missing_database_configuration_is_actionable() -> None:
    database = Database("")
    with pytest.raises(DatabaseError) as caught:
        with database.connection():
            pass
    assert caught.value.code == "database_not_configured"
    assert caught.value.retryable is False
    assert "SUPABASE_DB_URL" in caught.value.message


def test_database_pool_disables_session_prepared_statements(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakePool:
        def __init__(self, database_url: str, **kwargs: object) -> None:
            captured["database_url"] = database_url
            captured.update(kwargs)

    monkeypatch.setattr("psycopg_pool.ConnectionPool", FakePool)

    pool = Database("postgresql://example.invalid/classlens")._get_pool()

    assert isinstance(pool, FakePool)
    assert captured["kwargs"] == {"prepare_threshold": None}


def test_analysis_store_batches_response_and_member_inserts() -> None:
    parsed = parsed_assessment([
        csv_row(f"S{i}", "Q1", "How do plants make food?", f"Similar answer {i}")
        for i in range(1, 4)
    ])
    result = analyze_assessment(
        parsed,
        AnalysisEmbeddings([[1, 0], [0.99, 0.02], [0.98, -0.02]]),
        analysis_settings(),
    )

    class Cursor:
        def __init__(self, rows=()):
            self.rows = list(rows)

        def fetchall(self):
            return self.rows

        def fetchone(self):
            return self.rows[0] if self.rows else None

    class Connection:
        def __init__(self):
            self.batches = []
            self.group_id = 100

        def execute(self, query, params=()):
            if "select id, external_key from questions" in query:
                return Cursor([(10, "Q1")])
            if "insert into analysis_runs" in query:
                return Cursor([(20,)])
            if "select r.id, q.external_key, r.student_key" in query:
                return Cursor([(index, "Q1", f"S{index}") for index in range(1, 4)])
            if "insert into misconception_groups" in query:
                self.group_id += 1
                return Cursor([(self.group_id,)])
            return Cursor()

        def cursor(self):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def executemany(self, query, params_seq):
            self.batches.append((query, list(params_seq)))

    connection = Connection()
    store = PostgresAnalysisStore(Database("postgresql://example.invalid/test"))
    store.save_in_connection(
        connection, parsed, result, assessment_kind="baseline", baseline_assessment_id=None
    )

    assert len(connection.batches) == 2
    response_batch, member_batch = connection.batches
    assert "insert into student_responses" in response_batch[0]
    assert "on conflict (question_id, student_key) do nothing" in response_batch[0].lower()
    assert len(response_batch[1]) == len(parsed.responses) == 3
    assert "insert into misconception_members" in member_batch[0]
    assert len(member_batch[1]) == sum(len(group.member_student_ids) for group in result.groups) == 3


def test_persisted_chunks_are_reembedded_when_vector_cache_is_empty() -> None:
    class CacheableIndex(InMemoryMaterialIndex):
        def set_embeddings(self, material_id, embeddings):
            record = self.get(material_id)
            assert record is not None
            self.upsert(MaterialRecord(material=record.material, chunks=record.chunks, embeddings=embeddings))

    material = LearningMaterial(
        material_id="mat_persisted", title="Lesson", filename="lesson.txt",
        source_kind="teacher_upload", content_hash="hash", chunk_count=1,
        chunk_size_chars=900, chunk_overlap_chars=120,
        embedding_model="test/material-embeddings", embedding_dimension=2,
    )
    index = CacheableIndex()
    index.upsert(MaterialRecord(
        material=material,
        chunks=(MaterialChunk(chunk_id="chunk_001", chunk_index=0, text="Plants use light energy.", start_char=0, end_char=24),),
        embeddings=(),
    ))
    embedding = FakeEmbeddingService()

    result = retrieve_for_misconception(
        material.material_id,
        context(),
        embedding_service=embedding,
        material_index=index,
        settings=settings(threshold=0.8),
        **review_stores(),
    )

    assert result.status == "retrieved"
    assert result.results[0].chunk_id == "chunk_001"
    assert embedding.calls[0] == ["Plants use light energy."]
