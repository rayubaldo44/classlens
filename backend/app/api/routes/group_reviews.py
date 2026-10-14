from typing import Annotated

from fastapi import APIRouter, Depends

from app.concurrency import run_in_worker
from app.providers.analysis_store import AnalysisStore, get_analysis_store
from app.providers.group_review_store import GroupReviewStore, get_group_review_store
from app.providers.remediation_store import RemediationStore, get_remediation_store
from app.schemas.assessment import ErrorResponse
from app.schemas.group_reviews import GroupReviewActionRequest, GroupReviewResponse
from app.services.group_reviews import apply_group_review, get_group_reviews

router = APIRouter(prefix="/api/v1/assessments/analyses", tags=["group-reviews"])


@router.get(
    "/{analysis_id}/group-reviews",
    response_model=GroupReviewResponse,
    responses={404: {"model": ErrorResponse}},
)
async def read_group_reviews(
    analysis_id: str,
    analysis_store: Annotated[AnalysisStore, Depends(get_analysis_store)],
    review_store: Annotated[GroupReviewStore, Depends(get_group_review_store)],
) -> GroupReviewResponse:
    return await run_in_worker(get_group_reviews, analysis_id, analysis_store, review_store)


@router.post(
    "/{analysis_id}/group-reviews",
    response_model=GroupReviewResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def update_group_reviews(
    analysis_id: str,
    request: GroupReviewActionRequest,
    analysis_store: Annotated[AnalysisStore, Depends(get_analysis_store)],
    review_store: Annotated[GroupReviewStore, Depends(get_group_review_store)],
    remediation_store: Annotated[RemediationStore, Depends(get_remediation_store)],
) -> GroupReviewResponse:
    return await run_in_worker(
        apply_group_review,
        analysis_id,
        request,
        analysis_store,
        review_store,
        remediation_store,
    )
