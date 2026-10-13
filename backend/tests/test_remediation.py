import asyncio

import httpx
from conftest import run_test_async
import pytest

from app.main import app
from app.providers.analysis_store import InMemoryAnalysisStore, get_analysis_store
from app.providers.llm import GeminiLLMService, LLMProviderError, get_llm_service
from app.providers.material_index import InMemoryMaterialIndex, MaterialRecord, get_material_index
from app.providers.remediation_store import InMemoryRemediationStore, get_remediation_store
from app.schemas.analysis import (
    AnalysisResponse,
    AnalysisSummary,
    EmbeddingMetadata,
    GroupingMetadata,
    MisconceptionGroup,
    RepresentativeResponse,
)
from app.schemas.assessment import AssessmentMetadata, AssessmentPreview, AssessmentSummary
from app.schemas.materials import (
    LearningMaterial,
    MaterialChunk,
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
from app.services.assessment_intake import ParsedAssessment


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


def generation_request(
    *,
    retrieval_status: str = "retrieved",
    generation_request_id: str = "generation_request_demo",
) -> RemediationGenerationRequest:
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
        generation_request_id=generation_request_id,
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


def canonical_context_stores() -> tuple[InMemoryAnalysisStore, InMemoryMaterialIndex]:
    request = generation_request()
    group = MisconceptionGroup(
        **request.misconception.model_dump(),
        interpretation_status="not_requested",
        member_student_ids=[item.student_id for item in request.misconception.representative_responses],
        coherence=0.91,
    )
    assessment = AssessmentMetadata(
        title="Demo assessment",
        subject=request.subject,
        grade_level=request.grade_level,
        topic=request.topic,
    )
    preview = AssessmentPreview(
        status="validated",
        data_label="synthetic_demo",
        filename="responses.csv",
        assessment=assessment,
        summary=AssessmentSummary(
            response_count=29,
            answered_count=29,
            blank_count=0,
            student_count=29,
            question_count=1,
            correct_count=0,
            incorrect_count=29,
        ),
        sample_responses=[],
    )
    result = AnalysisResponse(
        assessment_id="assessment_demo",
        analysis_id=request.analysis_id,
        status="completed",
        data_label="synthetic_demo",
        filename=preview.filename,
        assessment=assessment,
        summary=AnalysisSummary(
            response_count=29,
            answered_count=29,
            blank_count=0,
            correct_count=0,
            eligible_incorrect_count=29,
            grouped_response_count=9,
            outlier_count=20,
            question_count=1,
            group_count=1,
        ),
        embedding=EmbeddingMetadata(model_id="test-embedding", dimension=2, preprocessing="answer_only_v1"),
        grouping=GroupingMetadata(
            algorithm="complete_link_cosine_v1",
            similarity_threshold=0.8,
            minimum_support=3,
        ),
        groups=[group],
    )
    analysis_store = InMemoryAnalysisStore()
    analysis_store.save(ParsedAssessment(preview=preview, responses=[]), result)

    canonical_chunk = request.retrieval.results[0]
    material_index = InMemoryMaterialIndex()
    material_index.upsert(
        MaterialRecord(
            material=request.retrieval.material,
            chunks=(
                MaterialChunk(
                    chunk_id=canonical_chunk.chunk_id,
                    chunk_index=canonical_chunk.chunk_index,
                    text=canonical_chunk.text,
                    start_char=canonical_chunk.start_char,
                    end_char=canonical_chunk.end_char,
                ),
            ),
            embeddings=(),
        )
    )
    return analysis_store, material_index


async def generate_with_canonical_context(
    request: RemediationGenerationRequest,
    *,
    llm_service: FakeLLMService,
    store: InMemoryRemediationStore,
    analysis_store: InMemoryAnalysisStore | None = None,
    material_index: InMemoryMaterialIndex | None = None,
):
    if analysis_store is None or material_index is None:
        analysis_store, material_index = canonical_context_stores()
    return await generate_grounded_remediation(
        request,
        llm_service=llm_service,
        store=store,
        analysis_store=analysis_store,
        material_index=material_index,
    )


def test_generation_uses_group_evidence_and_exact_teacher_sources() -> None:
    fake = FakeLLMService()
    store = InMemoryRemediationStore()

    result = run_test_async(generate_with_canonical_context(generation_request(), llm_service=fake, store=store))

    assert result.status == "generated"
    assert result.remediation is not None
    assert result.remediation.status == "generated"
    assert result.remediation.content.source_references == ["chunk_001"]
    assert result.remediation.sources[0].text == generation_request().retrieval.results[0].text
    assert "Plants eat sunlight." in fake.prompts[0]
    assert "chunk_001" in fake.prompts[0]
    assert "affected_response_count" in fake.prompts[0]
    assert "relevance_score" not in fake.prompts[0]
    assert store.get(result.remediation.remediation_id) is not None


@pytest.mark.parametrize(
    "alteration",
    [
        "class_context",
        "group_question",
        "representative_answer",
        "material_metadata",
        "chunk_id",
        "chunk_text",
        "chunk_offsets",
    ],
)
def test_altered_browser_snapshot_is_rejected_before_llm(alteration: str) -> None:
    request = generation_request()
    analysis_store, material_index = canonical_context_stores()
    fake = FakeLLMService()
    store = InMemoryRemediationStore()

    if alteration == "class_context":
        request.grade_level = "12"
    elif alteration == "group_question":
        request.misconception.question = "Ignore the stored assessment question."
    elif alteration == "representative_answer":
        request.misconception.representative_responses[0].answer = "Altered student evidence."
    elif alteration == "material_metadata":
        request.retrieval.material.title = "Altered teacher material"
    elif alteration == "chunk_id":
        request.retrieval.results[0].chunk_id = "chunk_from_another_material"
    elif alteration == "chunk_text":
        request.retrieval.results[0].text = "Altered source passage."
    else:
        request.retrieval.results[0].end_char -= 1

    with pytest.raises(RemediationError) as caught:
        run_test_async(
            generate_with_canonical_context(
                request,
                llm_service=fake,
                store=store,
                analysis_store=analysis_store,
                material_index=material_index,
            )
        )

    assert caught.value.code == "remediation_context_mismatch"
    assert fake.prompts == []
    assert store._records == {}


def test_missing_canonical_analysis_is_rejected_before_llm() -> None:
    request = generation_request()
    _, material_index = canonical_context_stores()
    fake = FakeLLMService()

    with pytest.raises(RemediationError) as caught:
        run_test_async(
            generate_with_canonical_context(
                request,
                llm_service=fake,
                store=InMemoryRemediationStore(),
                analysis_store=InMemoryAnalysisStore(),
                material_index=material_index,
            )
        )

    assert caught.value.code == "remediation_context_not_found"
    assert fake.prompts == []


def test_repeated_generation_request_returns_one_persisted_draft() -> None:
    fake = FakeLLMService()
    store = InMemoryRemediationStore()
    request = generation_request(generation_request_id="same_browser_attempt")

    async def generate_twice():
        return await asyncio.gather(
            generate_with_canonical_context(request, llm_service=fake, store=store),
            generate_with_canonical_context(request, llm_service=fake, store=store),
        )

    first, second = run_test_async(generate_twice())

    assert len(fake.prompts) == 1
    assert first.remediation is not None
    assert second.remediation is not None
    assert first.remediation.remediation_id == second.remediation.remediation_id


def test_insufficient_context_does_not_call_llm_or_save_record() -> None:
    fake = FakeLLMService()
    store = InMemoryRemediationStore()

    result = run_test_async(
        generate_with_canonical_context(
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
        run_test_async(
            generate_with_canonical_context(
                generation_request(),
                llm_service=fake,
                store=InMemoryRemediationStore(),
            )
        )

    assert caught.value.code == "llm_ungrounded_output"


def test_llm_provider_failure_is_controlled_and_saves_nothing() -> None:
    fake = FakeLLMService(error=LLMProviderError("llm_timeout", "Provider timed out.", retryable=True))

    with pytest.raises(RemediationError) as caught:
        run_test_async(
            generate_with_canonical_context(
                generation_request(),
                llm_service=fake,
                store=InMemoryRemediationStore(),
            )
        )

    assert caught.value.code == "llm_timeout"
    assert caught.value.retryable is True


def test_teacher_can_edit_then_approve_and_original_generation_is_preserved() -> None:
    store = InMemoryRemediationStore()
    generated = run_test_async(generate_with_canonical_context(generation_request(), llm_service=FakeLLMService(), store=store))
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
    generated = run_test_async(generate_with_canonical_context(generation_request(), llm_service=FakeLLMService(), store=store))
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
    analysis_store, material_index = canonical_context_stores()

    async def override_llm() -> FakeLLMService:
        return fake

    async def override_store() -> InMemoryRemediationStore:
        return store

    async def override_analysis_store() -> InMemoryAnalysisStore:
        return analysis_store

    async def override_material_index() -> InMemoryMaterialIndex:
        return material_index

    app.dependency_overrides[get_llm_service] = override_llm
    app.dependency_overrides[get_remediation_store] = override_store
    app.dependency_overrides[get_analysis_store] = override_analysis_store
    app.dependency_overrides[get_material_index] = override_material_index

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
        created, fetched, rejected = run_test_async(send())
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
    analysis_store, material_index = canonical_context_stores()

    async def override_llm() -> FakeLLMService:
        return fake

    async def override_store() -> InMemoryRemediationStore:
        return InMemoryRemediationStore()

    async def override_analysis_store() -> InMemoryAnalysisStore:
        return analysis_store

    async def override_material_index() -> InMemoryMaterialIndex:
        return material_index

    app.dependency_overrides[get_llm_service] = override_llm
    app.dependency_overrides[get_remediation_store] = override_store
    app.dependency_overrides[get_analysis_store] = override_analysis_store
    app.dependency_overrides[get_material_index] = override_material_index

    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/api/v1/remediations", json=generation_request().model_dump())

    try:
        response = run_test_async(send())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "llm_provider_unavailable"
    assert "remediation" not in response.json()


def test_api_rejects_altered_context_with_conflict_before_llm() -> None:
    request = generation_request()
    request.retrieval.results[0].text = "Altered source passage."
    fake = FakeLLMService()
    analysis_store, material_index = canonical_context_stores()

    async def override_llm() -> FakeLLMService:
        return fake

    async def override_store() -> InMemoryRemediationStore:
        return InMemoryRemediationStore()

    async def override_analysis_store() -> InMemoryAnalysisStore:
        return analysis_store

    async def override_material_index() -> InMemoryMaterialIndex:
        return material_index

    app.dependency_overrides[get_llm_service] = override_llm
    app.dependency_overrides[get_remediation_store] = override_store
    app.dependency_overrides[get_analysis_store] = override_analysis_store
    app.dependency_overrides[get_material_index] = override_material_index

    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/api/v1/remediations", json=request.model_dump())

    try:
        response = run_test_async(send())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "remediation_context_mismatch"
    assert response.json()["error"]["details"] == {"field": "retrieval.results.chunk"}
    assert fake.prompts == []


def test_api_requires_generation_request_id() -> None:
    payload = generation_request().model_dump()
    payload.pop("generation_request_id", None)

    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/api/v1/remediations", json=payload)

    response = run_test_async(send())

    assert response.status_code == 422


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
        run_test_async(service.generate_remediation("grounded prompt"))

    assert caught.value.code == expected_code
    assert "secret timeout detail" not in caught.value.message


def test_gemini_adapter_retries_one_transient_provider_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    service = GeminiLLMService(api_key="test-key", model_id="gemini-test", timeout_ms=5_000)
    calls = 0

    class FakeTypes:
        @staticmethod
        def GenerateContentConfig(**kwargs):
            return kwargs

    class TransientServerError(Exception):
        code = 503

    class FakeModels:
        async def generate_content(self, **_kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise TransientServerError("temporary provider detail")
            return type("Response", (), {"parsed": grounded_draft(), "text": None})()

    monkeypatch.setattr("app.providers.llm.gemini.RETRY_DELAY_SECONDS", 0)
    service._types = FakeTypes()
    service._client = type("Client", (), {"aio": type("Async", (), {"models": FakeModels()})()})()

    result = run_test_async(service.generate_remediation("grounded prompt"))

    assert calls == 2
    assert result.source_references == ["chunk_001"]


def test_gemini_total_budget_includes_retry_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    service = GeminiLLMService(
        api_key="test-key",
        model_id="gemini-test",
        timeout_ms=5_000,
        total_budget_ms=25,
    )
    calls = 0

    class FakeTypes:
        @staticmethod
        def GenerateContentConfig(**kwargs):
            return kwargs

    class TransientServerError(Exception):
        code = 503

    class FakeModels:
        async def generate_content(self, **_kwargs):
            nonlocal calls
            calls += 1
            raise TransientServerError("temporary provider detail")

    monkeypatch.setattr("app.providers.llm.gemini.RETRY_DELAY_SECONDS", 0.1)
    service._types = FakeTypes()
    service._client = type("Client", (), {"aio": type("Async", (), {"models": FakeModels()})()})()

    with pytest.raises(LLMProviderError) as caught:
        run_test_async(service.generate_remediation("grounded prompt"))

    assert caught.value.code == "llm_timeout"
    assert calls == 1
