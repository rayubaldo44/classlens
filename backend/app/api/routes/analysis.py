from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from app.config import get_analysis_settings
from app.providers.embeddings import EmbeddingService, get_embedding_service
from app.providers.analysis_store import AnalysisStore, get_analysis_store
from app.schemas.analysis import AnalysisResponse
from app.schemas.assessment import ErrorResponse
from app.services.assessment_intake import MAX_CSV_BYTES, IntakeError, parse_assessment_csv_full
from app.services.misconception_analysis import analyze_assessment
from app.services.results import ResultsError

router = APIRouter(prefix="/api/v1/assessments", tags=["analysis"])
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
) -> AnalysisResponse:
    filename = file.filename or "responses.csv"
    if not filename.lower().endswith(".csv"):
        raise IntakeError("unsupported_file_type", "Choose a file with a .csv extension.")
    content = await file.read(MAX_CSV_BYTES + 1)
    parsed = parse_assessment_csv_full(content, filename=filename, data_label="teacher_upload")
    result = analyze_assessment(parsed, embedding_service, get_analysis_settings())
    analysis_store.save(parsed, result)
    return result


@router.get(
    "/demo/photosynthesis/analysis",
    response_model=AnalysisResponse,
    responses={503: {"model": ErrorResponse}},
)
async def analyze_photosynthesis_demo(
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
    analysis_store: Annotated[AnalysisStore, Depends(get_analysis_store)],
) -> AnalysisResponse:
    parsed = parse_assessment_csv_full(
        DEMO_CSV_PATH.read_bytes(),
        filename=DEMO_CSV_PATH.name,
        data_label="synthetic_demo",
    )
    result = analyze_assessment(parsed, embedding_service, get_analysis_settings())
    analysis_store.save(parsed, result)
    return result


@router.get(
    "/analyses/{analysis_id}",
    response_model=AnalysisResponse,
    responses={404: {"model": ErrorResponse}},
)
async def read_analysis(
    analysis_id: str,
    analysis_store: Annotated[AnalysisStore, Depends(get_analysis_store)],
) -> AnalysisResponse:
    snapshot = analysis_store.get(analysis_id)
    if snapshot is None:
        raise ResultsError("initial_assessment_not_found", "The requested assessment analysis was not found.")
    return snapshot.result
