import asyncio

import httpx
import pytest

from app.main import app
from app.providers.llm import GeminiLLMService, LLMProviderError, get_llm_service
from app.providers.remediation_store import InMemoryRemediationStore, get_remediation_store
from app.schemas.analysis import RepresentativeResponse
from app.schemas.materials import (
    LearningMaterial,
    MaterialRetrievalResponse,
    RetrievalMetadata,
    RetrievedChunk,
)
from app.schemas.remediations import (
    EditableRemediationContent,
    FollowUpQuestion,
    GeneratedRemediationDraft,
    RemediationGenerationRequest,
    RemediationMisconceptionContext,
    RemediationReviewRequest,
)
from app.services.remediation import RemediationError, generate_grounded_remediation, review_remediation


class FakeLLMService:
    provider_name = "fake-gemini"
    model_id = "gemini-test"

    def __init__(self, draft: GeneratedRemediationDraft | None = None, error: Exception | None = None) -> None:
        self.draft = draft or grounded_draft()
        self.error = error
        self.prompts: list[str] = []

    async def generate_remediation(self, prompt: str) -> GeneratedRemediationDraft:
        self.prompts.append(prompt)
        if self.error:
            raise self.error
        return self.draft.model_copy(deep=True)


def grounded_draft(**overrides: object) -> GeneratedRemediationDraft:
    values: dict[str, object] = {
        "misconception_summary": "The responses treat sunlight as matter that plants consume as food.",
        "learning_objective": "Distinguish light energy from the glucose plants produce.",
        "teacher_explanation": "Sunlight supplies energy for photosynthesis; it is not food entering the plant.",
        "corrected_concept": "Plants use light energy to make glucose from carbon dioxide and water.",
        "activity": "Have students sort cards into energy inputs, matter inputs, and products, then explain the glucose card.",
        "analogy": "Light powers the process like electricity powers a kitchen appliance, while ingredients become the product.",
        "follow_up_questions": [
            {
                "prompt": "What does sunlight provide during photosynthesis?",
                "expected_answer": "Energy used to make glucose.",
            }
        ],
        "source_references": ["chunk_001"],
    }
    values.update(overrides)
    return GeneratedRemediationDraft(**values)


def generation_request(*, retrieval_status: str = "retrieved") -> RemediationGenerationRequest:
    material = LearningMaterial(
        material_id="mat_demo",
        title="Photosynthesis notes",
        filename="photosynthesis.txt",
        source_kind="synthetic_demo",
        content_hash="abc",
        chunk_count=1,
        chunk_size_chars=900,
        chunk_overlap_chars=120,
        embedding_model="test-embedding",
        embedding_dimension=2,
    )
    results = [] if retrieval_status == "insufficient_relevant_context" else [
        RetrievedChunk(
            chunk_id="chunk_001",
            chunk_index=0,
            text="Sunlight supplies energy. Plants use carbon dioxide and water to make glucose.",
            similarity=0.83,
            start_char=0,
            end_char=81,
        )
    ]
    retrieval = MaterialRetrievalResponse(
        status=retrieval_status,
        group_id="grp_demo",
        material=material,
        retrieval=RetrievalMetadata(
            algorithm="cosine_similarity_v1",
            top_k=3,
            minimum_relevance_score=0.42,
            embedding_model="test-embedding",
        ),
        results=results,
        message="No relevant material." if not results else None,
    )
    return RemediationGenerationRequest(
        analysis_id="analysis_demo",
        grade_level="7",
        subject="Science",
        topic="Photosynthesis",
        misconception=RemediationMisconceptionContext(
            group_id="grp_demo",
            provisional_label="Potential misconception pattern 1",
            question_id="Q1",
            question="Explain how plants make food during photosynthesis.",
            correct_answer="Plants use light energy to convert carbon dioxide and water into glucose and oxygen.",
            support_count=9,
            eligible_response_count=29,
            representative_responses=[
                RepresentativeResponse(student_id="S001", answer="Plants eat sunlight.", similarity_to_medoid=0.96),
                RepresentativeResponse(student_id="S005", answer="Sunlight is food for plants.", similarity_to_medoid=0.93),
            ],
        ),
        retrieval=retrieval,
    )


def test_generation_uses_group_evidence_and_exact_teacher_sources() -> None:
    fake = FakeLLMService()
    store = InMemoryRemediationStore()

    result = asyncio.run(generate_grounded_remediation(generation_request(), llm_service=fake, store=store))

    assert result.status == "generated"
    assert result.remediation is not None
    assert result.remediation.status == "generated"
    assert result.remediation.content.source_references == ["chunk_001"]
    assert result.remediation.sources[0].text == generation_request().retrieval.results[0].text
    assert "Plants eat sunlight." in fake.prompts[0]
    assert "chunk_001" in fake.prompts[0]
    assert "affected_response_count" in fake.prompts[0]
    assert store.get(result.remediation.remediation_id) is not None


def test_insufficient_context_does_not_call_llm_or_save_record() -> None:
    fake = FakeLLMService()
    store = InMemoryRemediationStore()

    result = asyncio.run(
        generate_grounded_remediation(
            generation_request(retrieval_status="insufficient_relevant_context"),
            llm_service=fake,
            store=store,
        )
    )

    assert result.status == "insufficient_context"
    assert result.remediation is None
    assert fake.prompts == []


def test_unknown_model_source_reference_is_rejected() -> None:
    fake = FakeLLMService(grounded_draft(source_references=["invented_chunk"]))

    with pytest.raises(RemediationError) as caught:
        asyncio.run(
            generate_grounded_remediation(
                generation_request(),
                llm_service=fake,
                store=InMemoryRemediationStore(),
            )
        )

    assert caught.value.code == "llm_ungrounded_output"


def test_llm_provider_failure_is_controlled_and_saves_nothing() -> None:
    fake = FakeLLMService(error=LLMProviderError("llm_timeout", "Provider timed out.", retryable=True))

    with pytest.raises(RemediationError) as caught:
        asyncio.run(
            generate_grounded_remediation(
                generation_request(),
                llm_service=fake,
                store=InMemoryRemediationStore(),
            )
        )

    assert caught.value.code == "llm_timeout"
    assert caught.value.retryable is True


def test_teacher_can_edit_then_approve_and_original_generation_is_preserved() -> None:
    store = InMemoryRemediationStore()
    generated = asyncio.run(generate_grounded_remediation(generation_request(), llm_service=FakeLLMService(), store=store))
    assert generated.remediation is not None
    original_activity = generated.remediation.generated_content.activity
    edited = EditableRemediationContent(
        **generated.remediation.content.model_dump(exclude={"source_references"})
    )
    edited.activity = "Teacher-edited card sort followed by a short written explanation."

    approved = review_remediation(
        generated.remediation.remediation_id,
        RemediationReviewRequest(action="approve", edited_content=edited, review_notes="Aligned to our lesson."),
        store=store,
    )

    assert approved.status == "approved"
    assert approved.content.activity.startswith("Teacher-edited")
    assert approved.generated_content.activity == original_activity
    assert approved.content.source_references == ["chunk_001"]
    with pytest.raises(RemediationError) as caught:
        review_remediation(
            approved.remediation_id,
            RemediationReviewRequest(action="reject"),
            store=store,
        )
    assert caught.value.code == "remediation_invalid_transition"


def test_teacher_can_reject_generated_remediation() -> None:
    store = InMemoryRemediationStore()
    generated = asyncio.run(generate_grounded_remediation(generation_request(), llm_service=FakeLLMService(), store=store))
    assert generated.remediation is not None

    rejected = review_remediation(
        generated.remediation.remediation_id,
        RemediationReviewRequest(action="reject", review_notes="This does not fit the class sequence."),
        store=store,
    )

    assert rejected.status == "rejected"
    assert rejected.review_notes == "This does not fit the class sequence."


def test_typed_api_generation_get_edit_and_reject_flow() -> None:
    fake = FakeLLMService()
    store = InMemoryRemediationStore()

    async def override_llm() -> FakeLLMService:
        return fake

    async def override_store() -> InMemoryRemediationStore:
        return store

    app.dependency_overrides[get_llm_service] = override_llm
    app.dependency_overrides[get_remediation_store] = override_store

    async def send() -> tuple[httpx.Response, httpx.Response, httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post("/api/v1/remediations", json=generation_request().model_dump())
            remediation_id = created.json()["remediation"]["remediation_id"]
            fetched = await client.get(f"/api/v1/remediations/{remediation_id}")
            rejected = await client.patch(
                f"/api/v1/remediations/{remediation_id}",
                json={"action": "reject", "review_notes": "Use a different activity."},
            )
            return created, fetched, rejected

    try:
        created, fetched, rejected = asyncio.run(send())
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 200
    assert created.json()["status"] == "generated"
    assert fetched.status_code == 200
    assert fetched.json()["generated_content"] == fetched.json()["content"]
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"


def test_api_returns_controlled_provider_error_without_fabricated_remediation() -> None:
    fake = FakeLLMService(error=LLMProviderError("llm_provider_unavailable", "Provider unavailable.", retryable=True))

    async def override_llm() -> FakeLLMService:
        return fake

    async def override_store() -> InMemoryRemediationStore:
        return InMemoryRemediationStore()

    app.dependency_overrides[get_llm_service] = override_llm
    app.dependency_overrides[get_remediation_store] = override_store

    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/api/v1/remediations", json=generation_request().model_dump())

    try:
        response = asyncio.run(send())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "llm_provider_unavailable"
    assert "remediation" not in response.json()


@pytest.mark.parametrize(
    ("api_key", "provider_result", "expected_code"),
    [
        ("", None, "llm_not_configured"),
        ("test-key", "malformed", "llm_malformed_output"),
        ("test-key", "timeout", "llm_timeout"),
    ],
)
def test_gemini_adapter_fails_safely(api_key: str, provider_result: str | None, expected_code: str) -> None:
    service = GeminiLLMService(api_key=api_key, model_id="gemini-test", timeout_ms=5_000)

    if api_key:
        class FakeTypes:
            @staticmethod
            def GenerateContentConfig(**kwargs):
                return kwargs

        class FakeModels:
            async def generate_content(self, **_kwargs):
                if provider_result == "timeout":
                    raise TimeoutError("secret timeout detail")
                return type("Response", (), {"parsed": None, "text": "not-json"})()

        service._types = FakeTypes()
        service._client = type("Client", (), {"aio": type("Async", (), {"models": FakeModels()})()})()

    with pytest.raises(LLMProviderError) as caught:
        asyncio.run(service.generate_remediation("grounded prompt"))

    assert caught.value.code == expected_code
    assert "secret timeout detail" not in caught.value.message
