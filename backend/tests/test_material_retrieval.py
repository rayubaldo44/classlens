import asyncio
from collections.abc import Sequence

import httpx
import pytest

from app.api.routes.analysis import get_embedding_service
from app.config import MaterialSettings
from app.main import app
from app.providers.material_index import InMemoryMaterialIndex, get_material_index
from app.schemas.materials import MisconceptionRetrievalContext
from app.services.material_ingestion import MaterialError, _chunk_text, ingest_learning_material
from app.services.material_retrieval import retrieve_for_misconception


class FakeEmbeddingService:
    model_id = "test/material-embeddings"

    def __init__(self, vectors: Sequence[Sequence[float]] | None = None) -> None:
        self.vectors = [list(vector) for vector in vectors] if vectors is not None else None
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        if self.vectors is not None:
            return self.vectors
        return [[1.0, 0.0] for _ in texts]


def settings(*, chunk_size: int = 900, overlap: int = 120, top_k: int = 3, threshold: float = 0.42) -> MaterialSettings:
    return MaterialSettings(
        chunk_size_chars=chunk_size,
        chunk_overlap_chars=overlap,
        retrieval_top_k=top_k,
        minimum_relevance_score=threshold,
    )


def context(**overrides: object) -> MisconceptionRetrievalContext:
    values: dict[str, object] = {
        "group_id": "grp_demo",
        "question_id": "Q1",
        "question": "How do plants make food?",
        "correct_answer": "Plants make glucose from carbon dioxide and water using light energy.",
        "representative_answers": ["Plants eat sunlight.", "Sunlight is plant food.", "Plants consume sunlight to grow."],
    }
    values.update(overrides)
    return MisconceptionRetrievalContext(**values)


def test_chunking_keeps_offsets_and_overlap_inside_normalized_source() -> None:
    text = ("Plants use light energy and water to produce glucose.\n\n" * 28).strip()

    chunks = _chunk_text(text, chunk_size=300, overlap=40)

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.text == text[chunk.start_char:chunk.end_char]
    for left, right in zip(chunks, chunks[1:], strict=False):
        assert right.start_char < left.end_char
        assert right.start_char >= left.start_char
        assert text[right.start_char - 1].isspace()


def test_ingestion_embeds_and_indexes_deterministic_material() -> None:
    content = b"Photosynthesis uses carbon dioxide and water.\n\nRoots absorb water and minerals."
    fake = FakeEmbeddingService()
    index = InMemoryMaterialIndex()

    result = ingest_learning_material(
        content,
        filename="../../lesson.txt",
        title="  Lesson  ",
        source_kind="teacher_upload",
        embedding_service=fake,
        material_index=index,
        settings=settings(chunk_size=300),
    )

    assert result.status == "ready"
    assert result.material.filename == "lesson.txt"
    assert result.material.title == "Lesson"
    assert result.material.chunk_count == 1
    assert result.material.embedding_dimension == 2
    assert index.get(result.material.material_id) is not None
    assert fake.calls == [["Photosynthesis uses carbon dioxide and water.\n\nRoots absorb water and minerals."]]


@pytest.mark.parametrize(
    ("content", "code"),
    [(b"", "material_empty"), (b"\xff", "material_encoding_error"), (b"\x00bad", "material_invalid_text")],
)
def test_invalid_or_empty_text_fails_with_specific_error(content: bytes, code: str) -> None:
    with pytest.raises(MaterialError) as caught:
        ingest_learning_material(
            content,
            filename="notes.txt",
            title=None,
            source_kind="teacher_upload",
            embedding_service=FakeEmbeddingService(),
            material_index=InMemoryMaterialIndex(),
            settings=settings(),
        )
    assert caught.value.code == code


def test_embedding_failure_does_not_index_material() -> None:
    class FailingEmbeddingService(FakeEmbeddingService):
        def embed(self, texts: list[str]) -> list[list[float]]:
            raise RuntimeError("provider secret detail")

    index = InMemoryMaterialIndex()
    with pytest.raises(MaterialError) as caught:
        ingest_learning_material(
            b"Photosynthesis uses light energy.",
            filename="notes.txt",
            title=None,
            source_kind="teacher_upload",
            embedding_service=FailingEmbeddingService(),
            material_index=index,
            settings=settings(),
        )

    assert caught.value.code == "material_embedding_failed"
    assert "provider secret detail" not in caught.value.message
    assert index.get("mat_missing") is None


def test_material_index_failure_returns_actionable_error() -> None:
    class FailingIndex(InMemoryMaterialIndex):
        def upsert(self, record):
            raise RuntimeError("storage detail")

    with pytest.raises(MaterialError) as caught:
        ingest_learning_material(
            b"Photosynthesis uses light energy.",
            filename="notes.txt",
            title=None,
            source_kind="teacher_upload",
            embedding_service=FakeEmbeddingService(),
            material_index=FailingIndex(),
            settings=settings(),
        )
    assert caught.value.code == "material_index_failed"
    assert "storage detail" not in caught.value.message


def test_empty_chunk_output_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.material_ingestion._chunk_text", lambda *_: [])
    with pytest.raises(MaterialError) as caught:
        ingest_learning_material(
            b"Valid source text.",
            filename="notes.txt",
            title=None,
            source_kind="teacher_upload",
            embedding_service=FakeEmbeddingService(),
            material_index=InMemoryMaterialIndex(),
            settings=settings(),
        )
    assert caught.value.code == "no_chunks_generated"


def test_retrieval_ranks_relevant_chunks_and_filters_below_threshold() -> None:
    content = (
        b"Plants make glucose using light energy, carbon dioxide, and water. "
        b"Leaves carry out photosynthesis when light is available.\n\n"
        b"The school garden has a blue fence. The garden tools are kept in a locked shed."
    )
    index = InMemoryMaterialIndex()
    ingestion = ingest_learning_material(
        content,
        filename="lesson.txt",
        title=None,
        source_kind="teacher_upload",
        embedding_service=FakeEmbeddingService([[1, 0], [1, 0]]),
        material_index=index,
        settings=settings(chunk_size=200, overlap=30),
    )
    result = retrieve_for_misconception(
        ingestion.material.material_id,
        context(),
        embedding_service=FakeEmbeddingService([[1, 0]]),
        material_index=index,
        settings=settings(chunk_size=200, overlap=30, threshold=0.8),
    )

    assert result.status == "retrieved"
    assert "Plants make glucose using light energy" in result.results[0].text
    assert result.results[0].similarity == 1.0
    assert result.results[0].text in content.decode()

    no_match = retrieve_for_misconception(
        ingestion.material.material_id,
        context(),
        embedding_service=FakeEmbeddingService([[0, 1]]),
        material_index=index,
        settings=settings(chunk_size=200, overlap=30, threshold=0.8),
    )
    assert no_match.status == "insufficient_relevant_context"
    assert no_match.results == []


def test_retrieval_requires_ingested_material_and_matching_model() -> None:
    with pytest.raises(MaterialError) as caught:
        retrieve_for_misconception(
            "mat_missing",
            context(),
            embedding_service=FakeEmbeddingService(),
            material_index=InMemoryMaterialIndex(),
            settings=settings(),
        )
    assert caught.value.code == "material_not_found"


def test_retrieval_index_failure_is_reported_without_sources() -> None:
    index = InMemoryMaterialIndex()
    ingestion = ingest_learning_material(
        b"Plants make glucose during photosynthesis.",
        filename="lesson.txt",
        title=None,
        source_kind="teacher_upload",
        embedding_service=FakeEmbeddingService(),
        material_index=index,
        settings=settings(),
    )
    index.search = lambda *_args: (_ for _ in ()).throw(RuntimeError("index detail"))

    with pytest.raises(MaterialError) as caught:
        retrieve_for_misconception(
            ingestion.material.material_id,
            context(),
            embedding_service=FakeEmbeddingService(),
            material_index=index,
            settings=settings(),
        )
    assert caught.value.code == "material_retrieval_failed"
    assert "index detail" not in caught.value.message


def test_demo_material_api_returns_typed_ingestion_response() -> None:
    fake = FakeEmbeddingService()
    index = InMemoryMaterialIndex()

    async def override_embedding_service() -> FakeEmbeddingService:
        return fake

    async def override_material_index() -> InMemoryMaterialIndex:
        return index

    app.dependency_overrides[get_embedding_service] = override_embedding_service
    app.dependency_overrides[get_material_index] = override_material_index

    async def send() -> tuple[httpx.Response, httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            ingestion_response = await client.post("/api/v1/learning-materials/demo/photosynthesis/ingest")
            material_id = ingestion_response.json()["material"]["material_id"]
            retrieval_response = await client.post(
                f"/api/v1/learning-materials/{material_id}/retrieve",
                json=context().model_dump(),
            )
            return ingestion_response, retrieval_response

    try:
        response, retrieval_response = asyncio.run(send())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["material"]["source_kind"] == "synthetic_demo"
    assert body["material"]["chunk_count"] > 1
    assert len(index.get(body["material"]["material_id"]).chunks) == body["material"]["chunk_count"]
    assert retrieval_response.status_code == 200
    assert retrieval_response.json()["status"] == "retrieved"
    assert retrieval_response.json()["results"]


def test_material_api_rejects_pdf_and_returns_structured_empty_file_error() -> None:
    async def send() -> tuple[httpx.Response, httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            unsupported = await client.post(
                "/api/v1/learning-materials/ingest",
                files={"file": ("lesson.pdf", b"pdf", "application/pdf")},
            )
            empty = await client.post(
                "/api/v1/learning-materials/ingest",
                files={"file": ("empty.txt", b"", "text/plain")},
            )
            return unsupported, empty

    unsupported, empty = asyncio.run(send())
    assert unsupported.status_code == 415
    assert unsupported.json()["error"]["code"] == "unsupported_material_type"
    assert empty.status_code == 400
    assert empty.json()["error"]["code"] == "material_empty"


def test_teacher_material_upload_api_ingests_text_file() -> None:
    index = InMemoryMaterialIndex()

    async def override_embedding_service() -> FakeEmbeddingService:
        return FakeEmbeddingService()

    async def override_material_index() -> InMemoryMaterialIndex:
        return index

    app.dependency_overrides[get_embedding_service] = override_embedding_service
    app.dependency_overrides[get_material_index] = override_material_index

    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/api/v1/learning-materials/ingest",
                files={"file": ("teacher_notes.txt", b"Photosynthesis uses light energy to make glucose.", "text/plain")},
                data={"title": "Teacher notes"},
            )

    try:
        response = asyncio.run(send())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["material"]["source_kind"] == "teacher_upload"
    assert body["material"]["filename"] == "teacher_notes.txt"
    assert body["material"]["title"] == "Teacher notes"
