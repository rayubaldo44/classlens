from functools import lru_cache

from app.config import get_analysis_settings


class SentenceTransformerEmbeddingService:
    def __init__(self, model_id: str) -> None:
        self._model_id = model_id

    @property
    def model_id(self) -> str:
        return self._model_id

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = _load_model(self._model_id).encode(
            texts,
            batch_size=32,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.tolist()


@lru_cache(maxsize=1)
def _get_embedding_service(model_id: str) -> SentenceTransformerEmbeddingService:
    return SentenceTransformerEmbeddingService(model_id)


async def get_embedding_service() -> SentenceTransformerEmbeddingService:
    return _get_embedding_service(get_analysis_settings().embedding_model)


@lru_cache(maxsize=1)
def _load_model(model_id: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_id)
