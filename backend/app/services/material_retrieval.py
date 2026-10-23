import math
from time import perf_counter

from app.config import MaterialSettings
from app.providers.embeddings import EmbeddingService
from app.providers.material_index import MaterialIndex
from app.providers.analysis_store import AnalysisStore
from app.providers.group_review_store import GroupReviewStore
from app.schemas.materials import (
    MaterialRetrievalResponse,
    MisconceptionRetrievalContext,
    RetrievalMetadata,
    RetrievedChunk,
)
from app.services.material_ingestion import MaterialError
from app.services.material_ingestion import _normalize_embeddings
from app.services.group_reviews import GroupReviewError, resolve_reviewed_group
from app.telemetry import log_error, log_stage


def retrieve_for_misconception(
    material_id: str,
    context: MisconceptionRetrievalContext,
    *,
    embedding_service: EmbeddingService,
    material_index: MaterialIndex,
    settings: MaterialSettings,
    analysis_store: AnalysisStore | None = None,
    review_store: GroupReviewStore | None = None,
) -> MaterialRetrievalResponse:
    if analysis_store is None or review_store is None:
        raise MaterialError("review_context_unavailable", "Reviewed evidence could not be resolved.")
    try:
        reviewed = resolve_reviewed_group(context.analysis_id, context.group_id, analysis_store, review_store)
    except GroupReviewError as error:
        raise MaterialError(error.code, error.message, details=error.details) from error
    supplied = (context.question_id, context.question, context.correct_answer, context.representative_answers)
    canonical = (
        reviewed.question_id, reviewed.question, reviewed.correct_answer,
        [item.answer for item in reviewed.representative_responses],
    )
    if supplied != canonical:
        raise MaterialError(
            "group_review_context_mismatch",
            "The selected reviewed group no longer matches the stored evidence. Reload the analysis.",
        )
    source_group_ids = reviewed.source_group_ids
    record = material_index.get(material_id)
    if record is None:
        raise MaterialError("material_not_found", "This learning material is not in the current backend index.", details={"material_id": material_id})
    if record.material.embedding_model != embedding_service.model_id:
        raise MaterialError(
            "embedding_model_mismatch",
            "This material was indexed with a different embedding model. Ingest it again before retrieval.",
        )

    if not record.embeddings:
        started = perf_counter()
        try:
            vectors = _normalize_embeddings(
                embedding_service.embed([chunk.text for chunk in record.chunks]),
                len(record.chunks),
            )
            cached = tuple(tuple(vector) for vector in vectors)
            setter = getattr(material_index, "set_embeddings", None)
            if setter is not None:
                setter(material_id, cached)
            record = material_index.get(material_id) or record
        except MaterialError:
            raise
        except Exception as error:
            log_error("material_reindex", "material_embedding_failed", provider_error=type(error).__name__, chunk_count=len(record.chunks))
            raise MaterialError(
                "material_embedding_failed",
                "The persisted learning material could not be re-indexed.",
                retryable=True,
                details={"provider_error": type(error).__name__},
            ) from error
        log_stage("material_reindex", (perf_counter() - started) * 1000, chunk_count=len(record.chunks), model=embedding_service.model_id)

    query = _build_query(context)
    started = perf_counter()
    try:
        embeddings = embedding_service.embed([query])
        query_vector = _normalize_query_embedding(embeddings)
        if len(query_vector) != record.material.embedding_dimension:
            raise MaterialError(
                "material_embedding_invalid_response",
                "The query vector dimensions do not match the indexed material.",
                retryable=True,
            )
        hits = material_index.search(material_id, query_vector, settings.retrieval_top_k)
    except MaterialError:
        raise
    except Exception as error:
        log_error("retrieval", "material_retrieval_failed", retrieval_error=type(error).__name__)
        raise MaterialError(
            "material_retrieval_failed",
            "Relevant material could not be retrieved.",
            retryable=True,
            details={"retrieval_error": type(error).__name__},
        ) from error
    log_stage("retrieval", (perf_counter() - started) * 1000, hit_count=len(hits), material_id=material_id)

    results = [
        RetrievedChunk(
            chunk_id=hit.chunk.chunk_id,
            chunk_index=hit.chunk.chunk_index,
            text=hit.chunk.text,
            similarity=round(hit.similarity, 4),
            start_char=hit.chunk.start_char,
            end_char=hit.chunk.end_char,
        )
        for hit in hits
        if hit.similarity >= settings.minimum_relevance_score
    ]
    if results:
        status = "retrieved"
        message = None
    else:
        status = "insufficient_relevant_context"
        message = "No passage in this material met the minimum relevance threshold. Grounded remediation must remain unavailable."
    return MaterialRetrievalResponse(
        status=status,
        group_id=context.group_id,
        source_group_ids=source_group_ids,
        material=record.material,
        retrieval=RetrievalMetadata(
            algorithm="cosine_similarity_v1",
            top_k=settings.retrieval_top_k,
            minimum_relevance_score=settings.minimum_relevance_score,
            embedding_model=embedding_service.model_id,
        ),
        results=results,
        message=message,
    )


def _build_query(context: MisconceptionRetrievalContext) -> str:
    evidence = " ".join(context.representative_answers)
    return (
        f"Question: {context.question}. "
        f"Student answer examples: {evidence}. "
        f"Accurate reference: {context.correct_answer}"
    )


def _normalize_query_embedding(embeddings: list[list[float]]) -> list[float]:
    if len(embeddings) != 1 or not embeddings[0]:
        raise MaterialError("material_embedding_invalid_response", "The embedding provider did not return one query vector.", retryable=True)
    vector = embeddings[0]
    if any(not math.isfinite(value) for value in vector):
        raise MaterialError("material_embedding_invalid_response", "The embedding provider returned non-finite values.", retryable=True)
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude == 0:
        raise MaterialError("material_embedding_invalid_response", "The embedding provider returned an empty query vector.", retryable=True)
    return [value / magnitude for value in vector]
