import asyncio

import httpx
import pytest
from fastapi import FastAPI, Request
from starlette import formparsers

from app.api.routes.assessments import DEMO_CSV_PATH
from app.main import app
from app.providers.embeddings import get_embedding_service
from conftest import run_test_async


def request(application, path, **kwargs):
    async def send():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://test"
        ) as client:
            return await client.post(path, **kwargs)

    return run_test_async(send())


def echo_app():
    application = FastAPI(middleware=app.user_middleware)

    @application.post("/")
    async def echo_size(request: Request):
        return len(await request.body())

    return application


def assert_error(response, status, code):
    assert response.status_code == status
    error = response.json()["error"]
    assert error["code"] == code
    assert error["retryable"] is False
    assert error["request_id"].startswith("req_")
    assert error["message"]
    return error["details"]


@pytest.mark.parametrize("declared", [None, "1"])
@pytest.mark.parametrize("extra", [0, 1])
def test_total_limit_uses_actual_stream_bytes(declared, extra):
    async def chunks():
        yield b" " * 2_097_151
        yield b"x" * (1 + extra)

    headers = {"Origin": "http://localhost:5173"}
    if declared is not None:
        headers["Content-Length"] = declared
    response = request(echo_app(), "/", content=chunks(), headers=headers)
    assert response.headers["access-control-allow-origin"] == headers["Origin"]
    if extra:
        details = assert_error(response, 413, "request_body_too_large")
        assert details["max_bytes"] == 2_097_152
    else:
        assert response.status_code == 200
        assert response.json() == 2_097_152


@pytest.mark.parametrize("declared", ["-1", "abc", "1, 2"])
def test_invalid_content_length_is_structured(declared):
    response = request(echo_app(), "/", content=b"x", headers={"Content-Length": declared})
    assert_error(response, 400, "invalid_content_length")


def test_declared_over_limit_rejected_without_reading(monkeypatch):
    monkeypatch.setenv("CLASSLENS_MAX_REQUEST_BYTES", "64")

    async def unread_body():
        pytest.fail("body should not be read when declared length exceeds the limit")
        yield b""

    response = request(echo_app(), "/", content=unread_body(), headers={"Content-Length": "65"})
    assert assert_error(response, 413, "request_body_too_large")["max_bytes"] == 64


def test_over_limit_multipart_never_reaches_parser_or_dependencies(monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("over-limit multipart reached parsing or route dependencies")

    monkeypatch.setattr(formparsers, "SpooledTemporaryFile", unexpected)
    monkeypatch.setitem(app.dependency_overrides, get_embedding_service, unexpected)
    multipart = httpx.Request("POST", "http://test/", files={"file": ("fixture.txt", b"x", "text/plain")})

    async def chunks():
        yield multipart.read()
        yield b" " * 2_097_152

    response = request(
        app, "/api/v1/learning-materials/ingest", content=chunks(),
        headers={"Content-Type": multipart.headers["content-type"]},
    )
    assert_error(response, 413, "request_body_too_large")


@pytest.mark.parametrize("path", [
    "/api/v1/assessments/preview", "/api/v1/assessments/analyze",
    "/api/v1/learning-materials/ingest", "/api/v1/results",
])
@pytest.mark.parametrize("extra", ["file", "fields"])
def test_multipart_part_limits_before_route_dependencies(monkeypatch, path, extra):
    async def unexpected():
        pytest.fail("rejected multipart reached an embedding dependency")

    monkeypatch.setitem(app.dependency_overrides, get_embedding_service, unexpected)
    parts = [("file", ("fixture.csv", b"", "text/csv"))]
    if extra == "file":
        parts.append(("extra", ("second.csv", b"", "text/csv")))
    else:
        parts.extend((f"field_{index}", (None, "x")) for index in range(5))
    assert_error(request(app, path, files=parts), 400, "invalid_multipart")


def test_malformed_multipart_error_is_structured():
    response = request(
        app, "/api/v1/assessments/preview", content=b"missing boundary",
        headers={"Content-Type": "multipart/form-data"},
    )
    assert_error(response, 400, "invalid_multipart")


@pytest.mark.parametrize("extra", [0, 1])
def test_one_file_and_four_fields_preserve_file_limit(extra):
    csv = DEMO_CSV_PATH.read_bytes()
    content = csv.ljust(1_000_000 + extra, b"\n")
    parts = [("file", ("fixture.csv", content, "text/csv"))]
    parts.extend((f"field_{index}", (None, "x")) for index in range(4))
    response = request(app, "/api/v1/assessments/preview", files=parts)
    if extra:
        assert_error(response, 413, "file_too_large")
    else:
        assert response.status_code == 200
        assert response.json()["summary"]["response_count"] == 45


@pytest.mark.parametrize("interruption", ["disconnect", "cancel"])
def test_incomplete_stream_never_enters_application(interruption):
    application = echo_app()
    signals = [{"type": "http.request", "body": b"abc", "more_body": True}]
    responses = []

    async def receive():
        if signals:
            return signals.pop()
        if interruption == "disconnect":
            return {"type": "http.disconnect"}
        raise asyncio.CancelledError

    async def send(message):
        responses.append(message)

    scope = {"type": "http", "method": "POST", "path": "/", "headers": [], "query_string": b""}
    if interruption == "cancel":
        with pytest.raises(asyncio.CancelledError):
            run_test_async(application(scope, receive, send))
    else:
        run_test_async(application(scope, receive, send))
    assert responses == []


def test_truncated_form_is_rejected_and_partial_files_are_closed(monkeypatch):
    opened = []
    create_file = formparsers.SpooledTemporaryFile

    def track_file(*args, **kwargs):
        file = create_file(*args, **kwargs)
        opened.append(file)
        return file

    monkeypatch.setattr(formparsers, "SpooledTemporaryFile", track_file)
    valid = httpx.Request(
        "POST", "http://test/",
        files=[("file", ("fixture.csv", DEMO_CSV_PATH.read_bytes())), ("title", (None, "fixture"))],
    )
    incomplete = valid.read().rsplit(b"\r\n--", 1)[0]
    response = request(
        app, "/api/v1/assessments/preview", content=incomplete,
        headers={"Content-Type": valid.headers["content-type"]},
    )
    assert_error(response, 400, "invalid_multipart")
    assert all(file.closed for file in opened)


@pytest.mark.parametrize(("path", "code"), [
    ("/api/v1/learning-materials/ingest", "material_too_large"),
    ("/api/v1/assessments/analyze", "file_too_large"),
])
def test_over_limit_file_rejected_before_disk_or_dependencies(monkeypatch, path, code):
    async def unexpected_dependency():
        pytest.fail("an over-limit file reached an embedding dependency")

    def unexpected_rollover(*args):
        pytest.fail("an over-limit file was spooled to disk")

    monkeypatch.setitem(app.dependency_overrides, get_embedding_service, unexpected_dependency)
    monkeypatch.setattr(formparsers.SpooledTemporaryFile, "rollover", unexpected_rollover)
    filename = "fixture.txt" if code == "material_too_large" else "fixture.csv"
    response = request(app, path, files={"file": (filename, b"x" * 1_100_000)})
    assert_error(response, 413, code)


def test_unframed_request_replays_exact_bytes_then_forwards_disconnect():
    application = FastAPI(middleware=app.user_middleware)

    @application.post("/")
    async def read_request(request: Request):
        assert await request.body() == b"\x00\xffbody"
        assert await request.receive() == {"type": "http.disconnect"}
        return "done"

    frames = iter([
        {"type": "http.request", "body": b"\x00", "more_body": True},
        {"type": "http.request", "body": b"\xffbody"},
        {"type": "http.disconnect"},
    ])
    response = []

    async def receive():
        return next(frames)

    async def send(message):
        response.append(message)

    scope = {"type": "http", "method": "POST", "path": "/", "headers": [], "query_string": b""}
    run_test_async(application(scope, receive, send))
    assert response[0]["status"] == 200


def test_over_limit_json_rejected_before_decoding(monkeypatch):
    async def unexpected_decode(*args):
        pytest.fail("over-limit JSON reached the decoder")

    monkeypatch.setattr(Request, "json", unexpected_decode)

    async def chunks():
        yield b" " * 2_097_152
        yield b"{"

    response = request(
        app, "/api/v1/remediations", content=chunks(), headers={"Content-Type": "application/json"},
    )
    assert_error(response, 413, "request_body_too_large")


def test_invalid_multipart_boundary_syntax_returns_structured_400():
    response = request(
        app, "/api/v1/assessments/preview", content=b"invalid multipart bytes",
        headers={"Content-Type": "multipart/form-data; boundary=classlens"},
    )
    assert_error(response, 400, "invalid_multipart")
