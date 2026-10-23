from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FollowUpComparisonLink(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_analysis_id: str = Field(min_length=1, max_length=100)
    group_id: str = Field(min_length=1, max_length=100)
    remediation_id: str = Field(min_length=1, max_length=100)


class AssessmentResultSnapshot(BaseModel):
    analysis_id: str
    assessment_title: str
    filename: str
    answered_students: int
    correct_students: int
    affected_students: int
    misconception_prevalence_percent: float


class StudentTransitionMetrics(BaseModel):
    baseline_affected_students: int
    resolved_correct: int
    changed_but_still_incorrect: int
    still_struggling: int
    missing_from_baseline_group: int
    new_affected_students: int


class ComparisonMetrics(BaseModel):
    before: AssessmentResultSnapshot
    after: AssessmentResultSnapshot
    matched_answered_students: int
    missing_follow_up_students: int
    percentage_point_reduction: float
    correct_percentage_point_change: float
    transitions: StudentTransitionMetrics


class ResultsTrace(BaseModel):
    baseline_assessment_id: str
    follow_up_assessment_id: str
    baseline_analysis_id: str
    follow_up_analysis_id: str
    baseline_group_id: str
    baseline_source_group_ids: list[str] = Field(default_factory=list)
    follow_up_group_id: str | None
    remediation_id: str
    remediation_status: Literal["approved"]
    comparison_method: Literal["same_question_member_overlap_v1"]

    @model_validator(mode="after")
    def restore_legacy_source_group(self):
        if not self.baseline_source_group_ids:
            self.baseline_source_group_ids = [self.baseline_group_id]
        return self


class FollowUpComparisonRecord(BaseModel):
    comparison_id: str
    status: Literal["completed", "insufficient_data"]
    data_label: Literal["teacher_upload", "synthetic_demo"]
    subject: str
    grade_level: str
    topic: str
    question_id: str
    question: str
    misconception_label: str
    trace: ResultsTrace | None = None
    metrics: ComparisonMetrics | None = None
    message: str | None = None
    created_at: datetime
