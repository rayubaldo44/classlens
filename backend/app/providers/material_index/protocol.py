from dataclasses import dataclass
from typing import Protocol

from app.schemas.materials import LearningMaterial, MaterialChunk


@dataclass(frozen=True)
class MaterialSearchHit:
    chunk: MaterialChunk
    similarity: float


@dataclass(frozen=True)
class MaterialRecord:
    material: LearningMaterial
    chunks: tuple[MaterialChunk, ...]
    embeddings: tuple[tuple[float, ...], ...]


def score_material(record: MaterialRecord, query: list[float], limit: int) -> list[MaterialSearchHit]:
    """Score one snapshot so cache eviction cannot change an in-flight retrieval."""
    hits = [
        MaterialSearchHit(
            chunk=chunk,
            similarity=sum(a * b for a, b in zip(query, vector, strict=True)),
        )
        for chunk, vector in zip(record.chunks, record.embeddings, strict=True)
    ]
    hits.sort(key=lambda hit: (-hit.similarity, hit.chunk.chunk_index))
    return hits[:limit]


class MaterialIndex(Protocol):
    def upsert(self, record: MaterialRecord) -> None: ...

    def get(self, material_id: str) -> MaterialRecord | None: ...
