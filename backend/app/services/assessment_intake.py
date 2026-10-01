import csv
import io
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from app.schemas.assessment import (
    AssessmentMetadata,
    AssessmentPreview,
    AssessmentSummary,
    NormalizedResponse,
)

REQUIRED_COLUMNS = (
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
MAX_CSV_BYTES = 1_000_000
SAMPLE_SIZE = 5


class IntakeError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


@dataclass(frozen=True)
class ParsedAssessment:
    preview: AssessmentPreview
    responses: list[NormalizedResponse]


def parse_assessment_csv_full(
    content: bytes,
    *,
    filename: str,
    data_label: Literal["teacher_upload", "synthetic_demo"],
) -> ParsedAssessment:
    if not content:
        raise IntakeError("csv_empty", "The CSV file is empty.")
    if len(content) > MAX_CSV_BYTES:
        raise IntakeError("file_too_large", "The CSV file exceeds the 1 MB limit.", {"max_bytes": MAX_CSV_BYTES})

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise IntakeError("csv_encoding_error", "The CSV must use UTF-8 encoding.") from error
    if "\x00" in text:
        raise IntakeError("csv_malformed", "The CSV contains unsupported null characters.")

    try:
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        raw_headers = reader.fieldnames
        if raw_headers is None:
            raise IntakeError("csv_empty", "The CSV file is empty.")
        headers = [header.strip() for header in raw_headers]
        if len(headers) != len(set(headers)):
            raise IntakeError("csv_duplicate_columns", "The CSV contains duplicate column names.")
        reader.fieldnames = headers

        missing_columns = [column for column in REQUIRED_COLUMNS if column not in headers]
        if missing_columns:
            raise IntakeError(
                "csv_missing_columns",
                "The CSV is missing required columns.",
                {"missing_columns": missing_columns},
            )

        rows = list(reader)
    except csv.Error as error:
        raise IntakeError("csv_malformed", "The CSV could not be parsed.", {"reason": str(error)}) from error

    if not rows:
        raise IntakeError("csv_empty", "The CSV must contain at least one response row.")

    normalized: list[NormalizedResponse] = []
    assessment_values: tuple[str, str, str, str] | None = None
    question_values: dict[str, tuple[str, str]] = {}
    seen_response_keys: set[tuple[str, str]] = set()

    for row_index, row in enumerate(rows, start=2):
        _validate_row_shape(row, row_index)
        cleaned = {column: (row[column] or "").strip() for column in REQUIRED_COLUMNS if column != "answer"}
        answer = row["answer"] or ""
        empty_fields = [column for column, value in cleaned.items() if not value]
        if empty_fields:
            raise IntakeError(
                "csv_blank_required_value",
                f"Row {row_index} has blank required values.",
                {"row": row_index, "fields": empty_fields},
            )

        raw_correctness = cleaned["is_correct"].lower()
        if raw_correctness not in {"true", "false"}:
            raise IntakeError(
                "csv_invalid_correctness",
                f"Row {row_index} has an invalid is_correct value.",
                {"row": row_index, "value": cleaned["is_correct"]},
            )
        is_correct = raw_correctness == "true"
        if not answer.strip() and is_correct:
            raise IntakeError(
                "csv_invalid_correctness",
                f"Row {row_index} cannot mark a blank answer as correct.",
                {"row": row_index, "value": cleaned["is_correct"]},
            )

        current_assessment = (
            cleaned["assessment_title"],
            cleaned["subject"],
            cleaned["grade_level"],
            cleaned["topic"],
        )
        if assessment_values is None:
            assessment_values = current_assessment
        elif assessment_values != current_assessment:
            raise IntakeError(
                "csv_inconsistent_assessment",
                f"Row {row_index} does not match the assessment metadata in earlier rows.",
                {"row": row_index},
            )

        question_id = cleaned["question_id"]
        current_question = (cleaned["question"], cleaned["correct_answer"])
        if question_id in question_values and question_values[question_id] != current_question:
            raise IntakeError(
                "csv_inconsistent_question",
                f"Row {row_index} conflicts with the existing definition for question_id '{question_id}'.",
                {"row": row_index, "question_id": question_id},
            )
        question_values[question_id] = current_question

        response_key = (cleaned["student_id"], question_id)
        if response_key in seen_response_keys:
            raise IntakeError(
                "csv_duplicate_response",
                f"Row {row_index} duplicates a student/question response.",
                {"row": row_index, "student_id": response_key[0], "question_id": response_key[1]},
            )
        seen_response_keys.add(response_key)

        normalized.append(
            NormalizedResponse(
                row_number=row_index,
                student_id=cleaned["student_id"],
                question_id=question_id,
                question=cleaned["question"],
                answer=answer,
                correct_answer=cleaned["correct_answer"],
                answer_status="blank" if not answer.strip() else "answered",
                is_correct=is_correct,
            )
        )

    if assessment_values is None:
        raise IntakeError("csv_empty", "The CSV must contain at least one response row.")

    title, subject, grade_level, topic = assessment_values
    blank_count = sum(response.answer_status == "blank" for response in normalized)
    correct_count = sum(response.answer_status == "answered" and response.is_correct for response in normalized)
    preview = AssessmentPreview(
        status="validated",
        data_label=data_label,
        filename=filename,
        assessment=AssessmentMetadata(title=title, subject=subject, grade_level=grade_level, topic=topic),
        summary=AssessmentSummary(
            response_count=len(normalized),
            answered_count=len(normalized) - blank_count,
            blank_count=blank_count,
            student_count=len({response.student_id for response in normalized}),
            question_count=len(question_values),
            correct_count=correct_count,
            incorrect_count=len(normalized) - blank_count - correct_count,
        ),
        sample_responses=normalized[:SAMPLE_SIZE],
    )
    return ParsedAssessment(preview=preview, responses=normalized)


def parse_assessment_csv(
    content: bytes,
    *,
    filename: str,
    data_label: Literal["teacher_upload", "synthetic_demo"],
) -> AssessmentPreview:
    return parse_assessment_csv_full(content, filename=filename, data_label=data_label).preview


def _validate_row_shape(row: Mapping[str | None, str | list[str] | None], row_index: int) -> None:
    if None in row or any(value is None for key, value in row.items() if key is not None):
        raise IntakeError(
            "csv_malformed",
            f"Row {row_index} has a different number of values than the header.",
            {"row": row_index},
        )
