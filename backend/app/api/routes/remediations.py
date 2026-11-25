from typing import Annotated

from fastapi import APIRouter, Depends

from app.concurrency import run_in_worker
from app.config import MaterialSettings, get_material_settings
from app.providers.analysis_store import AnalysisStore, get_analysis_store
from app.providers.embeddings import EmbeddingService, get_embedding_service
from app.providers.group_review_store import GroupReviewStore, get_group_review_store
from app.providers.llm import LLMService, get_llm_service
from app.providers.material_index import MaterialIndex, get_material_index
from app.providers.remediation_store import RemediationStore, get_remediation_store
from app.schemas.assessment import ErrorResponse
from app.schemas.remediations import (
    RemediationGenerationRequest,
    RemediationGenerationResponse,
    RemediationRecord,
    RemediationReviewRequest,
)
from app.services.remediation import generate_grounded_remediation, get_remediation, review_remediation

router = APIRouter(prefix="/api/v1/remediations", tags=["remediations"])


@router.post(
    "",
    response_model=RemediationGenerationResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def generate_remediation(
    request: RemediationGenerationRequest,
    llm_service: Annotated[LLMService, Depends(get_llm_service)],
    store: Annotated[RemediationStore, Depends(get_remediation_store)],
    analysis_store: Annotated[AnalysisStore, Depends(get_analysis_store)],
    material_index: Annotated[MaterialIndex, Depends(get_material_index)],
    review_store: Annotated[GroupReviewStore, Depends(get_group_review_store)],
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
    settings: Annotated[MaterialSettings, Depends(get_material_settings)],
) -> RemediationGenerationResponse:
    return await generate_grounded_remediation(
        request,
        llm_service=llm_service,
        store=store,
        analysis_store=analysis_store,
        material_index=material_index,
        review_store=review_store,
        embedding_service=embedding_service,
        settings=settings,
    )


@router.get(
    "/{remediation_id}",
    response_model=RemediationRecord,
    responses={404: {"model": ErrorResponse}},
)
async def read_remediation(
    remediation_id: str,
    store: Annotated[RemediationStore, Depends(get_remediation_store)],
) -> RemediationRecord:
    return await run_in_worker(get_remediation, remediation_id, store=store)


@router.patch(
    "/{remediation_id}",
    response_model=RemediationRecord,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def update_remediation(
    remediation_id: str,
    request: RemediationReviewRequest,
    store: Annotated[RemediationStore, Depends(get_remediation_store)],
) -> RemediationRecord:
    return await run_in_worker(review_remediation, remediation_id, request, store=store)
