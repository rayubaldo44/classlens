from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .analysis import RepresentativeResponse
from .materials import MaterialRetrievalResponse


class FollowUpQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(description="One concise check-for-understanding question.")
    expected_answer: str = Field(description="A concise answer or teacher rubric note.")


class EditableRemediationContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    misconception_summary: str
    learning_objective: str
    teacher_explanation: str
    corrected_concept: str
    activity: str
    analogy: str | None = None
    follow_up_questions: list[FollowUpQuestion]


class GeneratedRemediationDraft(EditableRemediationContent):
    source_references: list[str] = Field(
        description="One or more source chunk IDs that directly support the intervention."
    )


class RemediationContent(EditableRemediationContent):
    source_references: list[str]


class RemediationMisconceptionContext(BaseModel):
    group_id: str = Field(min_length=1, max_length=100)
    source_group_ids: list[str] = Field(default_factory=list)
    provisional_label: str = Field(min_length=1, max_length=300)
    question_id: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=1, max_length=2000)
    correct_answer: str = Field(min_length=1, max_length=4000)
    support_count: int = Field(ge=1)
    eligible_response_count: int = Field(ge=1)
    representative_responses: list[RepresentativeResponse] = Field(min_length=1)

    @model_validator(mode="after")
    def default_source_group_ids(self):
        if not self.source_group_ids:
            self.source_group_ids = [self.group_id]
        return self


class RemediationGenerationRequest(BaseModel):
    generation_request_id: str = Field(
        min_length=8,
        max_length=100,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    analysis_id: str = Field(min_length=1, max_length=100)
    grade_level: str = Field(min_length=1, max_length=100)
    subject: str = Field(min_length=1, max_length=200)
    topic: str = Field(min_length=1, max_length=300)
    misconception: RemediationMisconceptionContext
    retrieval: MaterialRetrievalResponse


class RemediationSource(BaseModel):
    material_id: str
    material_title: str
    filename: str
    chunk_id: str
    chunk_index: int
    text: str
    similarity: float
    start_char: int
    end_char: int


class RemediationRecord(BaseModel):
    remediation_id: str
    status: Literal["generated", "approved", "rejected"]
    analysis_id: str
    group_id: str
    source_group_ids: list[str] = Field(default_factory=list)
    provider: str
    model: str
    prompt_version: Literal["grounded_remediation_v1"]
    generated_content: RemediationContent
    content: RemediationContent
    sources: list[RemediationSource]
    review_notes: str | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def default_source_group_ids(self):
        if not self.source_group_ids:
            self.source_group_ids = [self.group_id]
        return self


class RemediationGenerationResponse(BaseModel):
    status: Literal["generated", "insufficient_context"]
    remediation: RemediationRecord | None = None
    message: str | None = None


class RemediationReviewRequest(BaseModel):
    action: Literal["save", "approve", "reject"]
    edited_content: EditableRemediationContent | None = None
    review_notes: str | None = Field(default=None, max_length=2000)
