from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import httpx
from pydantic import ValidationError
from conftest import run_test_async

from app.providers.group_review_store import InMemoryGroupReviewStore
from app.providers.group_review_store import get_group_review_store
from app.providers.analysis_store import InMemoryAnalysisStore, get_analysis_store
from app.providers.remediation_store import InMemoryRemediationStore, get_remediation_store
from app.main import app
from app.services.assessment_intake import parse_assessment_csv_full
from app.services.group_reviews import (
    GroupReviewError,
    apply_group_review,
    get_group_reviews,
    resolve_reviewed_group,
)
from app.services.misconception_analysis import analyze_assessment
from app.config import AnalysisSettings
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


class ReviewEmbeddings:
    model_id = "test/reviews"

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = {
            "light one": [1.0, 0.0, 0.0], "light two": [0.99, 0.01, 0.0],
            "soil one": [0.0, 1.0, 0.0], "soil two": [0.0, 0.99, 0.01],
            "root one": [0.0, 0.0, 1.0], "root two": [0.01, 0.0, 0.99],
        }
        return [vectors[text] for text in texts]


def _analysis_store() -> tuple[InMemoryAnalysisStore, str]:
    header = (
        "assessment_title,subject,grade_level,topic,student_id,question_id,question,answer,"
        "correct_answer,is_correct\n"
    )
    rows = [
        'Review,Science,7,Plants,S1,Q1,"How food?","light one","Glucose",false\n',
        'Review,Science,7,Plants,S2,Q1,"How food?","light two","Glucose",false\n',
        'Review,Science,7,Plants,S3,Q1,"How food?","soil one","Glucose",false\n',
        'Review,Science,7,Plants,S4,Q1,"How food?","soil two","Glucose",false\n',
        'Review,Science,7,Plants,S5,Q2,"What enters roots?","root one","Water",false\n',
        'Review,Science,7,Plants,S6,Q2,"What enters roots?","root two","Water",false\n',
    ]
    parsed = parse_assessment_csv_full(
        (header + "".join(rows)).encode(), filename="review.csv", data_label="teacher_upload"
    )
    result = analyze_assessment(
        parsed, ReviewEmbeddings(),
        AnalysisSettings(embedding_model=ReviewEmbeddings.model_id, similarity_threshold=0.8, min_group_size=2),
    )
    assert len(result.groups) == 3
    store = InMemoryAnalysisStore()
    store.save(parsed, result)
    return store, result.analysis_id


def test_initial_overlay_preserves_detected_groups_without_persisting_state() -> None:
    analysis_store, analysis_id = _analysis_store()
    review_store = InMemoryGroupReviewStore()

    response = get_group_reviews(analysis_id, analysis_store, review_store)

    assert response.revision == 0
    assert len(response.active_groups) == 3
    assert response.dismissed_groups == []
    assert response.events == []
    assert review_store.get(analysis_id) is None
    for group in response.active_groups:
        assert group.reviewed_group_id == group.source_group_ids[0]
        assert group.coherence is not None


def test_rename_dismiss_restore_and_history_are_deterministic() -> None:
    analysis_store, analysis_id = _analysis_store()
    review_store = InMemoryGroupReviewStore()
    original = get_group_reviews(analysis_id, analysis_store, review_store).active_groups[0]

    renamed = apply_group_review(
        analysis_id,
        GroupReviewActionRequest(action="rename", group_ids=[original.reviewed_group_id], label="  Energy confusion  "),
        analysis_store, review_store, None,
    )
    assert renamed.active_groups[0].display_label == "Energy confusion"
    dismissed = apply_group_review(
        analysis_id,
        GroupReviewActionRequest(action="dismiss", group_ids=[original.reviewed_group_id], review_note="Duplicate"),
        analysis_store, review_store, None,
    )
    assert [group.reviewed_group_id for group in dismissed.dismissed_groups] == [original.reviewed_group_id]
    restored = apply_group_review(
        analysis_id,
        GroupReviewActionRequest(action="restore", group_ids=[original.reviewed_group_id]),
        analysis_store, review_store, None,
    )
    assert len(restored.active_groups) == 3
    assert [event.action for event in restored.events] == ["rename", "dismiss", "restore"]
    assert [event.sequence for event in restored.events] == [1, 2, 3]


def test_merge_unions_exact_evidence_and_uses_label_independent_id() -> None:
    analysis_store, analysis_id = _analysis_store()
    initial = get_group_reviews(analysis_id, analysis_store, InMemoryGroupReviewStore())
    q1_groups = [group for group in initial.active_groups if group.question_id == "Q1"]

    def merge(label: str):
        store = InMemoryGroupReviewStore()
        response = apply_group_review(
            analysis_id,
            GroupReviewActionRequest(
                action="merge", group_ids=[group.reviewed_group_id for group in reversed(q1_groups)], label=label
            ),
            analysis_store, store, None,
        )
        return response, store

    first, first_store = merge("Combined misconception")
    second, _ = merge("Different teacher wording")
    merged = next(group for group in first.active_groups if len(group.source_group_ids) == 2)
    merged_again = next(group for group in second.active_groups if len(group.source_group_ids) == 2)
    expected_members = sorted({student for group in q1_groups for student in group.member_student_ids})
    expected_answers = {item.answer for group in q1_groups for item in group.representative_responses}

    assert merged.reviewed_group_id == merged_again.reviewed_group_id
    assert merged.source_group_ids == sorted(group.reviewed_group_id for group in q1_groups)
    assert merged.member_student_ids == expected_members
    assert {item.answer for item in merged.representative_responses} == expected_answers
    assert merged.support_count == len(expected_members)
    assert merged.coherence is None
    assert resolve_reviewed_group(analysis_id, merged.reviewed_group_id, analysis_store, first_store) == merged


@pytest.mark.parametrize("case", ["unknown", "cross_question", "already_dismissed", "already_merged"])
def test_invalid_or_stale_actions_leave_state_and_history_unchanged(case: str) -> None:
    analysis_store, analysis_id = _analysis_store()
    review_store = InMemoryGroupReviewStore()
    initial = get_group_reviews(analysis_id, analysis_store, review_store)
    q1 = [group for group in initial.active_groups if group.question_id == "Q1"]
    q2 = next(group for group in initial.active_groups if group.question_id == "Q2")

    if case == "unknown":
        request = GroupReviewActionRequest(action="rename", group_ids=["grp_unknown"], label="No")
    elif case == "cross_question":
        request = GroupReviewActionRequest(
            action="merge", group_ids=[q1[0].reviewed_group_id, q2.reviewed_group_id], label="No"
        )
    elif case == "already_dismissed":
        apply_group_review(
            analysis_id, GroupReviewActionRequest(action="dismiss", group_ids=[q1[0].reviewed_group_id]),
            analysis_store, review_store, None,
        )
        request = GroupReviewActionRequest(action="dismiss", group_ids=[q1[0].reviewed_group_id])
    else:
        merged = apply_group_review(
            analysis_id,
            GroupReviewActionRequest(
                action="merge", group_ids=[group.reviewed_group_id for group in q1], label="Merged"
            ),
            analysis_store, review_store, None,
        )
        request = GroupReviewActionRequest(action="rename", group_ids=[q1[0].reviewed_group_id], label="Stale")
        assert len(merged.events) == 1

    before = review_store.get(analysis_id)
    with pytest.raises(GroupReviewError):
        apply_group_review(analysis_id, request, analysis_store, review_store, None)
    assert review_store.get(analysis_id) == before


def test_action_shape_validation_happens_before_write() -> None:
    analysis_store, analysis_id = _analysis_store()
    review_store = InMemoryGroupReviewStore()
    group_id = get_group_reviews(analysis_id, analysis_store, review_store).active_groups[0].reviewed_group_id

    for request in (
        GroupReviewActionRequest(action="rename", group_ids=[group_id]),
        GroupReviewActionRequest(action="dismiss", group_ids=[group_id], label="Not allowed"),
    ):
        with pytest.raises(GroupReviewError):
            apply_group_review(analysis_id, request, analysis_store, review_store, None)
    assert review_store.get(analysis_id) is None


def _api_request(analysis_store, review_store, method: str, path: str, json=None) -> httpx.Response:
    async def override_analysis_store():
        return analysis_store

    async def override_review_store():
        return review_store

    async def override_remediation_store():
        return InMemoryRemediationStore()

    app.dependency_overrides[get_analysis_store] = override_analysis_store
    app.dependency_overrides[get_group_review_store] = override_review_store
    app.dependency_overrides[get_remediation_store] = override_remediation_store

    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, json=json)

    try:
        return run_test_async(send())
    finally:
        app.dependency_overrides.clear()


def test_group_review_api_supports_all_actions_and_ordered_history() -> None:
    analysis_store, analysis_id = _analysis_store()
    review_store = InMemoryGroupReviewStore()
    path = f"/api/v1/assessments/analyses/{analysis_id}/group-reviews"

    initial = _api_request(analysis_store, review_store, "GET", path)
    assert initial.status_code == 200
    q1 = [group for group in initial.json()["active_groups"] if group["question_id"] == "Q1"]

    renamed = _api_request(analysis_store, review_store, "POST", path, {
        "action": "rename", "group_ids": [q1[0]["reviewed_group_id"]], "label": "Teacher label"
    })
    assert renamed.status_code == 200
    dismissed = _api_request(analysis_store, review_store, "POST", path, {
        "action": "dismiss", "group_ids": [q1[0]["reviewed_group_id"]], "review_note": "Duplicate"
    })
    assert dismissed.status_code == 200
    restored = _api_request(analysis_store, review_store, "POST", path, {
        "action": "restore", "group_ids": [q1[0]["reviewed_group_id"]]
    })
    assert restored.status_code == 200
    merged = _api_request(analysis_store, review_store, "POST", path, {
        "action": "merge", "group_ids": [group["reviewed_group_id"] for group in q1], "label": "Combined"
    })
    assert merged.status_code == 200
    assert [event["action"] for event in merged.json()["events"]] == ["rename", "dismiss", "restore", "merge"]


def test_group_review_api_returns_structured_not_found_conflict_and_validation_errors() -> None:
    analysis_store, analysis_id = _analysis_store()
    review_store = InMemoryGroupReviewStore()
    missing = _api_request(
        analysis_store, review_store, "GET", "/api/v1/assessments/analyses/missing/group-reviews"
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "analysis_not_found"

    path = f"/api/v1/assessments/analyses/{analysis_id}/group-reviews"
    unknown = _api_request(analysis_store, review_store, "POST", path, {
        "action": "rename", "group_ids": ["grp_missing"], "label": "No"
    })
    assert unknown.status_code == 409
    assert unknown.json()["error"]["code"] == "group_review_stale_group"
    assert unknown.json()["error"]["retryable"] is False
    assert unknown.json()["error"]["request_id"].startswith("req_")

    invalid = _api_request(analysis_store, review_store, "POST", path, {
        "action": "merge", "group_ids": []
    })
    assert invalid.status_code == 422
    assert invalid.json()["detail"]


def test_group_review_api_maps_stale_store_conflict_without_recording_history() -> None:
    analysis_store, analysis_id = _analysis_store()

    class StaleStore(InMemoryGroupReviewStore):
        def save(self, *args, **kwargs):
            raise ValueError("stale")

    store = StaleStore()
    initial = get_group_reviews(analysis_id, analysis_store, store)
    group_id = initial.active_groups[0].reviewed_group_id
    response = _api_request(
        analysis_store, store, "POST",
        f"/api/v1/assessments/analyses/{analysis_id}/group-reviews",
        {"action": "rename", "group_ids": [group_id], "label": "Teacher label"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "group_review_stale"
    assert store.get(analysis_id) is None
