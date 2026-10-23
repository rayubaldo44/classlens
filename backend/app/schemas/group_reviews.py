from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .analysis import RepresentativeResponse

GroupReviewAction = Literal["rename", "merge", "dismiss", "restore"]
GroupReviewStatus = Literal["active", "dismissed"]


class GroupReviewActionRequest(BaseModel):
    action: GroupReviewAction
    group_ids: list[str] = Field(min_length=1)
    expected_revision: int = Field(default=0, ge=0)
    label: str | None = None
    review_note: str | None = None

    @field_validator("group_ids")
    @classmethod
    def validate_group_ids(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value]
        if any(not item for item in normalized):
            raise ValueError("Group IDs cannot be blank.")
        if len(set(normalized)) != len(normalized):
            raise ValueError("Group IDs must be distinct.")
        return normalized

    @field_validator("label", "review_note")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ReviewedMisconceptionGroup(BaseModel):
    reviewed_group_id: str
    display_label: str
    status: GroupReviewStatus
    source_group_ids: list[str] = Field(min_length=1)
    question_id: str
    question: str
    correct_answer: str
    support_count: int = Field(gt=0)
    eligible_response_count: int = Field(gt=0)
    member_student_ids: list[str] = Field(min_length=1)
    representative_responses: list[RepresentativeResponse]
    coherence: float | None


class GroupReviewState(BaseModel):
    analysis_id: str
    revision: int = Field(ge=0)
    groups: list[ReviewedMisconceptionGroup] = Field(default_factory=list)


class GroupReviewEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    analysis_id: str
    sequence: int = Field(gt=0)
    action: GroupReviewAction
    source_group_ids: list[str] = Field(min_length=1)
    resulting_reviewed_group_id: str
    previous_state: GroupReviewState | None
    next_state: GroupReviewState
    review_note: str | None = None
    created_at: datetime


class GroupReviewResponse(BaseModel):
    analysis_id: str
    revision: int = Field(ge=0)
    active_groups: list[ReviewedMisconceptionGroup]
    dismissed_groups: list[ReviewedMisconceptionGroup]
    locked_group_ids: list[str]
    events: list[GroupReviewEvent]


class StoredGroupReviews(BaseModel):
    state: GroupReviewState
    events: list[GroupReviewEvent]
