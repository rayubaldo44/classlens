import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from app.config import AnalysisSettings
from app.providers.analysis_store import AnalysisStore
from app.providers.embeddings import EmbeddingService
from app.providers.remediation_store import RemediationStore
from app.providers.results_store import ResultsStore
from app.schemas.analysis import MisconceptionGroup
from app.schemas.assessment import NormalizedResponse
from app.schemas.results import (
    AssessmentResultSnapshot,
    ComparisonMetrics,
    FollowUpComparisonLink,
    FollowUpComparisonRecord,
    ResultsTrace,
    StudentTransitionMetrics,
)
from app.services.assessment_intake import ParsedAssessment
from app.services.misconception_analysis import analyze_assessment


class ResultsError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.retryable = False


def create_follow_up_comparison(
    link: FollowUpComparisonLink,
    follow_up: ParsedAssessment,
    *,
    embedding_service: EmbeddingService,
    settings: AnalysisSettings,
    analysis_store: AnalysisStore,
    remediation_store: RemediationStore,
    results_store: ResultsStore,
) -> FollowUpComparisonRecord:
    baseline = analysis_store.get(link.baseline_analysis_id)
    if baseline is None:
        raise ResultsError(
            "initial_assessment_not_found",
            "The initial assessment analysis is not available in this backend session. Analyze it again before adding follow-up results.",
        )

    baseline_group = next((group for group in baseline.result.groups if group.group_id == link.group_id), None)
    if baseline_group is None:
        raise ResultsError(
            "misconception_not_found",
            "The selected misconception does not belong to the initial assessment analysis.",
        )

    remediation = remediation_store.get(link.remediation_id)
    if remediation is None:
        raise ResultsError(
            "intervention_not_found",
            "The intervention is not available in this backend session.",
        )
    if remediation.group_id != baseline_group.group_id or remediation.analysis_id != baseline.result.analysis_id:
        raise ResultsError(
            "results_context_mismatch",
            "The approved intervention does not belong to the selected misconception.",
        )
    if remediation.status != "approved":
        raise ResultsError(
            "intervention_not_approved",
            "Approve the intervention before comparing follow-up results.",
        )

    _validate_follow_up_context(baseline.parsed, follow_up, baseline_group)
    follow_up_analysis = analyze_assessment(follow_up, embedding_service, settings)
    analysis_store.save(
        follow_up,
        follow_up_analysis,
        assessment_kind="follow_up",
        baseline_assessment_id=baseline.result.assessment_id,
    )

    follow_up_group = _match_follow_up_group(baseline_group, follow_up_analysis.groups)
    comparison_id = _comparison_id(link, follow_up_analysis.analysis_id)
    trace = ResultsTrace(
        baseline_assessment_id=baseline.result.assessment_id,
        follow_up_assessment_id=follow_up_analysis.assessment_id,
        baseline_analysis_id=baseline.result.analysis_id,
        follow_up_analysis_id=follow_up_analysis.analysis_id,
        baseline_group_id=baseline_group.group_id,
        follow_up_group_id=follow_up_group.group_id if follow_up_group else None,
        remediation_id=remediation.remediation_id,
        remediation_status="approved",
        comparison_method="same_question_member_overlap_v1",
    )

    if follow_up_group is None:
        record = FollowUpComparisonRecord(
            comparison_id=comparison_id,
            status="insufficient_data",
            data_label=follow_up.preview.data_label,
            subject=baseline.result.assessment.subject,
            grade_level=baseline.result.assessment.grade_level,
            topic=baseline.result.assessment.topic,
            question_id=baseline_group.question_id,
            question=baseline_group.question,
            misconception_label=baseline_group.provisional_label,
            trace=trace,
            message=(
                "The follow-up analysis did not produce a recurring group with enough overlapping students "
                "to re-identify this misconception reliably. No improvement percentage was calculated."
            ),
            created_at=datetime.now(UTC),
        )
        results_store.save(record)
        return record

    metrics = _calculate_metrics(
        baseline.parsed.responses,
        follow_up.responses,
        baseline_group,
        follow_up_group,
        baseline_analysis_id=baseline.result.analysis_id,
        follow_up_analysis_id=follow_up_analysis.analysis_id,
        baseline_filename=baseline.result.filename,
        follow_up_filename=follow_up_analysis.filename,
        baseline_title=baseline.result.assessment.title,
        follow_up_title=follow_up_analysis.assessment.title,
    )
    record = FollowUpComparisonRecord(
        comparison_id=comparison_id,
        status="completed",
        data_label=follow_up.preview.data_label,
        subject=baseline.result.assessment.subject,
        grade_level=baseline.result.assessment.grade_level,
        topic=baseline.result.assessment.topic,
        question_id=baseline_group.question_id,
        question=baseline_group.question,
        misconception_label=baseline_group.provisional_label,
        trace=trace,
        metrics=metrics,
        message="Observed before/after change only; this comparison does not establish that the intervention caused the change.",
        created_at=datetime.now(UTC),
    )
    results_store.save(record)
    return record


def get_follow_up_comparison(comparison_id: str, *, results_store: ResultsStore) -> FollowUpComparisonRecord:
    record = results_store.get(comparison_id)
    if record is None:
        raise ResultsError(
            "results_not_found",
            "This before/after comparison does not exist in the current backend session.",
        )
    return record


def _validate_follow_up_context(
    baseline: ParsedAssessment,
    follow_up: ParsedAssessment,
    group: MisconceptionGroup,
) -> None:
    baseline_meta = baseline.preview.assessment
    follow_up_meta = follow_up.preview.assessment
    expected_context = (baseline_meta.subject, baseline_meta.grade_level, baseline_meta.topic)
    received_context = (follow_up_meta.subject, follow_up_meta.grade_level, follow_up_meta.topic)
    if received_context != expected_context:
        raise ResultsError(
            "follow_up_assessment_mismatch",
            "The follow-up assessment subject, grade level, and topic must match the initial assessment.",
        )

    baseline_question = next(
        (response for response in baseline.responses if response.question_id == group.question_id),
        None,
    )
    follow_up_question = next(
        (response for response in follow_up.responses if response.question_id == group.question_id),
        None,
    )
    if baseline_question is None or follow_up_question is None:
        raise ResultsError(
            "follow_up_question_missing",
            "The follow-up assessment does not include the question linked to this misconception.",
        )
    if (
        follow_up_question.question != baseline_question.question
        or follow_up_question.correct_answer != baseline_question.correct_answer
    ):
        raise ResultsError(
            "follow_up_question_mismatch",
            "The follow-up question and expected answer must match the initial assessment for this comparison.",
        )

    baseline_students = {
        response.student_id for response in baseline.responses if response.question_id == group.question_id
    }
    follow_up_students = {
        response.student_id for response in follow_up.responses if response.question_id == group.question_id
    }
    unknown_students = sorted(follow_up_students - baseline_students)
    if unknown_students:
        raise ResultsError(
            "follow_up_student_mismatch",
            "The follow-up contains student identifiers that are not present in the initial assessment.",
            details={"unknown_student_ids": unknown_students},
        )


def _match_follow_up_group(
    baseline_group: MisconceptionGroup,
    candidates: list[MisconceptionGroup],
) -> MisconceptionGroup | None:
    baseline_members = set(baseline_group.member_student_ids)
    same_question = [candidate for candidate in candidates if candidate.question_id == baseline_group.question_id]
    ranked = sorted(
        same_question,
        key=lambda candidate: (
            len(baseline_members.intersection(candidate.member_student_ids)),
            candidate.coherence,
            candidate.support_count,
        ),
        reverse=True,
    )
    if not ranked:
        return None
    overlap = len(baseline_members.intersection(ranked[0].member_student_ids))
    return ranked[0] if overlap >= 2 else None


def _calculate_metrics(
    baseline_responses: list[NormalizedResponse],
    follow_up_responses: list[NormalizedResponse],
    baseline_group: MisconceptionGroup,
    follow_up_group: MisconceptionGroup,
    *,
    baseline_analysis_id: str,
    follow_up_analysis_id: str,
    baseline_filename: str,
    follow_up_filename: str,
    baseline_title: str,
    follow_up_title: str,
) -> ComparisonMetrics:
    question_id = baseline_group.question_id
    baseline_question = [response for response in baseline_responses if response.question_id == question_id]
    baseline_students = {response.student_id for response in baseline_question}
    follow_up_by_student = {
        response.student_id: response
        for response in follow_up_responses
        if response.question_id == question_id and response.student_id in baseline_students
    }
    baseline_answered = [response for response in baseline_question if response.answer_status == "answered"]
    follow_up_answered = [response for response in follow_up_by_student.values() if response.answer_status == "answered"]
    missing_follow_up = len(baseline_students) - len(follow_up_answered)

    baseline_members = set(baseline_group.member_student_ids)
    follow_up_members = set(follow_up_group.member_student_ids)
    resolved_correct = sum(
        response is not None and response.answer_status == "answered" and response.is_correct
        for student_id in baseline_members
        if (response := follow_up_by_student.get(student_id)) is not None
    )
    still_struggling = len(baseline_members.intersection(follow_up_members))
    changed_but_still_incorrect = sum(
        response is not None
        and response.answer_status == "answered"
        and not response.is_correct
        and student_id not in follow_up_members
        for student_id in baseline_members
        if (response := follow_up_by_student.get(student_id)) is not None
    )
    missing_from_group = len(baseline_members) - resolved_correct - still_struggling - changed_but_still_incorrect

    before_prevalence = _percent(baseline_group.support_count, len(baseline_answered))
    after_prevalence = _percent(follow_up_group.support_count, len(follow_up_answered))
    before_correct = _percent(sum(response.is_correct for response in baseline_answered), len(baseline_answered))
    after_correct = _percent(sum(response.is_correct for response in follow_up_answered), len(follow_up_answered))

    return ComparisonMetrics(
        before=AssessmentResultSnapshot(
            analysis_id=baseline_analysis_id,
            assessment_title=baseline_title,
            filename=baseline_filename,
            answered_students=len(baseline_answered),
            correct_students=sum(response.is_correct for response in baseline_answered),
            affected_students=baseline_group.support_count,
            misconception_prevalence_percent=before_prevalence,
        ),
        after=AssessmentResultSnapshot(
            analysis_id=follow_up_analysis_id,
            assessment_title=follow_up_title,
            filename=follow_up_filename,
            answered_students=len(follow_up_answered),
            correct_students=sum(response.is_correct for response in follow_up_answered),
            affected_students=follow_up_group.support_count,
            misconception_prevalence_percent=after_prevalence,
        ),
        matched_answered_students=len(follow_up_answered),
        missing_follow_up_students=missing_follow_up,
        percentage_point_reduction=round(before_prevalence - after_prevalence, 1),
        correct_percentage_point_change=round(after_correct - before_correct, 1),
        transitions=StudentTransitionMetrics(
            baseline_affected_students=len(baseline_members),
            resolved_correct=resolved_correct,
            changed_but_still_incorrect=changed_but_still_incorrect,
            still_struggling=still_struggling,
            missing_from_baseline_group=missing_from_group,
            new_affected_students=len(follow_up_members - baseline_members),
        ),
    )


def _percent(numerator: int, denominator: int) -> float:
    return round((numerator / denominator) * 100, 1) if denominator else 0.0


def _comparison_id(link: FollowUpComparisonLink, follow_up_analysis_id: str) -> str:
    payload = {
        "baseline_analysis_id": link.baseline_analysis_id,
        "follow_up_analysis_id": follow_up_analysis_id,
        "group_id": link.group_id,
        "remediation_id": link.remediation_id,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
    return f"comparison_{digest}"
