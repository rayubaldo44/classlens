from typing import Literal

from pydantic import BaseModel, Field, model_validator


class MaterialChunk(BaseModel):
    chunk_id: str
    chunk_index: int
    text: str
    start_char: int
    end_char: int


class LearningMaterial(BaseModel):
    material_id: str
    title: str
    filename: str
    source_kind: Literal["teacher_upload", "synthetic_demo"]
    content_hash: str
    chunk_count: int
    chunk_size_chars: int
    chunk_overlap_chars: int
    embedding_model: str
    embedding_dimension: int


class MaterialIngestionResponse(BaseModel):
    status: Literal["ready"]
    material: LearningMaterial
    message: str


class MisconceptionRetrievalContext(BaseModel):
    analysis_id: str = Field(min_length=1, max_length=100)
    group_id: str = Field(min_length=1, max_length=100)
    question_id: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=1, max_length=2000)
    correct_answer: str = Field(min_length=1, max_length=4000)
    representative_answers: list[str] = Field(min_length=1)


class RetrievedChunk(BaseModel):
    chunk_id: str
    chunk_index: int
    text: str
    similarity: float
    start_char: int
    end_char: int


class RetrievalMetadata(BaseModel):
    algorithm: Literal["cosine_similarity_v1"]
    top_k: int
    minimum_relevance_score: float
    embedding_model: str


class MaterialRetrievalResponse(BaseModel):
    status: Literal["retrieved", "insufficient_relevant_context"]
    group_id: str
    source_group_ids: list[str] = Field(default_factory=list)
    material: LearningMaterial
    retrieval: RetrievalMetadata
    results: list[RetrievedChunk]
    message: str | None = None

    @model_validator(mode="after")
    def default_source_group_ids(self):
        if not self.source_group_ids:
            self.source_group_ids = [self.group_id]
        return self
