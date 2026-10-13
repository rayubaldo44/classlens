from collections import defaultdict
from time import perf_counter
import hashlib
import json
import math

from app.config import AnalysisSettings
from app.providers.embeddings import EmbeddingService
from app.schemas.analysis import (
    AnalysisResponse,
    AnalysisSummary,
    EmbeddingMetadata,
    GroupingMetadata,
    MisconceptionGroup,
    RepresentativeResponse,
)
from app.schemas.assessment import NormalizedResponse
from app.services.assessment_intake import ParsedAssessment
from app.telemetry import log_error, log_stage

REPRESENTATIVE_LIMIT = 3


class AnalysisError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details or {}


def analyze_assessment(
    parsed: ParsedAssessment,
    embedding_service: EmbeddingService,
    settings: AnalysisSettings,
) -> AnalysisResponse:
    eligible = [
        response
        for response in parsed.responses
        if response.answer_status == "answered" and not response.is_correct
    ]
    analysis_id = _analysis_id(parsed, embedding_service.model_id, settings)
    grouping_metadata = GroupingMetadata(
        algorithm="complete_link_cosine_v1",
        similarity_threshold=settings.similarity_threshold,
        minimum_support=settings.min_group_size,
    )

    if len(eligible) < settings.min_group_size:
        return _response(
            parsed=parsed,
            analysis_id=analysis_id,
            eligible_count=len(eligible),
            groups=[],
            embedding=EmbeddingMetadata(
                model_id=embedding_service.model_id,
                dimension=0,
                preprocessing="answer_only_v1",
            ),
            grouping=grouping_metadata,
            message="Too few eligible incorrect responses to identify a recurring pattern.",
        )

    started = perf_counter()
    try:
        vectors = embedding_service.embed([response.answer for response in eligible])
    except Exception as error:
        log_error("embedding", "embedding_failed", provider_error=type(error).__name__, item_count=len(eligible))
        raise AnalysisError(
            "embedding_failed",
            "Response embeddings could not be generated.",
            retryable=True,
            details={"provider_error": type(error).__name__},
        ) from error
    log_stage("embedding", (perf_counter() - started) * 1000, item_count=len(eligible), model=embedding_service.model_id)

    started = perf_counter()
    normalized_vectors = _validate_and_normalize_vectors(vectors, len(eligible))
    dimension = len(normalized_vectors[0])
    by_question: dict[str, list[int]] = defaultdict(list)
    for index, response in enumerate(eligible):
        by_question[response.question_id].append(index)

    group_candidates: list[tuple[list[int], float]] = []
    for question_indices in by_question.values():
        if len(question_indices) < settings.min_group_size:
            continue
        similarities = _pairwise_similarities(normalized_vectors, question_indices)
        clusters = _complete_link_clusters(question_indices, similarities, settings.similarity_threshold)
        for cluster in clusters:
            if len(cluster) >= settings.min_group_size:
                group_candidates.append((cluster, _coherence(cluster, similarities)))

    group_candidates.sort(
        key=lambda item: (-len(item[0]), [eligible[index].student_id for index in sorted(item[0])])
    )
    groups = [
        _build_group(position + 1, cluster, coherence, eligible, normalized_vectors)
        for position, (cluster, coherence) in enumerate(group_candidates)
    ]
    log_stage("grouping", (perf_counter() - started) * 1000, eligible_count=len(eligible), group_count=len(groups))
    message = None if groups else "No recurring misconception pattern met the configured evidence threshold."
    return _response(
        parsed=parsed,
        analysis_id=analysis_id,
        eligible_count=len(eligible),
        groups=groups,
        embedding=EmbeddingMetadata(
            model_id=embedding_service.model_id,
            dimension=dimension,
            preprocessing="answer_only_v1",
        ),
        grouping=grouping_metadata,
        message=message,
    )


def _response(
    *,
    parsed: ParsedAssessment,
    analysis_id: str,
    eligible_count: int,
    groups: list[MisconceptionGroup],
    embedding: EmbeddingMetadata,
    grouping: GroupingMetadata,
    message: str | None,
) -> AnalysisResponse:
    grouped_count = sum(group.support_count for group in groups)
    summary = parsed.preview.summary
    return AnalysisResponse(
        assessment_id=_assessment_id(parsed),
        analysis_id=analysis_id,
        status="completed" if groups else "insufficient_data",
        data_label=parsed.preview.data_label,
        filename=parsed.preview.filename,
        assessment=parsed.preview.assessment,
        summary=AnalysisSummary(
            response_count=summary.response_count,
            answered_count=summary.answered_count,
            blank_count=summary.blank_count,
            correct_count=summary.correct_count,
            eligible_incorrect_count=eligible_count,
            grouped_response_count=grouped_count,
            outlier_count=eligible_count - grouped_count,
            question_count=summary.question_count,
            group_count=len(groups),
        ),
        embedding=embedding,
        grouping=grouping,
        groups=groups,
        message=message,
    )


def _validate_and_normalize_vectors(vectors: list[list[float]], expected_count: int) -> list[list[float]]:
    if len(vectors) != expected_count or not vectors:
        raise AnalysisError(
            "embedding_invalid_response",
            "The embedding provider returned the wrong number of vectors.",
            retryable=True,
            details={"expected": expected_count, "received": len(vectors)},
        )
    dimension = len(vectors[0])
    if dimension == 0 or any(len(vector) != dimension for vector in vectors):
        raise AnalysisError(
            "embedding_invalid_response",
            "The embedding provider returned inconsistent vector dimensions.",
            retryable=True,
        )

    normalized: list[list[float]] = []
    for vector in vectors:
        if any(not math.isfinite(value) for value in vector):
            raise AnalysisError(
                "embedding_invalid_response",
                "The embedding provider returned non-finite values.",
                retryable=True,
            )
        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            raise AnalysisError(
                "embedding_invalid_response",
                "The embedding provider returned a zero-length vector.",
                retryable=True,
            )
        normalized.append([value / magnitude for value in vector])
    return normalized


def _pairwise_similarities(vectors: list[list[float]], indices: list[int]) -> dict[tuple[int, int], float]:
    similarities: dict[tuple[int, int], float] = {}
    for position, left in enumerate(indices):
        for right in indices[position + 1 :]:
            similarities[(min(left, right), max(left, right))] = sum(
                a * b for a, b in zip(vectors[left], vectors[right], strict=True)
            )
    return similarities


def _similarity(left: int, right: int, similarities: dict[tuple[int, int], float]) -> float:
    return 1.0 if left == right else similarities[(min(left, right), max(left, right))]


def _complete_link_clusters(
    indices: list[int],
    similarities: dict[tuple[int, int], float],
    threshold: float,
) -> list[list[int]]:
    clusters = [[index] for index in indices]
    while True:
        best: tuple[float, int, int] | None = None
        for left_index in range(len(clusters)):
            for right_index in range(left_index + 1, len(clusters)):
                complete_link = min(
                    _similarity(left, right, similarities)
                    for left in clusters[left_index]
                    for right in clusters[right_index]
                )
                candidate = (complete_link, -left_index, -right_index)
                if complete_link >= threshold and (best is None or candidate > best):
                    best = candidate
        if best is None:
            break
        left_index, right_index = -best[1], -best[2]
        clusters[left_index] = sorted(clusters[left_index] + clusters[right_index])
        del clusters[right_index]
    return clusters


def _coherence(cluster: list[int], similarities: dict[tuple[int, int], float]) -> float:
    scores = [
        _similarity(left, right, similarities)
        for position, left in enumerate(cluster)
        for right in cluster[position + 1 :]
    ]
    return round(sum(scores) / len(scores), 4) if scores else 1.0


def _build_group(
    position: int,
    cluster: list[int],
    coherence: float,
    responses: list[NormalizedResponse],
    vectors: list[list[float]],
) -> MisconceptionGroup:
    member_scores = {
        index: sum(
            sum(a * b for a, b in zip(vectors[index], vectors[other], strict=True))
            for other in cluster
            if other != index
        )
        / (len(cluster) - 1)
        for index in cluster
    }
    medoid = max(cluster, key=lambda index: (member_scores[index], responses[index].student_id))
    representatives = sorted(
        cluster,
        key=lambda index: (
            -sum(a * b for a, b in zip(vectors[index], vectors[medoid], strict=True)),
            responses[index].student_id,
        ),
    )[:REPRESENTATIVE_LIMIT]
    question = responses[cluster[0]]
    member_ids = sorted(responses[index].student_id for index in cluster)
    group_hash = hashlib.sha256(
        f"{question.question_id}:{','.join(member_ids)}".encode()
    ).hexdigest()[:12]
    return MisconceptionGroup(
        group_id=f"grp_{group_hash}",
        provisional_label=f"Potential misconception pattern {position}",
        interpretation_status="not_requested",
        question_id=question.question_id,
        question=question.question,
        correct_answer=question.correct_answer,
        support_count=len(cluster),
        eligible_response_count=sum(response.question_id == question.question_id for response in responses),
        member_student_ids=member_ids,
        representative_responses=[
            RepresentativeResponse(
                student_id=responses[index].student_id,
                answer=responses[index].answer,
                similarity_to_medoid=round(
                    sum(a * b for a, b in zip(vectors[index], vectors[medoid], strict=True)),
                    4,
                ),
            )
            for index in representatives
        ],
        coherence=coherence,
    )


def _analysis_id(parsed: ParsedAssessment, model_id: str, settings: AnalysisSettings) -> str:
    payload = {
        "data_label": parsed.preview.data_label,
        "model": model_id,
        "threshold": settings.similarity_threshold,
        "minimum_support": settings.min_group_size,
        "assessment": parsed.preview.assessment.model_dump(),
        "responses": [response.model_dump() for response in parsed.responses],
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
    return f"analysis_{digest}"


def _assessment_id(parsed: ParsedAssessment) -> str:
    payload = {
        "data_label": parsed.preview.data_label,
        "assessment": parsed.preview.assessment.model_dump(),
        "responses": [response.model_dump() for response in parsed.responses],
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
    return f"assessment_{digest}"
