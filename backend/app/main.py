import os
from contextlib import asynccontextmanager
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .api.routes.assessments import router as assessments_router
from .api.routes.analysis import router as analysis_router
from .api.routes.materials import router as materials_router
from .api.routes.remediations import router as remediations_router
from .api.routes.results import router as results_router
from .config import get_cors_origins
from .services.assessment_intake import IntakeError
from .services.misconception_analysis import AnalysisError
from .services.material_ingestion import MaterialError
from .providers.llm import LLMProviderError
from .services.remediation import RemediationError
from .services.results import ResultsError
from .database import DatabaseError, get_database
from .providers.embeddings import get_embedding_service
from .providers.embeddings.sentence_transformer import embedding_model_loaded


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: Literal["classlens-api"]


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, Literal["ready", "not_ready"]]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if os.getenv("CLASSLENS_WARM_EMBEDDING_MODEL", "").strip().lower() in {"1", "true", "yes"}:
        embedding_service = await get_embedding_service()
        embedding_service.embed(["ClassLens startup warm-up"])
    yield


app = FastAPI(title="ClassLens API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Accept", "Content-Type"],
)
app.include_router(assessments_router)
app.include_router(analysis_router)
app.include_router(materials_router)
app.include_router(remediations_router)
app.include_router(results_router)

ERROR_STATUS_CODES = {
    "file_too_large": 413,
    "unsupported_file_type": 415,
}


@app.exception_handler(IntakeError)
async def handle_intake_error(_request: Request, error: IntakeError) -> JSONResponse:
    return JSONResponse(
        status_code=ERROR_STATUS_CODES.get(error.code, 400),
        content={
            "error": {
                "code": error.code,
                "message": error.message,
                "details": error.details,
                "retryable": False,
                "request_id": f"req_{uuid4().hex}",
            }
        },
    )


@app.exception_handler(AnalysisError)
async def handle_analysis_error(_request: Request, error: AnalysisError) -> JSONResponse:
    return JSONResponse(
        status_code=503 if error.retryable else 400,
        content={
            "error": {
                "code": error.code,
                "message": error.message,
                "details": error.details,
                "retryable": error.retryable,
                "request_id": f"req_{uuid4().hex}",
            }
        },
    )


@app.exception_handler(MaterialError)
async def handle_material_error(_request: Request, error: MaterialError) -> JSONResponse:
    status_code = (
        413 if error.code == "material_too_large"
        else 415 if error.code == "unsupported_material_type"
        else 404 if error.code == "material_not_found"
        else 503 if error.retryable
        else 400
    )
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": error.code,
                "message": error.message,
                "details": error.details,
                "retryable": error.retryable,
                "request_id": f"req_{uuid4().hex}",
            }
        },
    )


@app.exception_handler(LLMProviderError)
async def handle_llm_provider_error(_request: Request, error: LLMProviderError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": error.code,
                "message": error.message,
                "details": {},
                "retryable": error.retryable,
                "request_id": f"req_{uuid4().hex}",
            }
        },
    )


@app.exception_handler(RemediationError)
async def handle_remediation_error(_request: Request, error: RemediationError) -> JSONResponse:
    status_code = (
        404 if error.code == "remediation_not_found"
        else 409 if error.code == "remediation_invalid_transition"
        else 502 if error.code in {"llm_malformed_output", "llm_ungrounded_output"}
        else 503 if error.retryable or error.code == "llm_not_configured"
        else 400
    )
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": error.code,
                "message": error.message,
                "details": error.details,
                "retryable": error.retryable,
                "request_id": f"req_{uuid4().hex}",
            }
        },
    )


@app.exception_handler(ResultsError)
async def handle_results_error(_request: Request, error: ResultsError) -> JSONResponse:
    status_code = (
        404 if error.code in {"initial_assessment_not_found", "misconception_not_found", "intervention_not_found", "results_not_found"}
        else 409 if error.code in {"intervention_not_approved", "results_context_mismatch"}
        else 400
    )
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": error.code,
                "message": error.message,
                "details": error.details,
                "retryable": error.retryable,
                "request_id": f"req_{uuid4().hex}",
            }
        },
    )


@app.exception_handler(DatabaseError)
async def handle_database_error(_request: Request, error: DatabaseError) -> JSONResponse:
    return JSONResponse(
        status_code=409 if error.code in {"database_conflict", "database_invalid_relationship"} else 503,
        content={
            "error": {
                "code": error.code,
                "message": error.message,
                "details": error.details,
                "retryable": error.retryable,
                "request_id": f"req_{uuid4().hex}",
            }
        },
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="classlens-api")


@app.get("/ready", response_model=ReadinessResponse)
def readiness() -> JSONResponse:
    try:
        with get_database().connection() as connection:
            connection.execute("select 1")
        database_status = "ready"
    except Exception:
        database_status = "not_ready"

    checks = {
        "database": database_status,
        "embedding_model": "ready" if embedding_model_loaded() else "not_ready",
    }
    status = "ready" if all(value == "ready" for value in checks.values()) else "not_ready"
    return JSONResponse(
        status_code=200 if status == "ready" else 503,
        content=ReadinessResponse(status=status, checks=checks).model_dump(),
    )
