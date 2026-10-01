import asyncio
from pathlib import Path

import httpx

from app.main import app

DEMO_CSV = Path(__file__).resolve().parents[2] / "data" / "demo" / "photosynthesis_responses.csv"
HEADER = (
    "assessment_title,subject,grade_level,topic,student_id,question_id,question,answer,"
    "correct_answer,is_correct\n"
)


def request(method: str, path: str, **kwargs: object) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send())


def upload(content: bytes, filename: str = "responses.csv") -> httpx.Response:
    return request("POST", "/api/v1/assessments/preview", files={"file": (filename, content, "text/csv")})


def test_demo_csv_returns_deterministic_normalized_preview() -> None:
    response = upload(DEMO_CSV.read_bytes())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "validated"
    assert body["assessment"] == {
        "title": "Photosynthesis Free-Response Check",
        "subject": "Science",
        "grade_level": "7",
        "topic": "Photosynthesis",
    }
    assert body["summary"] == {
        "response_count": 45,
        "answered_count": 43,
        "blank_count": 2,
        "correct_count": 14,
        "incorrect_count": 29,
        "student_count": 45,
        "question_count": 1,
    }
    assert len(body["sample_responses"]) == 5
    assert body["sample_responses"][0]["student_id"] == "S001"


def test_demo_preview_endpoint_uses_same_fixture() -> None:
    response = request("GET", "/api/v1/assessments/demo/photosynthesis/preview")

    assert response.status_code == 200
    assert response.json()["data_label"] == "synthetic_demo"
    assert response.json()["summary"]["response_count"] == 45


def test_missing_required_columns_returns_actionable_error() -> None:
    response = upload(b"student_id,answer\nS001,Plants eat sunlight.\n")

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "csv_missing_columns"
    assert "question_id" in error["details"]["missing_columns"]
    assert error["retryable"] is False
    assert error["request_id"].startswith("req_")


def test_header_only_csv_is_rejected_as_empty() -> None:
    response = upload(HEADER.encode())

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "csv_empty"


def test_zero_byte_csv_is_rejected_as_empty() -> None:
    response = upload(b"")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "csv_empty"


def test_malformed_csv_returns_useful_error() -> None:
    malformed = HEADER + 'Demo,Science,7,Photosynthesis,S001,Q1,Question,"unterminated,Correct answer,false\n'
    response = upload(malformed.encode())

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "csv_malformed"


def test_blank_answer_is_preserved_and_counted() -> None:
    content = HEADER + "Demo,Science,7,Photosynthesis,S001,Q1,Question,   ,Correct answer,false\n"
    response = upload(content.encode())

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["blank_count"] == 1
    assert body["sample_responses"][0]["answer"] == "   "
    assert body["sample_responses"][0]["answer_status"] == "blank"


def test_non_csv_extension_is_rejected() -> None:
    response = upload(DEMO_CSV.read_bytes(), filename="responses.txt")

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_file_type"


def test_duplicate_student_question_response_is_rejected() -> None:
    row = "Demo,Science,7,Photosynthesis,S001,Q1,Question,Answer,Correct answer,false\n"
    response = upload((HEADER + row + row).encode())

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "csv_duplicate_response"


def test_invalid_correctness_value_is_rejected() -> None:
    row = "Demo,Science,7,Photosynthesis,S001,Q1,Question,Answer,Correct answer,yes\n"
    response = upload((HEADER + row).encode())

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "csv_invalid_correctness"


def test_blank_answer_cannot_be_marked_correct() -> None:
    row = "Demo,Science,7,Photosynthesis,S001,Q1,Question,   ,Correct answer,true\n"
    response = upload((HEADER + row).encode())

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "csv_invalid_correctness"
