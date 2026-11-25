from collections.abc import AsyncGenerator, Callable, Coroutine
from io import BytesIO
import os
from typing import Any
from uuid import uuid4

from fastapi import Request, params
from fastapi.routing import APIRoute
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException
from starlette.formparsers import MultiPartException, MultiPartParser
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .services.assessment_intake import MAX_CSV_BYTES
from .services.material_ingestion import MAX_MATERIAL_BYTES
from .telemetry import log_error


def limit_response(status: int, code: str, message: str, **details: object) -> JSONResponse:
    log_error("request", code)
    return JSONResponse(
        status_code=status,
        content={"error": {
            "code": code, "message": message, "details": details,
            "retryable": False, "request_id": f"req_{uuid4().hex}",
        }},
    )


class RequestBodyLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.max_bytes = int(os.getenv("CLASSLENS_MAX_REQUEST_BYTES", str(2 * 1024 * 1024)))
        if self.max_bytes <= 0:
            raise ValueError("CLASSLENS_MAX_REQUEST_BYTES must be positive.")

    def too_large(self) -> Response:
        return limit_response(
            413, "request_body_too_large", "The request body exceeds the configured byte limit.",
            max_bytes=self.max_bytes,
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        lengths = Headers(scope=scope).getlist("content-length")
        if lengths:
            length = lengths[0].strip(" \t")
            if len(lengths) != 1 or not length.isascii() or not length.isdecimal():
                error = limit_response(400, "invalid_content_length", "Supply one nonnegative Content-Length.")
                await error(scope, receive, send)
                return
            # Compare decimal strings so arbitrary-length declarations never need integer conversion.
            length = length.lstrip("0") or "0"
            maximum = str(self.max_bytes)
            if (len(length), length) > (len(maximum), maximum):
                await self.too_large()(scope, receive, send)
                return

        # Admit the entire bounded body before JSON parsing or multipart file allocation.
        # BytesIO coalesces even one-byte ASGI frames without retaining a list of frames.
        with BytesIO() as buffer:
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                if buffer.tell() + len(chunk) > self.max_bytes:
                    await self.too_large()(scope, receive, send)
                    return
                buffer.write(chunk)
                if not message.get("more_body", False):
                    break
            pending: bytes | None = buffer.getvalue()
        del message, chunk

        async def replay() -> Message:
            nonlocal pending
            if pending is not None:
                body, pending = pending, None
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


class FileLimitExceeded(Exception):
    pass


class UploadParser(MultiPartParser):
    def __init__(self, request: Request, max_file_bytes: int) -> None:
        self.max_file_bytes = max_file_bytes
        self.file_bytes = 0
        self.complete = False
        super().__init__(request.headers, self.checked_stream(request.stream()), max_files=1, max_fields=4)

    async def checked_stream(self, source: AsyncGenerator[bytes, None]) -> AsyncGenerator[bytes, None]:
        async for chunk in source:
            yield chunk
        # python-multipart's finalize() accepts a partial final part. Raise inside
        # Starlette's parse loop so it closes even files in unfinished parts.
        if not self.complete:
            raise MultiPartException("Missing final multipart boundary.")

    def on_end(self) -> None:
        self.complete = True

    def on_part_data(self, data: bytes, start: int, end: int) -> None:
        if self._current_part.file is not None:
            self.file_bytes += end - start
            if self.file_bytes > self.max_file_bytes:
                raise FileLimitExceeded
        super().on_part_data(data, start, end)


class UploadRoute(APIRoute):
    max_file_bytes = MAX_CSV_BYTES
    file_error_code = "file_too_large"

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()
        if self.body_field is None or not isinstance(self.body_field.field_info, params.Form):
            return handler

        async def handle_upload(request: Request) -> Response:
            media_type = request.headers.get("content-type", "").partition(";")[0].strip().lower()
            try:
                if media_type == "multipart/form-data":
                    # FastAPI reads request.form() after this hook and registers
                    # its normal FormData.close cleanup. Share Starlette's cache
                    # so each file is parsed and allocated exactly once.
                    request._form = await UploadParser(request, self.max_file_bytes).parse()
                else:
                    await request.form(max_files=1, max_fields=4)
            except FileLimitExceeded:
                return limit_response(
                    413, self.file_error_code, "The uploaded file exceeds the byte limit.",
                    max_bytes=self.max_file_bytes,
                )
            except (MultiPartException, HTTPException):
                return limit_response(
                    400, "invalid_multipart",
                    "Provide a complete form with at most one file and four ordinary fields.",
                    max_files=1, max_fields=4,
                )
            return await handler(request)

        return handle_upload


class MaterialUploadRoute(UploadRoute):
    max_file_bytes = MAX_MATERIAL_BYTES
    file_error_code = "material_too_large"
