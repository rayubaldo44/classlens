import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

DEFAULT_CORS_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")
DEFAULT_EMBEDDING_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"


def get_cors_origins() -> list[str]:
    """Return explicitly configured browser origins or local Vite defaults."""
    configured_origins = os.getenv("CLASSLENS_CORS_ORIGINS")
    if configured_origins is None:
        return list(DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in configured_origins.split(",") if origin.strip()]


@dataclass(frozen=True)
class AnalysisSettings:
    embedding_model: str
    similarity_threshold: float
    min_group_size: int
    embedding_revision: str = DEFAULT_EMBEDDING_REVISION


@dataclass(frozen=True)
class MaterialSettings:
    chunk_size_chars: int
    chunk_overlap_chars: int
    retrieval_top_k: int
    minimum_relevance_score: float


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    model: str
    timeout_ms: int
    total_budget_ms: int
    label_total_budget_ms: int
    api_key: str = field(repr=False)


def get_analysis_settings() -> AnalysisSettings:
    threshold = float(os.getenv("CLASSLENS_SIMILARITY_THRESHOLD", "0.70"))
    min_group_size = int(os.getenv("CLASSLENS_MIN_GROUP_SIZE", "3"))
    if not 0 < threshold <= 1:
        raise ValueError("CLASSLENS_SIMILARITY_THRESHOLD must be greater than 0 and at most 1.")
    if min_group_size < 3:
        raise ValueError("CLASSLENS_MIN_GROUP_SIZE must be at least 3.")
    return AnalysisSettings(
        embedding_model=os.getenv(
            "CLASSLENS_EMBEDDING_MODEL",
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        ),
        similarity_threshold=threshold,
        min_group_size=min_group_size,
        embedding_revision=os.getenv("CLASSLENS_EMBEDDING_REVISION", DEFAULT_EMBEDDING_REVISION).strip()
        or DEFAULT_EMBEDDING_REVISION,
    )


def get_material_settings() -> MaterialSettings:
    chunk_size = int(os.getenv("CLASSLENS_MATERIAL_CHUNK_SIZE_CHARS", "900"))
    chunk_overlap = int(os.getenv("CLASSLENS_MATERIAL_CHUNK_OVERLAP_CHARS", "120"))
    top_k = int(os.getenv("CLASSLENS_RETRIEVAL_TOP_K", "3"))
    threshold = float(os.getenv("CLASSLENS_RETRIEVAL_MIN_SCORE", "0.42"))
    if chunk_size < 200:
        raise ValueError("CLASSLENS_MATERIAL_CHUNK_SIZE_CHARS must be at least 200.")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("CLASSLENS_MATERIAL_CHUNK_OVERLAP_CHARS must be non-negative and smaller than chunk size.")
    if not 1 <= top_k <= 10:
        raise ValueError("CLASSLENS_RETRIEVAL_TOP_K must be between 1 and 10.")
    if not 0 <= threshold <= 1:
        raise ValueError("CLASSLENS_RETRIEVAL_MIN_SCORE must be between 0 and 1.")
    return MaterialSettings(
        chunk_size_chars=chunk_size,
        chunk_overlap_chars=chunk_overlap,
        retrieval_top_k=top_k,
        minimum_relevance_score=threshold,
    )


def get_llm_settings() -> LLMSettings:
    timeout_ms = int(os.getenv("CLASSLENS_LLM_TIMEOUT_MS", "45000"))
    total_budget_ms = int(os.getenv("CLASSLENS_LLM_TOTAL_BUDGET_MS", "60000"))
    label_total_budget_ms = int(os.getenv("CLASSLENS_LABEL_TOTAL_BUDGET_MS", "12000"))
    if not 5_000 <= timeout_ms <= 120_000:
        raise ValueError("CLASSLENS_LLM_TIMEOUT_MS must be between 5000 and 120000.")
    if not 5_000 <= total_budget_ms <= 180_000:
        raise ValueError("CLASSLENS_LLM_TOTAL_BUDGET_MS must be between 5000 and 180000.")
    if not 1_000 <= label_total_budget_ms <= 30_000:
        raise ValueError("CLASSLENS_LABEL_TOTAL_BUDGET_MS must be between 1000 and 30000.")
    return LLMSettings(
        provider="google-gemini",
        model=os.getenv("CLASSLENS_LLM_MODEL", "gemini-3.1-flash-lite").strip(),
        timeout_ms=timeout_ms,
        total_budget_ms=total_budget_ms,
        label_total_budget_ms=label_total_budget_ms,
        api_key=os.getenv("GEMINI_API_KEY", "").strip(),
    )
