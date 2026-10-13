"""Run a small live grounded-generation evaluation without persisting drafts."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
from time import perf_counter
from typing import Any

from app.config import get_llm_settings
from app.prompts.remediation import build_remediation_prompt
from app.providers.llm import GeminiLLMService, LLMProviderError
from app.schemas.remediations import RemediationGenerationRequest
from app.services.remediation import RemediationError, _validate_draft


DEFAULT_CASES = Path(__file__).with_name("generation_evaluation_cases.json")


class _TelemetryCapture(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def _fields(message: str) -> dict[str, str]:
    return dict(item.split("=", 1) for item in message.split() if "=" in item)


async def _close_service(service: GeminiLLMService) -> None:
    client = service._client
    if client is not None:
        await client.aio.aclose()
        client.close()


def _claim_review_complete(generated: list[dict[str, Any]], *, expected_count: int) -> bool:
    return len(generated) == expected_count and all(
        case.get("claim_support_review") == "approved" for case in generated
    )


async def _run_case(
    case: dict[str, Any], service: GeminiLLMService, capture: _TelemetryCapture
) -> dict[str, Any]:
    request = RemediationGenerationRequest.model_validate(case["request"])
    prompt = build_remediation_prompt(request)
    before = len(capture.messages)
    started = perf_counter()
    try:
        draft = await service.generate_remediation(prompt)
        elapsed = perf_counter() - started
        allowed_ids = {item.chunk_id for item in request.retrieval.results}
        try:
            _validate_draft(draft, allowed_source_ids=allowed_ids)
            citations_valid = True
            citation_error = None
        except RemediationError as error:
            citations_valid = False
            citation_error = error.code
        rendered = json.dumps(draft.model_dump(), ensure_ascii=False).lower()
        canaries = [value.lower() for value in case.get("forbidden_output_canaries", [])]
        telemetry = next(
            (
                _fields(message)
                for message in reversed(capture.messages[before:])
                if "stage_timing stage=gemini_call" in message
            ),
            {},
        )
        return {
            "id": case["id"],
            "status": "generated",
            "elapsed_seconds": round(elapsed, 3),
            "prompt_tokens": int(telemetry["prompt_tokens"]) if telemetry.get("prompt_tokens") else None,
            "output_tokens": int(telemetry["output_tokens"]) if telemetry.get("output_tokens") else None,
            "total_tokens": int(telemetry["total_tokens"]) if telemetry.get("total_tokens") else None,
            "schema_valid": True,
            "citations_valid": citations_valid,
            "citation_error": citation_error,
            "injection_canary_absent": not any(canary in rendered for canary in canaries),
            "claim_support_review": "pending_human_review",
            "draft": draft.model_dump(),
        }
    except LLMProviderError as error:
        return {
            "id": case["id"],
            "status": "provider_error",
            "elapsed_seconds": round(perf_counter() - started, 3),
            "error_code": error.code,
            "retryable": error.retryable,
        }


async def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    suite = json.loads(args.cases.read_text())
    settings = get_llm_settings()
    service = GeminiLLMService(
        api_key=settings.api_key,
        model_id=settings.model,
        timeout_ms=settings.timeout_ms,
        total_budget_ms=settings.total_budget_ms,
    )
    capture = _TelemetryCapture()
    telemetry_logger = logging.getLogger("classlens.telemetry")
    telemetry_logger.addHandler(capture)
    telemetry_logger.setLevel(logging.INFO)
    try:
        cases = [await _run_case(case, service, capture) for case in suite["cases"]]
        unavailable = GeminiLLMService(
            api_key="",
            model_id=settings.model,
            timeout_ms=settings.timeout_ms,
            total_budget_ms=settings.total_budget_ms,
        )
        try:
            await unavailable.generate_remediation("synthetic availability probe")
            unavailable_result = {"passed": False, "error_code": None}
        except LLMProviderError as error:
            unavailable_result = {
                "passed": error.code == "llm_not_configured" and not error.retryable,
                "error_code": error.code,
                "retryable": error.retryable,
            }
    finally:
        telemetry_logger.removeHandler(capture)
        await _close_service(service)

    generated = [case for case in cases if case["status"] == "generated"]
    report = {
        "provider": service.provider_name,
        "model": service.model_id,
        "case_count": len(cases),
        "generated_count": len(generated),
        "automated_checks_passed": all(
            case["schema_valid"] and case["citations_valid"] and case["injection_canary_absent"]
            for case in generated
        )
        and len(generated) == len(cases)
        and unavailable_result["passed"],
        "claim_support_review_complete": _claim_review_complete(
            generated, expected_count=len(cases)
        ),
        "provider_unavailable_check": unavailable_result,
        "cases": cases,
    }
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered)
    print(rendered, end="", flush=True)
    return 0 if report["automated_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
