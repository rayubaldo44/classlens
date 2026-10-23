from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from app.concurrency import run_in_worker

from app.config import get_material_settings
from app.providers.embeddings import EmbeddingService, get_embedding_service
from app.providers.material_index import MaterialIndex, get_material_index
from app.providers.analysis_store import AnalysisStore, get_analysis_store
from app.providers.group_review_store import GroupReviewStore, get_group_review_store
from app.schemas.assessment import ErrorResponse
from app.schemas.materials import (
    MaterialIngestionResponse,
    MaterialRetrievalResponse,
    MisconceptionRetrievalContext,
)
from app.services.material_ingestion import MAX_MATERIAL_BYTES, MaterialError, ingest_learning_material
from app.services.material_retrieval import retrieve_for_misconception

router = APIRouter(prefix="/api/v1/learning-materials", tags=["learning-materials"])
DEMO_MATERIAL_PATH = (
    Path(__file__).resolve().parents[4] / "data" / "demo" / "learning_materials" / "photosynthesis_grade7.txt"
)


@router.post(
    "/ingest",
    response_model=MaterialIngestionResponse,
    responses={400: {"model": ErrorResponse}, 413: {"model": ErrorResponse}, 415: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def ingest_uploaded_material(
    file: Annotated[UploadFile, File(description="UTF-8 plain text learning material")],
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
    material_index: Annotated[MaterialIndex, Depends(get_material_index)],
    title: Annotated[str | None, Form()] = None,
) -> MaterialIngestionResponse:
    filename = file.filename or "learning-material.txt"
    if not filename.lower().endswith(".txt"):
        raise MaterialError("unsupported_material_type", "Choose a UTF-8 plain text file with a .txt extension.")
    content = await file.read(MAX_MATERIAL_BYTES + 1)
    return await run_in_worker(
        ingest_learning_material,
        content,
        filename=filename,
        title=title,
        source_kind="teacher_upload",
        embedding_service=embedding_service,
        material_index=material_index,
        settings=get_material_settings(),
    )


@router.post(
    "/demo/photosynthesis/ingest",
    response_model=MaterialIngestionResponse,
    responses={400: {"model": ErrorResponse}, 413: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def ingest_photosynthesis_demo_material(
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
    material_index: Annotated[MaterialIndex, Depends(get_material_index)],
) -> MaterialIngestionResponse:
    return await run_in_worker(
        lambda: ingest_learning_material(
            DEMO_MATERIAL_PATH.read_bytes(),
            filename=DEMO_MATERIAL_PATH.name,
            title="Grade 7 Photosynthesis Learning Notes",
            source_kind="synthetic_demo",
            embedding_service=embedding_service,
            material_index=material_index,
            settings=get_material_settings(),
        )
    )


@router.post(
    "/{material_id}/retrieve",
    response_model=MaterialRetrievalResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def retrieve_material_for_misconception(
    material_id: str,
    context: MisconceptionRetrievalContext,
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
    material_index: Annotated[MaterialIndex, Depends(get_material_index)],
    analysis_store: Annotated[AnalysisStore, Depends(get_analysis_store)],
    review_store: Annotated[GroupReviewStore, Depends(get_group_review_store)],
) -> MaterialRetrievalResponse:
    return await run_in_worker(
        retrieve_for_misconception,
        material_id,
        context,
        embedding_service=embedding_service,
        material_index=material_index,
        settings=get_material_settings(),
        analysis_store=analysis_store,
        review_store=review_store,
    )
