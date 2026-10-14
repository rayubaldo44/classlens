import hashlib
from datetime import UTC, datetime
from threading import Lock, RLock
from typing import Any

from app.database import DatabaseError
from app.providers.analysis_store import AnalysisStore
from app.providers.group_review_store import GroupReviewStore
from app.providers.remediation_store import RemediationStore
from app.schemas.analysis import MisconceptionGroup
from app.schemas.group_reviews import (
    GroupReviewActionRequest,
    GroupReviewEvent,
    GroupReviewResponse,
    GroupReviewState,
    ReviewedMisconceptionGroup,
)


class GroupReviewError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 409, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


_locks_guard = Lock()
_analysis_locks: dict[str, RLock] = {}


def _lock_for(analysis_id: str) -> RLock:
    with _locks_guard:
        return _analysis_locks.setdefault(analysis_id, RLock())


def _from_detected(group: MisconceptionGroup) -> ReviewedMisconceptionGroup:
    return ReviewedMisconceptionGroup(
        reviewed_group_id=group.group_id,
        display_label=group.provisional_label,
        status="active",
        source_group_ids=[group.group_id],
        question_id=group.question_id,
        question=group.question,
        correct_answer=group.correct_answer,
        support_count=group.support_count,
        eligible_response_count=group.eligible_response_count,
        member_student_ids=list(group.member_student_ids),
        representative_responses=[item.model_copy(deep=True) for item in group.representative_responses],
        coherence=group.coherence,
    )


def _initial_state(analysis_id: str, analysis_store: AnalysisStore) -> GroupReviewState:
    snapshot = analysis_store.get(analysis_id)
    if snapshot is None:
        raise GroupReviewError(
            "analysis_not_found", "The requested analysis was not found.", status_code=404,
            details={"analysis_id": analysis_id},
        )
    return GroupReviewState(
        analysis_id=analysis_id,
        revision=0,
        groups=[_from_detected(group) for group in snapshot.result.groups],
    )


def _response(state: GroupReviewState, events: list[GroupReviewEvent]) -> GroupReviewResponse:
    return GroupReviewResponse(
        analysis_id=state.analysis_id,
        revision=state.revision,
        active_groups=[group for group in state.groups if group.status == "active"],
        dismissed_groups=[group for group in state.groups if group.status == "dismissed"],
        events=sorted(events, key=lambda event: event.sequence),
    )


def get_group_reviews(
    analysis_id: str,
    analysis_store: AnalysisStore,
    review_store: GroupReviewStore,
) -> GroupReviewResponse:
    initial = _initial_state(analysis_id, analysis_store)
    stored = review_store.get(analysis_id)
    return _response(stored.state, stored.events) if stored else _response(initial, [])


def _validate_shape(request: GroupReviewActionRequest) -> None:
    count = len(request.group_ids)
    if request.action == "merge":
        if count < 2:
            raise GroupReviewError("group_review_invalid_action", "Merge requires at least two groups.")
    elif count != 1:
        raise GroupReviewError("group_review_invalid_action", f"{request.action.title()} requires exactly one group.")
    if request.action in {"rename", "merge"}:
        if request.label is None or not 1 <= len(request.label) <= 120:
            raise GroupReviewError(
                "group_review_invalid_label", "Rename and merge require a label between 1 and 120 characters."
            )
    elif request.label is not None:
        raise GroupReviewError("group_review_invalid_label", "Dismiss and restore do not accept a label.")


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "|".join(str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(payload.encode()).hexdigest()[:16]}"


def apply_group_review(
    analysis_id: str,
    request: GroupReviewActionRequest,
    analysis_store: AnalysisStore,
    review_store: GroupReviewStore,
    remediation_store: RemediationStore | None,
) -> GroupReviewResponse:
    del remediation_store  # Downstream locking is added with remediation provenance in Task 4.
    _validate_shape(request)
    with _lock_for(analysis_id):
        initial = _initial_state(analysis_id, analysis_store)
        stored = review_store.get(analysis_id)
        previous = stored.state if stored else initial
        events = stored.events if stored else []
        groups_by_id = {group.reviewed_group_id: group for group in previous.groups}
        selected: list[ReviewedMisconceptionGroup] = []
        for group_id in request.group_ids:
            group = groups_by_id.get(group_id)
            if group is None:
                raise GroupReviewError(
                    "group_review_stale_group", "A selected group is unknown or no longer active.",
                    details={"group_id": group_id},
                )
            selected.append(group)

        if request.action == "restore":
            if selected[0].status != "dismissed":
                raise GroupReviewError("group_review_not_dismissed", "Only a dismissed group can be restored.")
        elif any(group.status != "active" for group in selected):
            raise GroupReviewError("group_review_inactive", "Only active groups can be reviewed.")

        sequence = len(events) + 1
        source_ids = sorted({source for group in selected for source in group.source_group_ids})
        next_groups = [group.model_copy(deep=True) for group in previous.groups]
        if request.action == "rename":
            target = next(group for group in next_groups if group.reviewed_group_id == selected[0].reviewed_group_id)
            target.display_label = request.label or target.display_label
            resulting_id = target.reviewed_group_id
        elif request.action in {"dismiss", "restore"}:
            target = next(group for group in next_groups if group.reviewed_group_id == selected[0].reviewed_group_id)
            target.status = "dismissed" if request.action == "dismiss" else "active"
            resulting_id = target.reviewed_group_id
        else:
            question_ids = {group.question_id for group in selected}
            if len(question_ids) != 1:
                raise GroupReviewError(
                    "group_review_cross_question", "Groups can only be merged within the same question."
                )
            selected_ids = {group.reviewed_group_id for group in selected}
            next_groups = [group for group in next_groups if group.reviewed_group_id not in selected_ids]
            resulting_id = _stable_id("rgrp", analysis_id, "merge", ",".join(source_ids), sequence)
            representative_by_student = {
                item.student_id: item.model_copy(deep=True)
                for group in selected for item in group.representative_responses
            }
            member_ids = sorted({student for group in selected for student in group.member_student_ids})
            first = selected[0]
            next_groups.append(ReviewedMisconceptionGroup(
                reviewed_group_id=resulting_id,
                display_label=request.label or "Merged misconception",
                status="active",
                source_group_ids=source_ids,
                question_id=first.question_id,
                question=first.question,
                correct_answer=first.correct_answer,
                support_count=len(member_ids),
                eligible_response_count=first.eligible_response_count,
                member_student_ids=member_ids,
                representative_responses=list(representative_by_student.values()),
                coherence=None,
            ))

        next_state = GroupReviewState(
            analysis_id=analysis_id, revision=previous.revision + 1, groups=next_groups
        )
        event = GroupReviewEvent(
            event_id=_stable_id("grev", analysis_id, request.action, ",".join(source_ids), sequence),
            analysis_id=analysis_id,
            sequence=sequence,
            action=request.action,
            source_group_ids=source_ids,
            resulting_reviewed_group_id=resulting_id,
            previous_state=previous if previous.revision else None,
            next_state=next_state,
            review_note=request.review_note,
            created_at=datetime.now(UTC),
        )
        expected_stored_state = stored.state if stored else None
        try:
            review_store.save(analysis_id, expected_stored_state, next_state, event)
        except (ValueError, DatabaseError) as error:
            if isinstance(error, DatabaseError) and error.code != "group_review_stale":
                raise
            raise GroupReviewError(
                "group_review_stale", "The group review changed before this action could be saved."
            ) from error
        return _response(next_state, [*events, event])


def resolve_reviewed_group(
    analysis_id: str,
    reviewed_group_id: str,
    analysis_store: AnalysisStore,
    review_store: GroupReviewStore,
) -> ReviewedMisconceptionGroup:
    response = get_group_reviews(analysis_id, analysis_store, review_store)
    group = next(
        (item for item in response.active_groups if item.reviewed_group_id == reviewed_group_id),
        None,
    )
    if group is None:
        raise GroupReviewError(
            "reviewed_group_not_available",
            "The selected group is dismissed, stale, or does not belong to this analysis.",
            details={"reviewed_group_id": reviewed_group_id},
        )
    return group
