from functools import lru_cache
from threading import RLock

from .protocol import MaterialIndex, MaterialRecord


class InMemoryMaterialIndex:
    """Process-local demo index. Replacing it requires preserving the MaterialIndex contract."""

    def __init__(self) -> None:
        self._records: dict[str, MaterialRecord] = {}
        self._lock = RLock()

    def upsert(self, record: MaterialRecord) -> None:
        with self._lock:
            self._records[record.material.material_id] = record

    def get(self, material_id: str) -> MaterialRecord | None:
        with self._lock:
            return self._records.get(material_id)


@lru_cache(maxsize=1)
def _get_material_index() -> InMemoryMaterialIndex:
    return InMemoryMaterialIndex()


async def get_material_index() -> MaterialIndex:
    from app.providers.postgres import get_postgres_material_index

    return get_postgres_material_index()
