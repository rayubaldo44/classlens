from typing import Literal

from pydantic import BaseModel

from .assessment import AssessmentMetadata


class EmbeddingMetadata(BaseModel):
    model_id: str
    dimension: int
    preprocessing: Literal["answer_only_v1"]


class GroupingMetadata(BaseModel):
    algorithm: Literal["complete_link_cosine_v1"]
    similarity_threshold: float
    minimum_support: int


class RepresentativeResponse(BaseModel):
    student_id: str
    answer: str
    similarity_to_medoid: float


class MisconceptionGroup(BaseModel):
    group_id: str
    provisional_label: str
    interpretation_status: Literal["not_requested", "completed", "fallback"]
    question_id: str
    question: str
    correct_answer: str
    support_count: int
    eligible_response_count: int
    member_student_ids: list[str]
    representative_responses: list[RepresentativeResponse]
    coherence: float


class AnalysisSummary(BaseModel):
    response_count: int
    answered_count: int
    blank_count: int
    correct_count: int
    eligible_incorrect_count: int
    grouped_response_count: int
    outlier_count: int
    question_count: int
    group_count: int


class AnalysisResponse(BaseModel):
    assessment_id: str
    analysis_id: str
    status: Literal["completed", "insufficient_data"]
    data_label: Literal["teacher_upload", "synthetic_demo"]
    filename: str
    assessment: AssessmentMetadata
    summary: AnalysisSummary
    embedding: EmbeddingMetadata
    grouping: GroupingMetadata
    groups: list[MisconceptionGroup]
    message: str | None = None
