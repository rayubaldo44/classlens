from pathlib import Path
from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from app.concurrency import run_in_worker
from app.request_limits import UploadRoute
from app.config import get_analysis_settings
from app.database import DatabaseError
from app.providers.embeddings import EmbeddingService, get_embedding_service
from app.providers.analysis_store import AnalysisStore, get_analysis_store
from app.providers.llm import LLMService, get_llm_service
from app.schemas.analysis import AnalysisResponse
from app.schemas.assessment import ErrorResponse
from app.services.assessment_intake import MAX_CSV_BYTES, IntakeError, ParsedAssessment, parse_assessment_csv_full
from app.services.misconception_analysis import analyze_assessment
from app.services.misconception_interpretation import interpret_misconception_groups
from app.services.results import ResultsError
from app.telemetry import log_stage

router = APIRouter(route_class=UploadRoute, prefix="/api/v1/assessments", tags=["analysis"])
DEMO_CSV_PATH = Path(__file__).resolve().parents[4] / "data" / "demo" / "photosynthesis_responses.csv"


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def analyze_uploaded_assessment(
    file: Annotated[UploadFile, File(description="Validated assessment response CSV")],
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
    analysis_store: Annotated[AnalysisStore, Depends(get_analysis_store)],
    llm_service: Annotated[LLMService, Depends(get_llm_service)],
) -> AnalysisResponse:
    filename = file.filename or "responses.csv"
    if not filename.lower().endswith(".csv"):
        raise IntakeError("unsupported_file_type", "Choose a file with a .csv extension.")
    content = await file.read(MAX_CSV_BYTES + 1)
    started = perf_counter()
    parsed = await run_in_worker(
        parse_assessment_csv_full, content, filename=filename, data_label="teacher_upload"
    )
    log_stage("csv_parse", (perf_counter() - started) * 1000, response_count=parsed.preview.summary.response_count)
    return await _run_baseline_analysis(parsed, embedding_service, analysis_store, llm_service)


@router.get(
    "/demo/photosynthesis/analysis",
    response_model=AnalysisResponse,
    responses={503: {"model": ErrorResponse}},
)
async def analyze_photosynthesis_demo(
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
    analysis_store: Annotated[AnalysisStore, Depends(get_analysis_store)],
    llm_service: Annotated[LLMService, Depends(get_llm_service)],
) -> AnalysisResponse:
    started = perf_counter()
    parsed = await run_in_worker(
        lambda: parse_assessment_csv_full(
            DEMO_CSV_PATH.read_bytes(),
            filename=DEMO_CSV_PATH.name,
            data_label="synthetic_demo",
        )
    )
    log_stage("csv_parse", (perf_counter() - started) * 1000, response_count=parsed.preview.summary.response_count)
    return await _run_baseline_analysis(parsed, embedding_service, analysis_store, llm_service)


async def _run_baseline_analysis(
    parsed: ParsedAssessment,
    embedding_service: EmbeddingService,
    analysis_store: AnalysisStore,
    llm_service: LLMService,
) -> AnalysisResponse:
    result = await run_in_worker(analyze_assessment, parsed, embedding_service, get_analysis_settings())
    existing = await run_in_worker(analysis_store.get, result.analysis_id)
    if existing is not None:
        return existing.result

    if result.groups:
        result = await interpret_misconception_groups(result, llm_service)
    started = perf_counter()
    await run_in_worker(analysis_store.save, parsed, result)
    log_stage("database_persistence", (perf_counter() - started) * 1000, operation="analysis_save")
    canonical = await run_in_worker(analysis_store.get, result.analysis_id)
    if canonical is None:
        raise DatabaseError(
            "database_operation_failed",
            "The persistent analysis could not be reloaded.",
        )
    return canonical.result


@router.get(
    "/analyses/{analysis_id}",
    response_model=AnalysisResponse,
    responses={404: {"model": ErrorResponse}},
)
async def read_analysis(
    analysis_id: str,
    analysis_store: Annotated[AnalysisStore, Depends(get_analysis_store)],
) -> AnalysisResponse:
    snapshot = await run_in_worker(analysis_store.get, analysis_id)
    if snapshot is None:
        raise ResultsError("initial_assessment_not_found", "The requested assessment analysis was not found.")
    return snapshot.result
