import asyncio
from time import perf_counter

from pydantic import ValidationError

from app.config import get_llm_settings
from app.schemas.remediations import GeneratedRemediationDraft

from .base import LLMProviderError
from app.telemetry import log_error, log_stage


MAX_PROVIDER_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 0.75
TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


class GeminiLLMService:
    provider_name = "google-gemini"

    def __init__(
        self,
        *,
        api_key: str,
        model_id: str,
        timeout_ms: int,
        total_budget_ms: int = 60_000,
    ) -> None:
        self._api_key = api_key
        self._model_id = model_id
        self._timeout_ms = timeout_ms
        self._total_budget_ms = total_budget_ms
        self._types = None
        self._client = None

    @property
    def model_id(self) -> str:
        return self._model_id

    async def generate_remediation(self, prompt: str) -> GeneratedRemediationDraft:
        if not self._api_key:
            raise LLMProviderError(
                "llm_not_configured",
                "Gemini is not configured. Add GEMINI_API_KEY to backend/.env and restart the API.",
                retryable=False,
            )
        if self._client is None:
            from google import genai
            from google.genai import types

            self._types = types
            self._client = genai.Client(
                api_key=self._api_key,
                http_options=types.HttpOptions(timeout=self._timeout_ms),
            )

        try:
            async with asyncio.timeout(self._total_budget_ms / 1000):
                return await self._generate_with_retries(prompt)
        except TimeoutError as error:
            raise LLMProviderError(
                "llm_timeout",
                "Gemini did not respond within the total generation time budget. Try again.",
                retryable=True,
            ) from error

    async def _generate_with_retries(self, prompt: str) -> GeneratedRemediationDraft:
        response = None
        for attempt in range(MAX_PROVIDER_ATTEMPTS):
            started = perf_counter()
            try:
                response = await self._client.aio.models.generate_content(
                    model=self._model_id,
                    contents=prompt,
                    config=self._types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_json_schema=_gemini_json_schema(),
                        temperature=0.2,
                        max_output_tokens=2200,
                    ),
                )
                usage = getattr(response, "usage_metadata", None)
                log_stage(
                    "gemini_call",
                    (perf_counter() - started) * 1000,
                    model=self._model_id,
                    attempt=attempt + 1,
                    prompt_tokens=getattr(usage, "prompt_token_count", None),
                    output_tokens=getattr(usage, "candidates_token_count", None),
                    total_tokens=getattr(usage, "total_token_count", None),
                )
                break
            except Exception as error:
                log_error("gemini_call", "llm_provider_error", model=self._model_id, attempt=attempt + 1, error_type=type(error).__name__)
                log_stage("gemini_call", (perf_counter() - started) * 1000, model=self._model_id, attempt=attempt + 1, status="error")
                retryable = _is_retryable_provider_error(error)
                if retryable and attempt + 1 < MAX_PROVIDER_ATTEMPTS:
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                    continue
                if _is_timeout(error):
                    raise LLMProviderError(
                        "llm_timeout",
                        "Gemini did not respond before the generation timeout. Try again.",
                        retryable=True,
                    ) from error
                raise LLMProviderError(
                    "llm_provider_unavailable",
                    "Gemini could not generate the intervention. Check the provider configuration and try again.",
                    retryable=retryable,
                ) from error

        if response is None:  # Defensive: every loop path either returns a response or raises.
            raise LLMProviderError(
                "llm_provider_unavailable",
                "Gemini could not generate the intervention. Check the provider configuration and try again.",
                retryable=True,
            )

        try:
            if isinstance(response.parsed, GeneratedRemediationDraft):
                return response.parsed
            if not response.text:
                raise ValueError("empty model output")
            return GeneratedRemediationDraft.model_validate_json(response.text)
        except (ValidationError, ValueError, TypeError) as error:
            raise LLMProviderError(
                "llm_malformed_output",
                "Gemini returned an invalid intervention structure. No remediation was saved.",
                retryable=True,
            ) from error


async def get_llm_service() -> GeminiLLMService:
    settings = get_llm_settings()
    return GeminiLLMService(
        api_key=settings.api_key,
        model_id=settings.model,
        timeout_ms=settings.timeout_ms,
        total_budget_ms=settings.total_budget_ms,
    )


def _gemini_json_schema() -> dict:
    """Return Pydantic's schema without metadata rejected by Gemini's schema endpoint."""
    return _remove_unsupported_schema_fields(GeneratedRemediationDraft.model_json_schema())


def _is_timeout(error: Exception) -> bool:
    return "timeout" in type(error).__name__.lower()


def _is_retryable_provider_error(error: Exception) -> bool:
    if _is_timeout(error):
        return True
    status = getattr(error, "status_code", None) or getattr(error, "code", None)
    try:
        return int(status) in TRANSIENT_STATUS_CODES
    except (TypeError, ValueError):
        return type(error).__name__.lower() in {"servererror", "serviceunavailable"}


def _remove_unsupported_schema_fields(value):
    if isinstance(value, dict):
        return {
            key: _remove_unsupported_schema_fields(item)
            for key, item in value.items()
            if key != "additionalProperties"
        }
    if isinstance(value, list):
        return [_remove_unsupported_schema_fields(item) for item in value]
    return value
