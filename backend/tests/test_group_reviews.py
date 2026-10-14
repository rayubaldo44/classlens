from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.providers.group_review_store import InMemoryGroupReviewStore
from app.schemas.group_reviews import (
    GroupReviewActionRequest,
    GroupReviewEvent,
    GroupReviewState,
    ReviewedMisconceptionGroup,
)


def _group(group_id: str = "grp_reviewed") -> ReviewedMisconceptionGroup:
    return ReviewedMisconceptionGroup(
        reviewed_group_id=group_id,
        display_label="Light is food",
        status="active",
        source_group_ids=["grp_source"],
        question_id="Q1",
        question="How do plants make food?",
        correct_answer="Plants use light energy to make glucose.",
        support_count=3,
        eligible_response_count=7,
        member_student_ids=["S1", "S2", "S3"],
        representative_responses=[
            {"student_id": "S1", "answer": "Sunlight is food.", "similarity_to_medoid": 0.9}
        ],
        coherence=0.84,
    )


def _state(revision: int = 1) -> GroupReviewState:
    return GroupReviewState(analysis_id="analysis_1", revision=revision, groups=[_group()])


def _event(sequence: int, state: GroupReviewState) -> GroupReviewEvent:
    return GroupReviewEvent(
        event_id=f"grev_{sequence}",
        analysis_id=state.analysis_id,
        sequence=sequence,
        action="rename",
        source_group_ids=["grp_source"],
        resulting_reviewed_group_id="grp_reviewed",
        previous_state=None if sequence == 1 else _state(sequence - 1),
        next_state=state,
        review_note=None,
        created_at=datetime(2026, 10, 14, tzinfo=UTC) + timedelta(seconds=sequence),
    )


def test_action_request_normalizes_optional_text_and_defaults() -> None:
    request = GroupReviewActionRequest(action="dismiss", group_ids=["grp_source"], review_note="  duplicate  ")

    assert request.label is None
    assert request.review_note == "duplicate"


def test_action_request_rejects_duplicate_group_ids() -> None:
    with pytest.raises(ValidationError):
        GroupReviewActionRequest(action="merge", group_ids=["grp_one", "grp_one"], label="Merged")


def test_in_memory_store_returns_immutable_copies_and_ordered_history() -> None:
    store = InMemoryGroupReviewStore()
    first_state = _state(1)
    second_state = _state(2)
    first_event = _event(1, first_state)
    second_event = _event(2, second_state)

    store.save("analysis_1", None, first_state, first_event)
    store.save("analysis_1", first_state, second_state, second_event)

    stored = store.get("analysis_1")
    assert stored is not None
    assert stored.state.revision == 2
    assert [event.sequence for event in stored.events] == [1, 2]

    stored.state.groups[0].display_label = "mutated"
    stored.events[0].next_state.groups[0].display_label = "also mutated"
    reloaded = store.get("analysis_1")
    assert reloaded is not None
    assert reloaded.state.groups[0].display_label == "Light is food"
    assert reloaded.events[0].next_state.groups[0].display_label == "Light is food"


def test_in_memory_store_rejects_stale_state_without_recording_event() -> None:
    store = InMemoryGroupReviewStore()
    first_state = _state(1)
    store.save("analysis_1", None, first_state, _event(1, first_state))

    with pytest.raises(ValueError, match="stale"):
        store.save("analysis_1", None, _state(2), _event(2, _state(2)))

    stored = store.get("analysis_1")
    assert stored is not None
    assert stored.state.revision == 1
    assert len(stored.events) == 1


def test_additive_migration_defines_review_state_and_append_only_history() -> None:
    migration = (
        Path(__file__).resolve().parents[2] / "database" / "migrations" / "002_teacher_group_reviews.sql"
    ).read_text()

    for table in ("analysis_group_review_states", "analysis_group_review_events"):
        assert f"create table if not exists {table}" in migration
        assert f"alter table {table} enable row level security" in migration
    assert "references analysis_runs(id) on delete restrict" in migration
    assert "action in ('rename', 'merge', 'dismiss', 'restore')" in migration
