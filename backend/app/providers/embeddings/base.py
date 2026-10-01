from typing import Protocol


class EmbeddingService(Protocol):
    @property
    def model_id(self) -> str: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...
