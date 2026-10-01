from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.prompts.remediation import PROMPT_VERSION, build_remediation_prompt
from app.providers.llm import LLMProviderError, LLMService
from app.providers.remediation_store import RemediationStore
from app.schemas.remediations import (
    EditableRemediationContent,
    GeneratedRemediationDraft,
    RemediationContent,
    RemediationGenerationRequest,
    RemediationGenerationResponse,
    RemediationRecord,
    RemediationReviewRequest,
    RemediationSource,
)


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
) -> RemediationGenerationResponse:
    if request.retrieval.group_id != request.misconception.group_id:
        raise RemediationError(
            "remediation_context_mismatch",
            "The retrieved passages do not belong to the selected misconception group.",
        )
    if request.retrieval.status != "retrieved" or not request.retrieval.results:
        return RemediationGenerationResponse(
            status="insufficient_context",
            message="Insufficient teacher-provided material to generate grounded remediation.",
        )

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
        remediation_id=f"rem_{uuid4().hex}",
        status="generated",
        analysis_id=request.analysis_id,
        group_id=request.misconception.group_id,
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
    store.save(record)
    return RemediationGenerationResponse(status="generated", remediation=record)


def get_remediation(remediation_id: str, *, store: RemediationStore) -> RemediationRecord:
    record = store.get(remediation_id)
    if record is None:
        raise RemediationError("remediation_not_found", "This remediation does not exist in the current backend session.")
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
    store.save(record)
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
        if len(value) > 4_000:
            raise RemediationError("remediation_invalid_content", f"{field_name} is too long.")
        setattr(content, field_name, value)
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
