from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, UploadFile

from app.schemas.assessment import AssessmentPreview, ErrorResponse
from app.services.assessment_intake import IntakeError, MAX_CSV_BYTES, parse_assessment_csv

router = APIRouter(prefix="/api/v1/assessments", tags=["assessments"])
DEMO_CSV_PATH = Path(__file__).resolve().parents[4] / "data" / "demo" / "photosynthesis_responses.csv"


@router.post(
    "/preview",
    response_model=AssessmentPreview,
    responses={400: {"model": ErrorResponse}, 413: {"model": ErrorResponse}, 415: {"model": ErrorResponse}},
)
async def preview_assessment(
    file: Annotated[UploadFile, File(description="UTF-8 assessment response CSV")],
    data_label: Annotated[Literal["teacher_upload", "synthetic_demo"], Form()] = "teacher_upload",
) -> AssessmentPreview:
    filename = file.filename or "responses.csv"
    if not filename.lower().endswith(".csv"):
        raise IntakeError("unsupported_file_type", "Choose a file with a .csv extension.")

    content = await file.read(MAX_CSV_BYTES + 1)
    return parse_assessment_csv(content, filename=filename, data_label=data_label)


@router.get("/demo/photosynthesis/preview", response_model=AssessmentPreview)
async def preview_photosynthesis_demo() -> AssessmentPreview:
    return parse_assessment_csv(
        DEMO_CSV_PATH.read_bytes(),
        filename=DEMO_CSV_PATH.name,
        data_label="synthetic_demo",
    )
