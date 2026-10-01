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


class MaterialIndex(Protocol):
    def upsert(self, record: MaterialRecord) -> None: ...

    def get(self, material_id: str) -> MaterialRecord | None: ...

    def search(
        self,
        material_id: str,
        query_embedding: list[float],
        limit: int,
    ) -> list[MaterialSearchHit]: ...
