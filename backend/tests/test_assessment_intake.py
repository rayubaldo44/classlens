from pathlib import Path

import httpx
from conftest import run_test_async

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

    return run_test_async(send())


def upload(content: bytes, filename: str = "responses.csv") -> httpx.Response:
    return request("POST", "/api/v1/assessments/preview", files={"file": (filename, content, "text/csv")})


def make_incorrect_response_csv(response_count: int, *, question_count: int) -> bytes:
    rows = []
    for index in range(response_count):
        question_number = index % question_count + 1
        rows.append(
            "Demo,Science,7,Photosynthesis,"
            f"S{index + 1:04d},Q{question_number},Question {question_number},"
            f"Incorrect answer {index + 1},Correct answer {question_number},false\n"
        )
    return (HEADER + "".join(rows)).encode()


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


def test_exact_csv_and_question_limits_are_accepted() -> None:
    response = upload(make_incorrect_response_csv(500, question_count=5))

    assert response.status_code == 200
    assert response.json()["summary"] == {
        "response_count": 500,
        "answered_count": 500,
        "blank_count": 0,
        "correct_count": 0,
        "incorrect_count": 500,
        "student_count": 500,
        "question_count": 5,
    }


def test_csv_above_row_limit_returns_actionable_error() -> None:
    response = upload(make_incorrect_response_csv(501, question_count=6))

    assert response.status_code == 413
    error = response.json()["error"]
    assert error["code"] == "csv_row_limit_exceeded"
    assert error["details"] == {"actual_rows": 501, "max_rows": 500}
    assert error["retryable"] is False


def test_question_above_eligible_response_limit_returns_actionable_error() -> None:
    response = upload(make_incorrect_response_csv(101, question_count=1))

    assert response.status_code == 413
    error = response.json()["error"]
    assert error["code"] == "csv_question_eligible_limit_exceeded"
    assert error["details"] == {
        "question_id": "Q1",
        "actual_eligible_responses": 101,
        "max_eligible_responses": 100,
    }
    assert error["retryable"] is False


def test_correct_and_blank_answers_do_not_count_toward_question_eligible_limit() -> None:
    content = make_incorrect_response_csv(100, question_count=1).decode()
    content += "Demo,Science,7,Photosynthesis,S0101,Q1,Question 1,Correct answer 1,Correct answer 1,true\n"
    content += "Demo,Science,7,Photosynthesis,S0102,Q1,Question 1,   ,Correct answer 1,false\n"

    response = upload(content.encode())

    assert response.status_code == 200
    assert response.json()["summary"] == {
        "response_count": 102,
        "answered_count": 101,
        "blank_count": 1,
        "correct_count": 1,
        "incorrect_count": 100,
        "student_count": 102,
        "question_count": 1,
    }
