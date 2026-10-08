from functools import lru_cache

from app.config import DEFAULT_EMBEDDING_REVISION, get_analysis_settings


class SentenceTransformerEmbeddingService:
    def __init__(self, model_id: str, revision: str = DEFAULT_EMBEDDING_REVISION) -> None:
        self._model_id = model_id
        self._revision = revision

    @property
    def model_id(self) -> str:
        return self._model_id

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = _load_model(self._model_id, self._revision).encode(
            texts,
            batch_size=32,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.tolist()


@lru_cache(maxsize=1)
def _get_embedding_service(model_id: str, revision: str) -> SentenceTransformerEmbeddingService:
    return SentenceTransformerEmbeddingService(model_id, revision)


async def get_embedding_service() -> SentenceTransformerEmbeddingService:
    settings = get_analysis_settings()
    return _get_embedding_service(settings.embedding_model, settings.embedding_revision)


@lru_cache(maxsize=1)
def _load_model(model_id: str, revision: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_id, revision=revision)


def embedding_model_loaded() -> bool:
    return _load_model.cache_info().currsize > 0
