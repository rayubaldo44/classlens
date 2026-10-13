from pathlib import Path
from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from app.concurrency import run_in_worker

from app.config import get_analysis_settings
from app.providers.analysis_store import AnalysisStore, get_analysis_store
from app.providers.embeddings import EmbeddingService, get_embedding_service
from app.providers.remediation_store import RemediationStore, get_remediation_store
from app.providers.results_store import ResultsStore, get_results_store
from app.schemas.assessment import ErrorResponse
from app.schemas.results import FollowUpComparisonLink, FollowUpComparisonRecord
from app.services.assessment_intake import MAX_CSV_BYTES, IntakeError, parse_assessment_csv_full
from app.services.results import create_follow_up_comparison, get_follow_up_comparison
from app.telemetry import log_stage

router = APIRouter(prefix="/api/v1/results", tags=["results"])
DEMO_FOLLOW_UP_PATH = (
    Path(__file__).resolve().parents[4] / "data" / "demo" / "photosynthesis_follow_up_responses.csv"
)


@router.post(
    "",
    response_model=FollowUpComparisonRecord,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def submit_follow_up_results(
    file: Annotated[UploadFile, File(description="Follow-up assessment CSV in the existing assessment schema")],
    baseline_analysis_id: Annotated[str, Form()],
    group_id: Annotated[str, Form()],
    remediation_id: Annotated[str, Form()],
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
    analysis_store: Annotated[AnalysisStore, Depends(get_analysis_store)],
    remediation_store: Annotated[RemediationStore, Depends(get_remediation_store)],
    results_store: Annotated[ResultsStore, Depends(get_results_store)],
) -> FollowUpComparisonRecord:
    filename = file.filename or "follow_up_responses.csv"
    if not filename.lower().endswith(".csv"):
        raise IntakeError("unsupported_file_type", "Choose a follow-up file with a .csv extension.")
    content = await file.read(MAX_CSV_BYTES + 1)
    started = perf_counter()
    parsed = await run_in_worker(
        parse_assessment_csv_full, content, filename=filename, data_label="teacher_upload"
    )
    log_stage("csv_parse", (perf_counter() - started) * 1000, response_count=parsed.preview.summary.response_count)
    return await run_in_worker(
        create_follow_up_comparison,
        FollowUpComparisonLink(
            baseline_analysis_id=baseline_analysis_id,
            group_id=group_id,
            remediation_id=remediation_id,
        ),
        parsed,
        embedding_service=embedding_service,
        settings=get_analysis_settings(),
        analysis_store=analysis_store,
        remediation_store=remediation_store,
        results_store=results_store,
    )


@router.post(
    "/demo/photosynthesis",
    response_model=FollowUpComparisonRecord,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def submit_photosynthesis_demo_follow_up(
    link: FollowUpComparisonLink,
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
    analysis_store: Annotated[AnalysisStore, Depends(get_analysis_store)],
    remediation_store: Annotated[RemediationStore, Depends(get_remediation_store)],
    results_store: Annotated[ResultsStore, Depends(get_results_store)],
) -> FollowUpComparisonRecord:
    started = perf_counter()
    parsed = await run_in_worker(
        lambda: parse_assessment_csv_full(
            DEMO_FOLLOW_UP_PATH.read_bytes(),
            filename=DEMO_FOLLOW_UP_PATH.name,
            data_label="synthetic_demo",
        )
    )
    log_stage("csv_parse", (perf_counter() - started) * 1000, response_count=parsed.preview.summary.response_count)
    return await run_in_worker(
        create_follow_up_comparison,
        link,
        parsed,
        embedding_service=embedding_service,
        settings=get_analysis_settings(),
        analysis_store=analysis_store,
        remediation_store=remediation_store,
        results_store=results_store,
    )


@router.get(
    "/{comparison_id}",
    response_model=FollowUpComparisonRecord,
    responses={404: {"model": ErrorResponse}},
)
async def read_follow_up_results(
    comparison_id: str,
    results_store: Annotated[ResultsStore, Depends(get_results_store)],
) -> FollowUpComparisonRecord:
    return await run_in_worker(get_follow_up_comparison, comparison_id, results_store=results_store)
