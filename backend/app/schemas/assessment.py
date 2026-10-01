from typing import Literal

from pydantic import BaseModel


class AssessmentMetadata(BaseModel):
    title: str
    subject: str
    grade_level: str
    topic: str


class NormalizedResponse(BaseModel):
    row_number: int
    student_id: str
    question_id: str
    question: str
    answer: str
    correct_answer: str
    answer_status: Literal["answered", "blank"]
    is_correct: bool


class AssessmentSummary(BaseModel):
    response_count: int
    answered_count: int
    blank_count: int
    student_count: int
    question_count: int
    correct_count: int
    incorrect_count: int


class AssessmentPreview(BaseModel):
    status: Literal["validated"]
    data_label: Literal["teacher_upload", "synthetic_demo"]
    filename: str
    assessment: AssessmentMetadata
    summary: AssessmentSummary
    sample_responses: list[NormalizedResponse]


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, object]
    retryable: bool = False
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
