"""Run the curated real-embedding regression suite against production services."""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any

from app.config import AnalysisSettings, MaterialSettings
from app.providers.embeddings.sentence_transformer import SentenceTransformerEmbeddingService
from app.providers.material_index import InMemoryMaterialIndex
from app.schemas.materials import MisconceptionRetrievalContext
from app.services.assessment_intake import parse_assessment_csv_full
from app.services.material_ingestion import ingest_learning_material
from app.services.material_retrieval import retrieve_for_misconception
from app.services.misconception_analysis import analyze_assessment


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASES = Path(__file__).with_name("embedding_regression_cases.json")
CSV_FIELDS = (
    "assessment_title",
    "subject",
    "grade_level",
    "topic",
    "student_id",
    "question_id",
    "question",
    "answer",
    "correct_answer",
    "is_correct",
)


def _assessment_bytes(case: dict[str, Any]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
    writer.writeheader()
    metadata = case["assessment"]
    for response in case["responses"]:
        writer.writerow({**metadata, **response})
    return output.getvalue().encode()


def _pairs(groups: list[set[str]]) -> set[tuple[str, str]]:
    return {
        tuple(sorted((left, right)))
        for group in groups
        for position, left in enumerate(sorted(group))
        for right in sorted(group)[position + 1 :]
    }


def _score(expected_groups: list[set[str]], actual_groups: list[set[str]]) -> dict[str, float]:
    expected, actual = _pairs(expected_groups), _pairs(actual_groups)
    true_positive = len(expected & actual)
    precision = true_positive / len(actual) if actual else float(not expected)
    recall = true_positive / len(expected) if expected else float(not actual)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"pair_precision": precision, "pair_recall": recall, "pair_f1": f1}


def _evaluate_case(
    case: dict[str, Any],
    embedding_service: SentenceTransformerEmbeddingService,
    repeats: int,
) -> dict[str, Any]:
    parsed = parse_assessment_csv_full(
        _assessment_bytes(case), filename=f"{case['id']}.csv", data_label="synthetic_demo"
    )
    analysis_settings = AnalysisSettings(
        embedding_model=embedding_service.model_id,
        similarity_threshold=case.get("similarity_threshold", 0.70),
        min_group_size=case.get("minimum_support", 3),
    )
    runs = []
    durations = []
    for _ in range(repeats):
        started = perf_counter()
        result = analyze_assessment(parsed, embedding_service, analysis_settings)
        durations.append(perf_counter() - started)
        runs.append(result)

    expected_groups = [set(group) for group in case["expected_groups"]]
    actual_groups = [set(group.member_student_ids) for group in runs[0].groups]
    eligible_ids = {
        response.student_id
        for response in parsed.responses
        if response.answer_status == "answered" and not response.is_correct
    }
    expected_outliers = set(case["expected_outliers"])
    actual_outliers = eligible_ids - set().union(*actual_groups) if actual_groups else eligible_ids
    stable = all(
        {frozenset(group.member_student_ids) for group in run.groups}
        == {frozenset(group) for group in actual_groups}
        for run in runs[1:]
    )

    material_settings = MaterialSettings(
        chunk_size_chars=case.get("chunk_size_chars", 360),
        chunk_overlap_chars=case.get("chunk_overlap_chars", 40),
        retrieval_top_k=case.get("retrieval_top_k", 3),
        minimum_relevance_score=case.get("minimum_relevance_score", 0.42),
    )
    index = InMemoryMaterialIndex()
    material = ingest_learning_material(
        case["material"].encode(),
        filename=f"{case['id']}.txt",
        title=case["assessment"]["topic"],
        source_kind="synthetic_demo",
        embedding_service=embedding_service,
        material_index=index,
        settings=material_settings,
    ).material
    retrieval_checks = []
    for check in case["retrieval_checks"]:
        result = retrieve_for_misconception(
            material.material_id,
            MisconceptionRetrievalContext(
                group_id=f"eval_{case['id']}",
                question_id=case["assessment"]["question_id"],
                question=case["assessment"]["question"],
                correct_answer=case["assessment"]["correct_answer"],
                representative_answers=check["representative_answers"],
            ),
            embedding_service=embedding_service,
            material_index=index,
            settings=material_settings,
        )
        combined = " ".join(chunk.text for chunk in result.results).lower()
        retrieval_checks.append(
            {
                "name": check["name"],
                "passed": check["expected_text"].lower() in combined,
                "top_scores": [chunk.similarity for chunk in result.results],
            }
        )

    scores = _score(expected_groups, actual_groups)
    outlier_recall = (
        len(expected_outliers & actual_outliers) / len(expected_outliers)
        if expected_outliers
        else float(not actual_outliers)
    )
    quality = case["quality_gates"]
    passed = (
        scores["pair_f1"] >= quality["minimum_pair_f1"]
        and outlier_recall >= quality["minimum_outlier_recall"]
        and all(check["passed"] for check in retrieval_checks)
        and stable
    )
    return {
        "id": case["id"],
        "review": case["review"],
        **scores,
        "outlier_precision": len(expected_outliers & actual_outliers) / len(actual_outliers) if actual_outliers else float(not expected_outliers),
        "outlier_recall": outlier_recall,
        "expected_groups": [sorted(group) for group in expected_groups],
        "actual_groups": [sorted(group) for group in actual_groups],
        "expected_outliers": sorted(expected_outliers),
        "actual_outliers": sorted(actual_outliers),
        "stable": stable,
        "quality_gates": quality,
        "passed": passed,
        "run_seconds": [round(duration, 3) for duration in durations],
        "retrieval_checks": retrieval_checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repeats", type=int, default=2)
    args = parser.parse_args()
    if args.repeats < 2:
        parser.error("--repeats must be at least 2 to measure stability")

    suite = json.loads(args.cases.read_text())
    service = SentenceTransformerEmbeddingService(suite["model_id"], suite["model_revision"])
    results = [_evaluate_case(case, service, args.repeats) for case in suite["cases"]]
    approved = [result for result in results if result["review"]["status"] == "approved"]
    regression_passed = all(result["passed"] for result in approved)
    report = {
        "model_id": suite["model_id"],
        "model_revision": suite["model_revision"],
        "case_count": len(results),
        "teacher_reviewed_case_count": len(approved),
        "review_complete": len(approved) == len(results),
        "regression_passed": regression_passed if len(approved) == len(results) else False,
        "summary": {
            "mean_pair_f1": round(mean(result["pair_f1"] for result in results), 4),
            "mean_outlier_recall": round(mean(result["outlier_recall"] for result in results), 4),
            "retrieval_checks_passed": sum(
                check["passed"] for result in results for check in result["retrieval_checks"]
            ),
            "retrieval_check_count": sum(len(result["retrieval_checks"]) for result in results),
            "stable_case_count": sum(result["stable"] for result in results),
        },
        "cases": results,
    }
    rendered = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered)
    print(rendered, end="")
    if not report["review_complete"]:
        return 2
    return 0 if report["regression_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
