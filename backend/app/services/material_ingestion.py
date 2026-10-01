import hashlib
import math
import re
from pathlib import Path
from typing import Literal

from app.config import MaterialSettings
from app.providers.embeddings import EmbeddingService
from app.providers.material_index import MaterialIndex, MaterialRecord
from app.schemas.materials import LearningMaterial, MaterialChunk, MaterialIngestionResponse

MAX_MATERIAL_BYTES = 1_000_000


class MaterialError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details or {}


def ingest_learning_material(
    content: bytes,
    *,
    filename: str,
    title: str | None,
    source_kind: Literal["teacher_upload", "synthetic_demo"],
    embedding_service: EmbeddingService,
    material_index: MaterialIndex,
    settings: MaterialSettings,
) -> MaterialIngestionResponse:
    text = _extract_and_clean_text(content)
    chunks = _chunk_text(text, settings.chunk_size_chars, settings.chunk_overlap_chars)
    if not chunks:
        raise MaterialError("no_chunks_generated", "No usable text chunks could be generated from this material.")

    try:
        embeddings = _normalize_embeddings(embedding_service.embed([chunk.text for chunk in chunks]), len(chunks))
    except MaterialError:
        raise
    except Exception as error:
        raise MaterialError(
            "material_embedding_failed",
            "The learning material could not be embedded.",
            retryable=True,
            details={"provider_error": type(error).__name__},
        ) from error

    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    material_id = f"mat_{content_hash[:16]}"
    safe_filename = Path(filename.replace("\\", "/")).name or "learning-material.txt"
    material = LearningMaterial(
        material_id=material_id,
        title=(title or Path(safe_filename).stem).strip() or Path(safe_filename).stem,
        filename=safe_filename,
        source_kind=source_kind,
        content_hash=content_hash,
        chunk_count=len(chunks),
        chunk_size_chars=settings.chunk_size_chars,
        chunk_overlap_chars=settings.chunk_overlap_chars,
        embedding_model=embedding_service.model_id,
        embedding_dimension=len(embeddings[0]),
    )
    try:
        material_index.upsert(MaterialRecord(material=material, chunks=tuple(chunks), embeddings=tuple(map(tuple, embeddings))))
    except Exception as error:
        raise MaterialError(
            "material_index_failed",
            "The learning material could not be added to the retrieval index.",
            retryable=True,
            details={"index_error": type(error).__name__},
        ) from error

    return MaterialIngestionResponse(
        status="ready",
        material=material,
        message=f"Material is ready with {len(chunks)} persisted chunks.",
    )


def _extract_and_clean_text(content: bytes) -> str:
    if not content:
        raise MaterialError("material_empty", "The learning material file is empty.")
    if len(content) > MAX_MATERIAL_BYTES:
        raise MaterialError("material_too_large", "The learning material exceeds the 1 MB limit.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise MaterialError("material_encoding_error", "The material must use UTF-8 plain text.") from error
    if "\x00" in text:
        raise MaterialError("material_invalid_text", "The material contains unsupported null characters.")

    # Normalize line endings and excess blank lines, while retaining the text used for source chunks.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    if not text:
        raise MaterialError("material_empty", "The learning material contains no text.")
    return text


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[MaterialChunk]:
    if chunk_size < 1 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Chunk size must be positive and overlap must be smaller than chunk size.")
    chunks: list[MaterialChunk] = []
    start = 0
    while start < len(text):
        proposed_end = min(start + chunk_size, len(text))
        end = proposed_end
        if proposed_end < len(text):
            search_start = start + int(chunk_size * 0.65)
            paragraph_boundary = text.rfind("\n\n", search_start, proposed_end)
            sentence_boundary = max(text.rfind(". ", search_start, proposed_end), text.rfind("? ", search_start, proposed_end), text.rfind("! ", search_start, proposed_end))
            whitespace_boundary = text.rfind(" ", search_start, proposed_end)
            if paragraph_boundary >= 0:
                end = paragraph_boundary
            elif sentence_boundary >= 0:
                end = sentence_boundary + 1
            elif whitespace_boundary > start:
                end = whitespace_boundary
        if end <= start:
            end = proposed_end

        chunk_start = start
        while chunk_start < end and text[chunk_start].isspace():
            chunk_start += 1
        chunk_end = end
        while chunk_end > chunk_start and text[chunk_end - 1].isspace():
            chunk_end -= 1
        if chunk_start < chunk_end:
            index = len(chunks)
            chunks.append(
                MaterialChunk(
                    chunk_id=f"chunk_{index + 1:03d}",
                    chunk_index=index,
                    text=text[chunk_start:chunk_end],
                    start_char=chunk_start,
                    end_char=chunk_end,
                )
            )
        if end >= len(text):
            break
        next_start = max(start + 1, end - overlap)
        while next_start < end and not text[next_start].isspace():
            next_start += 1
        while next_start < end and text[next_start].isspace():
            next_start += 1
        start = next_start if next_start < end else max(start + 1, end - overlap)
    return chunks


def _normalize_embeddings(embeddings: list[list[float]], expected_count: int) -> list[list[float]]:
    if len(embeddings) != expected_count or not embeddings:
        raise MaterialError(
            "material_embedding_invalid_response",
            "The embedding provider returned an unexpected number of vectors.",
            retryable=True,
        )
    dimension = len(embeddings[0])
    if dimension == 0 or any(len(vector) != dimension for vector in embeddings):
        raise MaterialError("material_embedding_invalid_response", "The embedding provider returned inconsistent vectors.", retryable=True)
    normalized: list[list[float]] = []
    for vector in embeddings:
        if any(not math.isfinite(value) for value in vector):
            raise MaterialError("material_embedding_invalid_response", "The embedding provider returned non-finite values.", retryable=True)
        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            raise MaterialError("material_embedding_invalid_response", "The embedding provider returned an empty vector.", retryable=True)
        normalized.append([value / magnitude for value in vector])
    return normalized
