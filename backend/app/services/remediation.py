import asyncio
from datetime import UTC, datetime
from hashlib import sha256
import json
from time import perf_counter
from typing import Any, NoReturn

from app.concurrency import run_in_worker
from app.config import MaterialSettings
from app.locks import AsyncKeyedLocks
from app.prompts.remediation import PROMPT_VERSION, build_remediation_prompt
from app.providers.analysis_store import AnalysisStore
from app.providers.embeddings import EmbeddingService
from app.providers.group_review_store import GroupReviewStore
from app.providers.llm import LLMProviderError, LLMService
from app.providers.material_index import MaterialIndex
from app.providers.remediation_store import RemediationStore
from app.schemas.materials import (
    MaterialChunk,
    MaterialRetrievalResponse,
    MisconceptionRetrievalContext,
    RetrievedChunk,
)
from app.schemas.remediations import (
    MAX_REMEDIATION_FIELD_CHARS,
    EditableRemediationContent,
    GeneratedRemediationDraft,
    RemediationContent,
    RemediationGenerationRequest,
    RemediationGenerationResponse,
    RemediationMisconceptionContext,
    RemediationRecord,
    RemediationReviewRequest,
    RemediationSource,
)
from app.services.group_reviews import GroupReviewError, group_review_lock, resolve_reviewed_group
from app.services.material_ingestion import MaterialError
from app.services.material_retrieval import retrieve_for_misconception
from app.telemetry import log_stage


MAX_GENERATION_SOURCE_CHARS = 12_000
_GENERATION_LOCKS = AsyncKeyedLocks()


class RemediationError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details or {}


async def generate_grounded_remediation(
    request: RemediationGenerationRequest,
    *,
    llm_service: LLMService,
    store: RemediationStore,
    analysis_store: AnalysisStore,
    material_index: MaterialIndex,
    review_store: GroupReviewStore,
    embedding_service: EmbeddingService,
    settings: MaterialSettings,
) -> RemediationGenerationResponse:
    retrieval = await run_in_worker(
        _retrieve_generation_context,
        request,
        analysis_store=analysis_store,
        material_index=material_index,
        review_store=review_store,
        embedding_service=embedding_service,
        settings=settings,
    )
    if retrieval.status != "retrieved":
        return RemediationGenerationResponse(
            status="insufficient_context",
            message="Insufficient teacher-provided material to generate grounded remediation.",
        )

    if _chunk_ids(request.retrieval) != _chunk_ids(retrieval):
        _raise_context_mismatch("retrieval.results")
    if any(
        _passage_snapshot(supplied) != _passage_snapshot(selected)
        for supplied, selected in zip(request.retrieval.results, retrieval.results, strict=True)
    ):
        _raise_context_mismatch("retrieval.results.chunk")
    source_chars = sum(len(item.text) for item in retrieval.results)
    if source_chars > MAX_GENERATION_SOURCE_CHARS:
        raise RemediationError(
            "generation_context_too_large",
            "The retrieved teacher-material passages are too long to generate an intervention.",
            details={"source_chars": source_chars, "max_source_chars": MAX_GENERATION_SOURCE_CHARS},
        )

    request = request.model_copy(update={"retrieval": retrieval})
    remediation_id = _remediation_id(request)
    async with _GENERATION_LOCKS.hold(remediation_id):
        existing = await run_in_worker(store.get, remediation_id)
        if existing is not None:
            return RemediationGenerationResponse(status="generated", remediation=existing)

        prompt = build_remediation_prompt(request)
        try:
            draft = await llm_service.generate_remediation(prompt)
        except LLMProviderError as error:
            raise RemediationError(error.code, error.message, retryable=error.retryable) from error
        except Exception as error:
            raise RemediationError(
                "llm_generation_failed",
                "The intervention could not be generated. No remediation was saved.",
                retryable=True,
                details={"provider_error": type(error).__name__},
            ) from error

        draft = _validate_draft(draft, allowed_source_ids={item.chunk_id for item in request.retrieval.results})
        content = RemediationContent(**draft.model_dump())
        now = datetime.now(UTC)
        record = RemediationRecord(
            remediation_id=remediation_id,
            status="generated",
            analysis_id=request.analysis_id,
            group_id=request.misconception.group_id,
            source_group_ids=request.misconception.source_group_ids,
            provider=llm_service.provider_name,
            model=llm_service.model_id,
            prompt_version=PROMPT_VERSION,
            generated_content=content.model_copy(deep=True),
            content=content.model_copy(deep=True),
            sources=[
                RemediationSource(
                    material_id=request.retrieval.material.material_id,
                    material_title=request.retrieval.material.title,
                    filename=request.retrieval.material.filename,
                    chunk_id=item.chunk_id,
                    chunk_index=item.chunk_index,
                    text=item.text,
                    similarity=item.similarity,
                    start_char=item.start_char,
                    end_char=item.end_char,
                )
                for item in request.retrieval.results
            ],
            created_at=now,
            updated_at=now,
        )
        started = perf_counter()
        save = asyncio.create_task(run_in_worker(
            _save_if_review_is_current,
            request,
            record,
            store,
            analysis_store,
            material_index,
            review_store,
        ))
        try:
            await asyncio.shield(save)
        except asyncio.CancelledError:
            # Preserve the generation lock until an admitted save settles.
            while not save.done():
                try:
                    await asyncio.shield(save)
                except asyncio.CancelledError:
                    continue
                except Exception:
                    break
            if not save.cancelled():
                save.exception()
            raise
        log_stage("database_persistence", (perf_counter() - started) * 1000, operation="remediation_save")
        return RemediationGenerationResponse(status="generated", remediation=record)


def _save_if_review_is_current(
    request: RemediationGenerationRequest,
    record: RemediationRecord,
    store: RemediationStore,
    analysis_store: AnalysisStore,
    material_index: MaterialIndex,
    review_store: GroupReviewStore,
) -> None:
    with group_review_lock(request.analysis_id):
        _validate_generation_context(
            request,
            analysis_store=analysis_store,
            material_index=material_index,
            review_store=review_store,
        )
        store.save(record)


def _chunk_ids(retrieval: MaterialRetrievalResponse) -> list[str]:
    return [item.chunk_id for item in retrieval.results]


def _passage_snapshot(chunk: MaterialChunk | RetrievedChunk) -> tuple[int, str, int, int]:
    return chunk.chunk_index, chunk.text, chunk.start_char, chunk.end_char


def _remediation_id(request: RemediationGenerationRequest) -> str:
    identity = {
        "retrieval_identity": "server_v1",
        "generation_request_id": request.generation_request_id,
        "analysis_id": request.analysis_id,
        "group_id": request.misconception.group_id,
        "material_id": request.retrieval.material.material_id,
        "chunk_ids": _chunk_ids(request.retrieval),
    }
    digest = sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return f"rem_{digest[:32]}"


def _retrieve_generation_context(
    request: RemediationGenerationRequest,
    *,
    analysis_store: AnalysisStore,
    material_index: MaterialIndex,
    review_store: GroupReviewStore,
    embedding_service: EmbeddingService,
    settings: MaterialSettings,
) -> MaterialRetrievalResponse:
    context = _validate_generation_context(
        request,
        analysis_store=analysis_store,
        material_index=material_index,
        review_store=review_store,
    )
    material_id = request.retrieval.material.material_id
    try:
        retrieval = retrieve_for_misconception(
            material_id,
            context,
            embedding_service=embedding_service,
            material_index=material_index,
            settings=settings,
            analysis_store=analysis_store,
            review_store=review_store,
        )
    except MaterialError as error:
        if error.code == "material_not_found":
            _raise_missing_material(material_id)
        if error.code == "analysis_not_found":
            _raise_missing_analysis(context.analysis_id)
        if error.code == "group_review_context_mismatch":
            _raise_context_mismatch("misconception")
        if error.code == "reviewed_group_not_available":
            raise RemediationError(error.code, error.message, details=error.details) from error
        raise

    if retrieval.material != request.retrieval.material:
        _raise_context_mismatch("retrieval.material")
    if retrieval.source_group_ids != request.misconception.source_group_ids:
        _raise_context_mismatch("retrieval.source_group_ids")
    return retrieval


def _validate_generation_context(
    request: RemediationGenerationRequest,
    *,
    analysis_store: AnalysisStore,
    material_index: MaterialIndex,
    review_store: GroupReviewStore,
) -> MisconceptionRetrievalContext:
    analysis = analysis_store.get(request.analysis_id)
    if analysis is None:
        _raise_missing_analysis(request.analysis_id)
    material_id = request.retrieval.material.material_id
    material = material_index.get(material_id)
    if material is None:
        _raise_missing_material(material_id)

    result = analysis.result
    if result.analysis_id != request.analysis_id:
        _raise_context_mismatch("analysis_id")

    try:
        group = resolve_reviewed_group(
            request.analysis_id, request.misconception.group_id, analysis_store, review_store
        )
    except GroupReviewError as error:
        if error.code == "analysis_not_found":
            _raise_missing_analysis(request.analysis_id)
        raise RemediationError(error.code, error.message, details=error.details) from error

    assessment = result.assessment
    class_context = {
        "grade_level": request.grade_level,
        "subject": request.subject,
        "topic": request.topic,
    }
    canonical_class_context = {
        "grade_level": assessment.grade_level,
        "subject": assessment.subject,
        "topic": assessment.topic,
    }
    if class_context != canonical_class_context:
        _raise_context_mismatch("class_context")

    canonical_misconception = RemediationMisconceptionContext(
        group_id=group.reviewed_group_id,
        source_group_ids=group.source_group_ids,
        provisional_label=group.display_label,
        question_id=group.question_id,
        question=group.question,
        correct_answer=group.correct_answer,
        support_count=group.support_count,
        eligible_response_count=group.eligible_response_count,
        representative_responses=group.representative_responses,
    )
    if request.misconception != canonical_misconception:
        _raise_context_mismatch("misconception")
    if request.retrieval.group_id != group.reviewed_group_id:
        _raise_context_mismatch("retrieval.group_id")
    if request.retrieval.source_group_ids != group.source_group_ids:
        _raise_context_mismatch("retrieval.source_group_ids")
    if request.retrieval.material != material.material:
        _raise_context_mismatch("retrieval.material")
    if request.retrieval.retrieval.embedding_model != material.material.embedding_model:
        _raise_context_mismatch("retrieval.embedding_model")

    chunks_by_id = {chunk.chunk_id: chunk for chunk in material.chunks}
    if len(chunks_by_id) != len(material.chunks):
        _raise_context_mismatch("material.chunks")

    seen_chunk_ids: set[str] = set()
    for supplied in request.retrieval.results:
        if supplied.chunk_id in seen_chunk_ids:
            _raise_context_mismatch("retrieval.results")
        seen_chunk_ids.add(supplied.chunk_id)
        chunk = chunks_by_id.get(supplied.chunk_id)
        if chunk is None:
            _raise_context_mismatch("retrieval.results.chunk_id")
        if _passage_snapshot(supplied) != _passage_snapshot(chunk):
            _raise_context_mismatch("retrieval.results.chunk")
    return MisconceptionRetrievalContext(
        analysis_id=result.analysis_id,
        group_id=group.reviewed_group_id,
        question_id=group.question_id,
        question=group.question,
        correct_answer=group.correct_answer,
        representative_answers=[item.answer for item in group.representative_responses],
    )


def _raise_missing_analysis(analysis_id: str) -> NoReturn:
    raise RemediationError(
        "remediation_context_not_found",
        "The selected analysis is no longer available. Reload the analysis before generating an intervention.",
        details={"resource": "analysis", "analysis_id": analysis_id},
    )


def _raise_missing_material(material_id: str) -> NoReturn:
    raise RemediationError(
        "remediation_context_not_found",
        "The selected teacher material is no longer available. Retrieve passages again before generating an intervention.",
        details={"resource": "material", "material_id": material_id},
    )


def _raise_context_mismatch(field: str) -> NoReturn:
    raise RemediationError(
        "remediation_context_mismatch",
        "The generation context no longer matches stored analysis or teacher-material evidence. Reload the workflow and retrieve passages again.",
        details={"field": field},
    )


def get_remediation(remediation_id: str, *, store: RemediationStore) -> RemediationRecord:
    record = store.get(remediation_id)
    if record is None:
        raise RemediationError("remediation_not_found", "This remediation does not exist in persistent storage.")
    return record


def review_remediation(
    remediation_id: str,
    request: RemediationReviewRequest,
    *,
    store: RemediationStore,
) -> RemediationRecord:
    record = get_remediation(remediation_id, store=store)
    if record.status != "generated":
        raise RemediationError(
            "remediation_invalid_transition",
            f"A {record.status} remediation can no longer be edited or reviewed.",
        )
    if request.action == "save" and request.edited_content is None:
        raise RemediationError("remediation_edit_required", "Provide edited_content before saving changes.")

    if request.edited_content is not None:
        edited = _validate_edit(request.edited_content)
        record.content = RemediationContent(
            **edited.model_dump(),
            source_references=list(record.content.source_references),
        )

    if request.action == "approve":
        record.status = "approved"
    elif request.action == "reject":
        record.status = "rejected"

    record.review_notes = request.review_notes.strip() if request.review_notes and request.review_notes.strip() else None
    record.updated_at = datetime.now(UTC)
    started = perf_counter()
    store.save(record)
    log_stage("database_persistence", (perf_counter() - started) * 1000, operation="remediation_update")
    return record


def _validate_draft(draft: GeneratedRemediationDraft, *, allowed_source_ids: set[str]) -> GeneratedRemediationDraft:
    _validate_edit(draft)
    references = list(dict.fromkeys(reference.strip() for reference in draft.source_references if reference.strip()))
    if not references or not set(references).issubset(allowed_source_ids):
        raise RemediationError(
            "llm_ungrounded_output",
            "The generated intervention cited missing or unknown teaching passages. No remediation was saved.",
            retryable=True,
        )
    draft.source_references = references
    return draft


def _validate_edit(content: EditableRemediationContent) -> EditableRemediationContent:
    field_names = (
        "misconception_summary",
        "learning_objective",
        "teacher_explanation",
        "corrected_concept",
        "activity",
    )
    for field_name in field_names:
        value = getattr(content, field_name).strip()
        if not value:
            raise RemediationError("remediation_invalid_content", f"{field_name} cannot be empty.")
        if len(value) > MAX_REMEDIATION_FIELD_CHARS:
            raise RemediationError("remediation_invalid_content", f"{field_name} is too long.")
        setattr(content, field_name, value)
    try:
        content.validate_analogy_and_follow_up_lengths()
    except ValueError as error:
        raise RemediationError("remediation_invalid_content", str(error)) from error
    if content.analogy is not None:
        content.analogy = content.analogy.strip() or None
    if not 1 <= len(content.follow_up_questions) <= 3:
        raise RemediationError("remediation_invalid_content", "Include between one and three follow-up questions.")
    for item in content.follow_up_questions:
        item.prompt = item.prompt.strip()
        item.expected_answer = item.expected_answer.strip()
        if not item.prompt or not item.expected_answer:
            raise RemediationError("remediation_invalid_content", "Follow-up questions and expected answers cannot be empty.")
    return content
