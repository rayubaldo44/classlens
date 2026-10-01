from pathlib import Path

import pytest

from app.database import Database, DatabaseError
from app.providers.material_index.protocol import MaterialRecord
from app.providers.material_index.memory import InMemoryMaterialIndex
from app.schemas.materials import LearningMaterial, MaterialChunk
from app.services.material_retrieval import retrieve_for_misconception
from test_material_retrieval import FakeEmbeddingService, context, settings


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
    )

    assert result.status == "retrieved"
    assert result.results[0].chunk_id == "chunk_001"
    assert embedding.calls[0] == ["Plants use light energy."]
